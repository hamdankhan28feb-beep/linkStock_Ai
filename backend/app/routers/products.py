"""
Products router — rewritten to use Supabase REST API.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.supabase_client import products_table, inventory_table
from app.dependencies import get_current_user, require_warehouse

router = APIRouter(prefix="/api/products", tags=["Products"])


def _enrich_product(p: dict, inventories: dict = {}) -> dict:
    inv = inventories.get(str(p.get("id")))
    quantity = inv.get("quantity") if inv else None
    threshold = inv.get("low_stock_threshold", 50) if inv else 50
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "sku": p.get("sku"),
        "category": p.get("category"),
        "description": p.get("description"),
        "unit_price": float(p.get("unit_price", 0)),
        "unit": p.get("unit", "unit"),
        "image_url": p.get("image_url"),
        "is_active": p.get("is_active", True),
        "created_at": p.get("created_at"),
        "current_stock": quantity,
        "is_low_stock": (quantity is not None and quantity <= threshold),
    }


@router.get("/categories/list")
def list_categories(current_user=Depends(get_current_user)):
    products = products_table.select("category")
    cats = sorted(set(p["category"] for p in products if p.get("category")))
    return cats


@router.get("/", response_model=List[dict])
def list_products(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0),
    limit: int = Query(50),
    current_user=Depends(get_current_user),
):
    params = {}
    if active_only:
        params["is_active"] = "eq.true"
    if category:
        params["category"] = f"ilike.*{category}*"
    if search:
        params["or"] = f"(name.ilike.*{search}*,sku.ilike.*{search}*)"

    products = products_table.select_raw(params, "*")
    products.sort(key=lambda p: (p.get("category", ""), p.get("name", "")))

    # Fetch inventories for stock enrichment
    invs = inventory_table.select("*")
    inv_map = {str(i["product_id"]): i for i in invs}

    enriched = [_enrich_product(p, inv_map) for p in products]
    return enriched[skip: skip + limit]


@router.get("/{product_id}", response_model=dict)
def get_product(product_id: str, current_user=Depends(get_current_user)):
    products = products_table.select("*", id=product_id)
    if not products:
        raise HTTPException(status_code=404, detail="Product not found")
    p = products[0]
    invs = inventory_table.select("*", product_id=product_id)
    inv_map = {str(invs[0]["product_id"]): invs[0]} if invs else {}
    return _enrich_product(p, inv_map)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_product(payload: dict, current_user=Depends(require_warehouse)):
    existing = products_table.select("id", sku=payload.get("sku"))
    if existing:
        raise HTTPException(status_code=409, detail=f"SKU '{payload.get('sku')}' already exists")

    product = products_table.insert(payload)
    # Initialize inventory record at 0
    inventory_table.insert({
        "product_id": product["id"],
        "warehouse_user_id": current_user["id"] if isinstance(current_user, dict) else str(current_user.id),
        "quantity": 0,
        "low_stock_threshold": 50,
    })
    return product


@router.put("/{product_id}")
def update_product(product_id: str, payload: dict, current_user=Depends(require_warehouse)):
    existing = products_table.select("id", id=product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    updated = products_table.update({"id": product_id}, payload)
    return updated[0] if updated else {}


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_product(product_id: str, current_user=Depends(require_warehouse)):
    existing = products_table.select("id", id=product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    products_table.update({"id": product_id}, {"is_active": False})
