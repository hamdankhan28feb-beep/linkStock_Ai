"""
Inventory router — rewritten to use Supabase REST API.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.supabase_client import inventory_table, products_table, low_stock_alerts_table
from app.dependencies import get_current_user, require_warehouse, require_distributor_or_warehouse
from datetime import datetime

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


def _enrich_inventory(inv: dict, products_map: dict) -> dict:
    p = products_map.get(str(inv.get("product_id")))
    return {
        "id": inv.get("id"),
        "product_id": inv.get("product_id"),
        "warehouse_user_id": inv.get("warehouse_user_id"),
        "quantity": inv.get("quantity"),
        "low_stock_threshold": inv.get("low_stock_threshold"),
        "is_low_stock": (inv.get("quantity", 0) <= inv.get("low_stock_threshold", 50)),
        "updated_at": inv.get("updated_at"),
        "product_name": p.get("name") if p else None,
        "product_sku": p.get("sku") if p else None,
        "product_category": p.get("category") if p else None,
        "product_unit": p.get("unit") if p else None,
    }


@router.get("/")
def list_inventory(current_user=Depends(require_distributor_or_warehouse)):
    invs = inventory_table.select("*")
    # Fetch active products
    products = products_table.select("id,name,sku,category,unit", is_active="true")
    products_map = {str(p["id"]): p for p in products}

    # Only return inventory for active products
    enriched = []
    for inv in invs:
        if str(inv["product_id"]) in products_map:
            enriched.append(_enrich_inventory(inv, products_map))
    
    # Sort by category, name
    enriched.sort(key=lambda x: (x.get("product_category", ""), x.get("product_name", "")))
    return enriched


@router.get("/alerts")
def get_alerts(current_user=Depends(require_distributor_or_warehouse)):
    alerts = low_stock_alerts_table.select("*", resolved_at="is.null")
    
    if not alerts:
        return []

    # Get related products
    product_ids = list(set(a["product_id"] for a in alerts))
    products_map = {}
    for pid in product_ids:
        p_res = products_table.select("id,name,sku", id=pid)
        if p_res:
            products_map[str(pid)] = p_res[0]
            
    res = []
    for a in alerts:
        p = products_map.get(str(a["product_id"]))
        res.append({
            "id": a.get("id"),
            "inventory_id": a.get("inventory_id"),
            "product_id": a.get("product_id"),
            "current_quantity": a.get("current_quantity"),
            "threshold": a.get("threshold"),
            "is_read": a.get("is_read", False),
            "triggered_at": a.get("triggered_at"),
            "resolved_at": a.get("resolved_at"),
            "product_name": p.get("name") if p else None,
            "product_sku": p.get("sku") if p else None,
        })
    return res


@router.get("/alerts/count")
def alert_count(current_user=Depends(get_current_user)):
    alerts = low_stock_alerts_table.select("id", resolved_at="is.null", is_read="false")
    return {"unread_alert_count": len(alerts)}


@router.get("/{inventory_id}")
def get_inventory_item(inventory_id: str, current_user=Depends(require_distributor_or_warehouse)):
    invs = inventory_table.select("*", id=inventory_id)
    if not invs:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    inv = invs[0]
    products = products_table.select("id,name,sku,category,unit", id=inv["product_id"])
    p_map = {str(products[0]["id"]): products[0]} if products else {}
    return _enrich_inventory(inv, p_map)


def _check_and_create_alert(inv: dict):
    """Check stock level and create alert if needed."""
    if inv.get("quantity", 0) <= inv.get("low_stock_threshold", 50):
        # Check if unresolved alert already exists
        existing = low_stock_alerts_table.select(
            "id", 
            inventory_id=inv["id"], 
            resolved_at="is.null"
        )
        if not existing:
            low_stock_alerts_table.insert({
                "inventory_id": inv["id"],
                "product_id": inv["product_id"],
                "current_quantity": inv.get("quantity", 0),
                "threshold": inv.get("low_stock_threshold", 50)
            })
    else:
        # Resolve existing alerts
        existing = low_stock_alerts_table.select(
            "id", 
            inventory_id=inv["id"], 
            resolved_at="is.null"
        )
        for a in existing:
            low_stock_alerts_table.update({"id": a["id"]}, {"resolved_at": datetime.utcnow().isoformat()})


@router.patch("/{inventory_id}")
def update_inventory(inventory_id: str, payload: dict, current_user=Depends(require_warehouse)):
    invs = inventory_table.select("*", id=inventory_id)
    if not invs:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    
    update_data = {}
    if "quantity" in payload:
        if payload["quantity"] < 0:
            raise HTTPException(status_code=400, detail="Quantity cannot be negative")
        update_data["quantity"] = payload["quantity"]
        
    if "low_stock_threshold" in payload:
        update_data["low_stock_threshold"] = payload["low_stock_threshold"]
        
    if not update_data:
        return get_inventory_item(inventory_id, current_user)
        
    updated = inventory_table.update({"id": inventory_id}, update_data)
    if updated:
        _check_and_create_alert(updated[0])
    
    return get_inventory_item(inventory_id, current_user)


@router.post("/{inventory_id}/adjust")
def adjust_inventory(inventory_id: str, payload: dict, current_user=Depends(require_warehouse)):
    invs = inventory_table.select("*", id=inventory_id)
    if not invs:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    
    inv = invs[0]
    delta = payload.get("delta", 0)
    new_qty = inv.get("quantity", 0) + delta
    
    if new_qty < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Adjustment would result in negative stock ({new_qty})",
        )
        
    updated = inventory_table.update({"id": inventory_id}, {"quantity": new_qty})
    if updated:
        _check_and_create_alert(updated[0])
        
    return get_inventory_item(inventory_id, current_user)


@router.post("/alerts/{alert_id}/read")
def read_alert(alert_id: str, current_user=Depends(require_warehouse)):
    alerts = low_stock_alerts_table.select("*", id=alert_id)
    if not alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    low_stock_alerts_table.update({"id": alert_id}, {"is_read": True})
    return {"message": "Alert marked as read"}


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert_endpoint(alert_id: str, current_user=Depends(require_warehouse)):
    alerts = low_stock_alerts_table.select("*", id=alert_id)
    if not alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    low_stock_alerts_table.update(
        {"id": alert_id}, 
        {"resolved_at": datetime.utcnow().isoformat(), "is_read": True}
    )
    return {"message": "Alert resolved"}
