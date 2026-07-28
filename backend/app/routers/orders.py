"""
Orders router — rewritten to use Supabase REST API.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.supabase_client import orders_table, order_items_table, products_table, inventory_table, users_table, locations_table
from app.dependencies import get_current_user, require_retailer
from datetime import datetime

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def _enrich_order(o: dict, items: list, users_map: dict, locations_map: dict, products_map: dict) -> dict:
    retailer = users_map.get(str(o.get("retailer_id")))
    loc = locations_map.get(str(o.get("retailer_id")))
    
    enriched_items = []
    for item in items:
        p = products_map.get(str(item.get("product_id")))
        enriched_items.append({
            "id": item.get("id"),
            "order_id": item.get("order_id"),
            "product_id": item.get("product_id"),
            "quantity": item.get("quantity"),
            "unit_price": item.get("unit_price"),
            "subtotal": float(item.get("quantity", 0)) * float(item.get("unit_price", 0)),
            "product_name": p.get("name") if p else None,
            "product_sku": p.get("sku") if p else None,
            "product_unit": p.get("unit") if p else None,
        })
        
    return {
        "id": o.get("id"),
        "retailer_id": o.get("retailer_id"),
        "distributor_id": o.get("distributor_id"),
        "status": o.get("status"),
        "total_amount": o.get("total_amount"),
        "notes": o.get("notes"),
        "created_at": o.get("created_at"),
        "updated_at": o.get("updated_at"),
        "delivered_at": o.get("delivered_at"),
        "items": enriched_items,
        "retailer_name": retailer.get("name") if retailer else None,
        "retailer_area": loc.get("area") if loc else None,
        "retailer_lat": loc.get("latitude") if loc else None,
        "retailer_lon": loc.get("longitude") if loc else None,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def place_order(payload: dict, current_user=Depends(require_retailer)):
    items_data = payload.get("items", [])
    if not items_data:
        raise HTTPException(status_code=400, detail="Order must have at least one item")

    # Fetch all relevant products and inventory
    product_ids = [i.get("product_id") for i in items_data]
    products = []
    invs = []
    for pid in product_ids:
        p_res = products_table.select("*", id=pid, is_active="true")
        if p_res:
            products.append(p_res[0])
        i_res = inventory_table.select("*", product_id=pid)
        if i_res:
            invs.append(i_res[0])
            
    products_map = {str(p["id"]): p for p in products}
    invs_map = {str(i["product_id"]): i for i in invs}

    total = 0.0
    for item_data in items_data:
        pid = str(item_data.get("product_id"))
        qty = item_data.get("quantity", 0)
        
        if pid not in products_map:
            raise HTTPException(status_code=404, detail=f"Product {pid} not found or inactive")
        if qty <= 0:
            raise HTTPException(status_code=400, detail="Item quantity must be positive")
            
        p = products_map[pid]
        inv = invs_map.get(pid)
        
        if not inv or inv.get("quantity", 0) < qty:
            available = inv.get("quantity", 0) if inv else 0
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{p['name']}': available {available}, requested {qty}",
            )
            
        total += float(p.get("unit_price", 0)) * qty

    retailer_id = current_user.get("id") if isinstance(current_user, dict) else str(current_user.id)
    
    # Create order
    order = orders_table.insert({
        "retailer_id": retailer_id,
        "status": "pending",
        "notes": payload.get("notes"),
        "total_amount": round(total, 2)
    })
    
    # Create items
    db_items = []
    for item_data in items_data:
        pid = str(item_data.get("product_id"))
        p = products_map[pid]
        qty = item_data.get("quantity", 0)
        db_items.append({
            "order_id": order["id"],
            "product_id": pid,
            "quantity": qty,
            "unit_price": p.get("unit_price", 0)
        })
    
    order_items_table.insert_many(db_items)
    
    # Deduct inventory (since it's not a single transaction, do best effort)
    for item_data in items_data:
        pid = str(item_data.get("product_id"))
        qty = item_data.get("quantity", 0)
        inv = invs_map.get(pid)
        if inv:
            new_qty = inv.get("quantity", 0) - qty
            inventory_table.update({"id": inv["id"]}, {"quantity": new_qty})
            
    # Fetch full order to return
    return get_order(order["id"], current_user)


@router.get("/")
def list_orders(status_filter: Optional[str] = Query(None, alias="status"), current_user=Depends(get_current_user)):
    role = current_user.get("role") if isinstance(current_user, dict) else str(current_user.role)
    user_id = current_user.get("id") if isinstance(current_user, dict) else str(current_user.id)
    
    params = {}
    if status_filter:
        params["status"] = f"eq.{status_filter}"
        
    if role == "retailer":
        params["retailer_id"] = f"eq.{user_id}"
        orders = orders_table.select_raw(params)
    elif role == "distributor":
        # Cannot easily do OR condition with postgrest without 'or' param, let's fetch pending and assigned
        if status_filter:
            if status_filter == "pending":
                params["status"] = "eq.pending"
                orders = orders_table.select_raw(params)
            else:
                params["distributor_id"] = f"eq.{user_id}"
                orders = orders_table.select_raw(params)
        else:
            orders_pending = orders_table.select_raw({"status": "eq.pending"})
            orders_assigned = orders_table.select_raw({"distributor_id": f"eq.{user_id}"})
            # merge and deduplicate
            orders_dict = {o["id"]: o for o in orders_pending + orders_assigned}
            orders = list(orders_dict.values())
    else:
        orders = orders_table.select_raw(params)
        
    orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Batch enrich
    order_ids = [o["id"] for o in orders]
    retailer_ids = list(set(o["retailer_id"] for o in orders if o.get("retailer_id")))
    
    users = []
    locs = []
    for rid in retailer_ids:
        u_res = users_table.select("id,name", id=rid)
        if u_res: users.append(u_res[0])
        l_res = locations_table.select("*", user_id=rid)
        if l_res: locs.append(l_res[0])
        
    users_map = {str(u["id"]): u for u in users}
    locs_map = {str(l["user_id"]): l for l in locs}
    
    all_items = []
    # For large lists, we should fetch items per order
    # To avoid N+1 queries, we fetch all items for these order ids in batches
    for o_id in order_ids:
        items = order_items_table.select("*", order_id=o_id)
        all_items.extend(items)
        
    items_by_order = {}
    product_ids = set()
    for i in all_items:
        items_by_order.setdefault(i["order_id"], []).append(i)
        product_ids.add(i["product_id"])
        
    products = []
    for pid in product_ids:
        p_res = products_table.select("id,name,sku,unit", id=pid)
        if p_res: products.append(p_res[0])
    products_map = {str(p["id"]): p for p in products}

    result = []
    for o in orders:
        items = items_by_order.get(o["id"], [])
        result.append(_enrich_order(o, items, users_map, locs_map, products_map))
        
    return result


@router.get("/pending-for-cluster")
def get_pending_for_cluster(current_user=Depends(get_current_user)):
    orders = orders_table.select("*", status="pending")
    retailer_ids = list(set(o["retailer_id"] for o in orders if o.get("retailer_id")))
    
    users = []
    locs = []
    for rid in retailer_ids:
        u_res = users_table.select("id,name", id=rid)
        if u_res: users.append(u_res[0])
        l_res = locations_table.select("*", user_id=rid)
        if l_res: locs.append(l_res[0])
        
    users_map = {str(u["id"]): u for u in users}
    locs_map = {str(l["user_id"]): l for l in locs}
    
    # Filter orders to only those with retailer location
    orders_with_loc = [o for o in orders if o.get("retailer_id") and str(o["retailer_id"]) in locs_map]
    
    all_items = []
    for o in orders_with_loc:
        items = order_items_table.select("*", order_id=o["id"])
        all_items.extend(items)
        
    items_by_order = {}
    product_ids = set()
    for i in all_items:
        items_by_order.setdefault(i["order_id"], []).append(i)
        product_ids.add(i["product_id"])
        
    products = []
    for pid in product_ids:
        p_res = products_table.select("id,name,sku,unit", id=pid)
        if p_res: products.append(p_res[0])
    products_map = {str(p["id"]): p for p in products}

    result = []
    for o in orders_with_loc:
        items = items_by_order.get(o["id"], [])
        result.append(_enrich_order(o, items, users_map, locs_map, products_map))
        
    return result


@router.get("/{order_id}")
def get_order(order_id: str, current_user=Depends(get_current_user)):
    orders = orders_table.select("*", id=order_id)
    if not orders:
        raise HTTPException(status_code=404, detail="Order not found")
    o = orders[0]
    
    role = current_user.get("role") if isinstance(current_user, dict) else str(current_user.role)
    user_id = current_user.get("id") if isinstance(current_user, dict) else str(current_user.id)
    
    if role == "retailer" and str(o.get("retailer_id")) != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    items = order_items_table.select("*", order_id=order_id)
    
    rid = o.get("retailer_id")
    users = users_table.select("id,name", id=rid) if rid else []
    locs = locations_table.select("*", user_id=rid) if rid else []
    
    users_map = {str(u["id"]): u for u in users}
    locs_map = {str(l["user_id"]): l for l in locs}
    
    products_map = {}
    for item in items:
        p_res = products_table.select("id,name,sku,unit", id=item["product_id"])
        if p_res:
            products_map[str(p_res[0]["id"])] = p_res[0]
            
    return _enrich_order(o, items, users_map, locs_map, products_map)


@router.patch("/{order_id}")
def update_order(order_id: str, payload: dict, current_user=Depends(get_current_user)):
    orders = orders_table.select("*", id=order_id)
    if not orders:
        raise HTTPException(status_code=404, detail="Order not found")
        
    update_data = {}
    if "status" in payload:
        update_data["status"] = payload["status"]
        if payload["status"] == "delivered":
            update_data["delivered_at"] = datetime.utcnow().isoformat()
    if "distributor_id" in payload:
        update_data["distributor_id"] = payload["distributor_id"]
    if "notes" in payload and payload["notes"] is not None:
        update_data["notes"] = payload["notes"]
        
    if update_data:
        orders_table.update({"id": order_id}, update_data)
        
    return get_order(order_id, current_user)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_order(order_id: str, current_user=Depends(require_retailer)):
    user_id = current_user.get("id") if isinstance(current_user, dict) else str(current_user.id)
    orders = orders_table.select("*", id=order_id, retailer_id=user_id)
    if not orders:
        raise HTTPException(status_code=404, detail="Order not found")
        
    o = orders[0]
    if o.get("status") not in ("pending", "confirmed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order in status '{o.get('status')}'",
        )
        
    orders_table.update({"id": order_id}, {"status": "cancelled"})
