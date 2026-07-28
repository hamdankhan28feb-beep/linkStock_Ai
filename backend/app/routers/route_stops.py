"""
Route Stops router: mark individual delivery stops as completed,
triggering inventory deduction and low-stock alert generation.
Rewritten to use Supabase REST API.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from app.supabase_client import (
    route_stops_table, delivery_routes_table, orders_table,
    order_items_table, inventory_table, low_stock_alerts_table
)
from app.dependencies import get_current_user, require_distributor

router = APIRouter(prefix="/api/route-stops", tags=["Route Stops"])


@router.get("/{stop_id}")
def get_stop(stop_id: str, current_user=Depends(get_current_user)):
    stops = route_stops_table.select("*", id=stop_id)
    if not stops:
        raise HTTPException(status_code=404, detail="Route stop not found")
    return stops[0]


def _deduct_inventory_and_alert(order_id: str):
    items = order_items_table.select("product_id,quantity", order_id=order_id)
    for item in items:
        pid = item["product_id"]
        qty = item["quantity"]
        
        invs = inventory_table.select("*", product_id=pid)
        if invs:
            inv = invs[0]
            new_qty = inv.get("quantity", 0) - qty
            inventory_table.update({"id": inv["id"]}, {"quantity": new_qty})
            
            # Check for alerts
            threshold = inv.get("low_stock_threshold", 50)
            if new_qty <= threshold:
                existing = low_stock_alerts_table.select("id", inventory_id=inv["id"], resolved_at="is.null")
                if not existing:
                    low_stock_alerts_table.insert({
                        "inventory_id": inv["id"],
                        "product_id": pid,
                        "current_quantity": new_qty,
                        "threshold": threshold
                    })


@router.post("/{stop_id}/complete")
def complete_stop(stop_id: str, payload: dict = {}, current_user=Depends(require_distributor)):
    stops = route_stops_table.select("*", id=stop_id)
    if not stops:
        raise HTTPException(status_code=404, detail="Route stop not found")
    stop = stops[0]

    if stop.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Stop already completed")

    routes = delivery_routes_table.select("id,distributor_id", id=stop["route_id"])
    if not routes or str(routes[0]["distributor_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
        
    route = routes[0]

    # 1. Mark stop
    update_data = {
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat()
    }
    if payload.get("notes"):
        update_data["notes"] = payload["notes"]
        
    route_stops_table.update({"id": stop_id}, update_data)
    stop.update(update_data)

    # 2. Mark order as delivered
    orders_table.update(
        {"id": stop["order_id"]}, 
        {
            "status": "delivered",
            "delivered_at": datetime.utcnow().isoformat()
        }
    )

    # 3 & 4. Deduct inventory + generate alerts
    _deduct_inventory_and_alert(stop["order_id"])

    # 5. Check if whole route is now complete
    all_stops = route_stops_table.select("status", route_id=route["id"])
    if all(s.get("status") in ("completed", "skipped") for s in all_stops):
        delivery_routes_table.update(
            {"id": route["id"]},
            {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            }
        )

    return stop


@router.post("/{stop_id}/skip")
def skip_stop(stop_id: str, current_user=Depends(require_distributor)):
    stops = route_stops_table.select("*", id=stop_id)
    if not stops:
        raise HTTPException(status_code=404, detail="Route stop not found")
    stop = stops[0]
    
    if stop.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending stops can be skipped")

    routes = delivery_routes_table.select("id,distributor_id", id=stop["route_id"])
    if not routes or str(routes[0]["distributor_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
        
    route = routes[0]

    update_data = {"status": "skipped"}
    route_stops_table.update({"id": stop_id}, update_data)
    stop.update(update_data)

    # Check if route is complete
    all_stops = route_stops_table.select("status", route_id=route["id"])
    if all(s.get("status") in ("completed", "skipped") for s in all_stops):
        delivery_routes_table.update(
            {"id": route["id"]},
            {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            }
        )

    return stop
