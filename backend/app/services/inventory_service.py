"""
Inventory management service: stock deduction, low-stock alert generation.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.inventory import Inventory, LowStockAlert
from app.models.order import Order, OrderItem, OrderStatus


def deduct_inventory_for_order(db: Session, order: Order) -> List[LowStockAlert]:
    """
    Deduct order item quantities from inventory.
    Creates LowStockAlert records for any product that drops below threshold.
    Returns list of newly created alerts.
    """
    new_alerts: List[LowStockAlert] = []

    for item in order.items:
        inv = db.query(Inventory).filter(Inventory.product_id == item.product_id).first()
        if not inv:
            continue

        # Deduct — clamp at 0 to avoid negative stock
        inv.quantity = max(0, inv.quantity - item.quantity)
        inv.updated_at = datetime.utcnow()

        # Check low-stock threshold
        if inv.quantity <= inv.low_stock_threshold:
            # Only create a new alert if there isn't an unresolved one already
            existing = (
                db.query(LowStockAlert)
                .filter(
                    LowStockAlert.inventory_id == inv.id,
                    LowStockAlert.resolved_at.is_(None),
                )
                .first()
            )
            if not existing:
                alert = LowStockAlert(
                    inventory_id=inv.id,
                    product_id=item.product_id,
                    current_quantity=inv.quantity,
                    threshold=inv.low_stock_threshold,
                    is_read=False,
                )
                db.add(alert)
                new_alerts.append(alert)

    db.flush()
    return new_alerts


def resolve_alert(db: Session, alert_id: UUID) -> Optional[LowStockAlert]:
    alert = db.query(LowStockAlert).filter(LowStockAlert.id == alert_id).first()
    if alert:
        alert.resolved_at = datetime.utcnow()
        db.flush()
    return alert


def mark_alert_read(db: Session, alert_id: UUID) -> Optional[LowStockAlert]:
    alert = db.query(LowStockAlert).filter(LowStockAlert.id == alert_id).first()
    if alert:
        alert.is_read = True
        db.flush()
    return alert


def get_unresolved_alerts(db: Session) -> List[LowStockAlert]:
    return (
        db.query(LowStockAlert)
        .filter(LowStockAlert.resolved_at.is_(None))
        .order_by(LowStockAlert.triggered_at.desc())
        .all()
    )
