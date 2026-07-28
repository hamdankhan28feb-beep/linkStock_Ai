"""
Delivery Routes router: DBSCAN cluster generation and OR-Tools route optimization.
Rewritten to use Supabase REST API.
"""
from collections import defaultdict
from typing import List, Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from app.supabase_client import (
    orders_table, delivery_routes_table, route_stops_table, 
    users_table, locations_table
)
from app.dependencies import get_current_user, require_distributor
from app.services.clustering_service import cluster_orders, split_noise_into_solo_clusters, build_cluster_summaries
from app.services.routing_service import solve_vrp

router = APIRouter(prefix="/api/delivery-routes", tags=["Delivery Routes"])
routes_router = APIRouter(prefix="/api/routes", tags=["Routes"])


def _build_geo_orders(pending_orders: list, users_map: dict, locs_map: dict) -> list:
    geo_orders = []
    for order in pending_orders:
        retailer_id = str(order.get("retailer_id"))
        location = locs_map.get(retailer_id)
        user = users_map.get(retailer_id)
        if not location or not user:
            continue
        geo_orders.append({
            "id": str(order["id"]),
            "lat": location.get("latitude"),
            "lon": location.get("longitude"),
            "retailer_name": user.get("name"),
            "order": {
                "id": order.get("id"),
                "total_amount": order.get("total_amount", 0),
            },
        })
    return geo_orders


def _build_optimized_route_payload(
    depot_address: str,
    depot_latitude: float,
    depot_longitude: float,
    stop_details: list,
    ordered_stop_ids: list,
    total_distance_km: float,
    average_speed_kmh: float = 30.0,
) -> Dict:
    ordered_stops = []
    stop_lookup = {str(stop["id"]): stop for stop in stop_details}

    for stop_number, stop_id in enumerate(ordered_stop_ids, start=1):
        detail = stop_lookup.get(str(stop_id))
        if not detail:
            continue
        ordered_stops.append({
            "stop_number": stop_number,
            "id": str(detail["id"]),
            "order_id": detail["order_id"],
            "retailer_id": detail["retailer_id"],
            "retailer_name": detail.get("retailer_name", "Retailer"),
            "address": detail.get("address", ""),
            "latitude": detail.get("latitude"),
            "longitude": detail.get("longitude"),
            "order_total": detail.get("order_total", 0),
        })

    travel_minutes = 0
    if total_distance_km:
        travel_minutes = max(1, int(round((total_distance_km / average_speed_kmh) * 60)))

    return {
        "depot_address": depot_address,
        "depot_location": {"lat": depot_latitude, "lon": depot_longitude},
        "ordered_stops": ordered_stops,
        "total_distance_km": round(total_distance_km, 2),
        "estimated_travel_time_minutes": travel_minutes,
    }


@routes_router.post("/cluster")
def cluster_pending_orders(payload: dict, current_user=Depends(require_distributor)):
    pending_orders = orders_table.select("*", status="pending")
    if not pending_orders:
        raise HTTPException(status_code=404, detail="No pending orders found")

    retailer_ids = sorted({str(o.get("retailer_id")) for o in pending_orders if o.get("retailer_id")})
    users_map = {}
    locs_map = {}

    for retailer_id in retailer_ids:
        user_res = users_table.select("id,name", id=retailer_id)
        if user_res:
            users_map[retailer_id] = user_res[0]
        location_res = locations_table.select("*", user_id=retailer_id)
        if location_res:
            locs_map[retailer_id] = location_res[0]

    geo_orders = _build_geo_orders(pending_orders, users_map, locs_map)

    if not geo_orders:
        raise HTTPException(status_code=400, detail="No pending orders with retailer GPS coordinates found")

    eps_km = payload.get("eps_km", 2.0)
    min_samples = payload.get("min_samples", 2)
    raw_label_map = cluster_orders(
        [{"id": o["id"], "lat": o["lat"], "lon": o["lon"]} for o in geo_orders],
        eps_km=eps_km,
        min_samples=min_samples,
    )
    label_map = split_noise_into_solo_clusters(raw_label_map)

    clusters = build_cluster_summaries(geo_orders, label_map)

    return {
        "clusters": clusters,
        "cluster_count": len(clusters),
        "generated_by": current_user.get("id"),
    }


@routes_router.post("/optimize")
def optimize_cluster(payload: dict, current_user=Depends(require_distributor)):
    cluster = payload.get("cluster") or {}
    cluster_order_ids = [str(o.get("id")) for o in cluster.get("orders", []) if o.get("id")]
    if not cluster_order_ids and payload.get("order_ids"):
        cluster_order_ids = [str(o) for o in payload.get("order_ids", [])]

    if not cluster_order_ids:
        raise HTTPException(status_code=400, detail="No cluster orders were supplied")

    pending_orders = orders_table.select("*", status="pending")
    if not pending_orders:
        raise HTTPException(status_code=404, detail="No pending orders found")

    order_lookup = {str(order.get("id")): order for order in pending_orders if order.get("id")}
    selected_orders = [order_lookup[order_id] for order_id in cluster_order_ids if str(order_id) in order_lookup]

    if not selected_orders:
        raise HTTPException(status_code=400, detail="The selected cluster did not resolve to any pending orders")

    retailer_ids = sorted({str(order.get("retailer_id")) for order in selected_orders if order.get("retailer_id")})
    users_map = {}
    locs_map = {}

    for retailer_id in retailer_ids:
        user_res = users_table.select("id,name", id=retailer_id)
        if user_res:
            users_map[retailer_id] = user_res[0]
        location_res = locations_table.select("*", user_id=retailer_id)
        if location_res:
            locs_map[retailer_id] = location_res[0]

    stop_details = []
    for order in selected_orders:
        retailer_id = str(order.get("retailer_id"))
        location = locs_map.get(retailer_id)
        user = users_map.get(retailer_id)
        if not location or location.get("latitude") is None or location.get("longitude") is None:
            continue
        stop_details.append({
            "id": str(order["id"]),
            "order_id": str(order.get("id")),
            "retailer_id": retailer_id,
            "retailer_name": user.get("name") if user else retailer_id,
            "address": location.get("address", ""),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "order_total": order.get("total_amount", 0),
        })

    if not stop_details:
        raise HTTPException(status_code=400, detail="The selected cluster does not have retailer GPS coordinates")

    dist_loc_res = locations_table.select("*", user_id=current_user["id"])
    dist_loc = dist_loc_res[0] if dist_loc_res else None
    depot_lat = payload.get("depot_latitude") or (dist_loc["latitude"] if dist_loc else DEFAULT_DEPOT_LAT)
    depot_lon = payload.get("depot_longitude") or (dist_loc["longitude"] if dist_loc else DEFAULT_DEPOT_LON)
    depot_addr = payload.get("depot_address") or (dist_loc.get("address", DEFAULT_DEPOT_ADDR) if dist_loc else DEFAULT_DEPOT_ADDR)

    stops_input = [
        {"id": str(stop["id"]), "lat": stop["latitude"], "lon": stop["longitude"]}
        for stop in stop_details
    ]

    result = solve_vrp(
        depot_lat=depot_lat,
        depot_lon=depot_lon,
        stops=stops_input,
    )

    route_payload = _build_optimized_route_payload(
        depot_address=depot_addr,
        depot_latitude=depot_lat,
        depot_longitude=depot_lon,
        stop_details=stop_details,
        ordered_stop_ids=result["ordered_stop_ids"],
        total_distance_km=result.get("total_distance_km", 0.0),
    )

    return {
        "cluster_id": payload.get("cluster_id") or cluster.get("cluster_id"),
        "generated_by": current_user.get("id"),
        **route_payload,
    }

DEFAULT_DEPOT_LAT = 24.8850
DEFAULT_DEPOT_LON = 67.0100
DEFAULT_DEPOT_ADDR = "SITE Area, Karachi"


def _route_summary(route: dict, stops: list) -> dict:
    completed = sum(1 for s in stops if s.get("status") == "completed")
    return {
        "id": route.get("id"),
        "name": route.get("name"),
        "cluster_label": route.get("cluster_label"),
        "status": route.get("status"),
        "total_stops": route.get("total_stops"),
        "total_distance_km": route.get("total_distance_km"),
        "created_at": route.get("created_at"),
        "completed_stops": completed,
    }


def _route_detail(route: dict, stops: list) -> dict:
    enriched_stops = []
    for s in stops:
        enriched_stops.append({
            "id": s.get("id"),
            "route_id": s.get("route_id"),
            "order_id": s.get("order_id"),
            "retailer_id": s.get("retailer_id"),
            "stop_sequence": s.get("stop_sequence"),
            "latitude": s.get("latitude"),
            "longitude": s.get("longitude"),
            "address": s.get("address"),
            "retailer_name": s.get("retailer_name"),
            "order_total": s.get("order_total"),
            "status": s.get("status"),
            "completed_at": s.get("completed_at"),
            "notes": s.get("notes"),
        })
    return {
        "id": route.get("id"),
        "distributor_id": route.get("distributor_id"),
        "name": route.get("name"),
        "cluster_label": route.get("cluster_label"),
        "status": route.get("status"),
        "depot_latitude": route.get("depot_latitude"),
        "depot_longitude": route.get("depot_longitude"),
        "depot_address": route.get("depot_address"),
        "total_distance_km": route.get("total_distance_km"),
        "total_stops": route.get("total_stops"),
        "created_at": route.get("created_at"),
        "updated_at": route.get("updated_at"),
        "completed_at": route.get("completed_at"),
        "stops": enriched_stops,
    }


@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_clusters(payload: dict, current_user=Depends(require_distributor)):
    pending_orders = orders_table.select("*", status="pending")
    
    retailer_ids = list(set(o["retailer_id"] for o in pending_orders if o.get("retailer_id")))
    
    users = []
    locs = []
    for rid in retailer_ids:
        u_res = users_table.select("id,name", id=rid)
        if u_res: users.append(u_res[0])
        l_res = locations_table.select("*", user_id=rid)
        if l_res: locs.append(l_res[0])
        
    users_map = {str(u["id"]): u for u in users}
    locs_map = {str(l["user_id"]): l for l in locs}

    geo_orders = []
    for order in pending_orders:
        rid = str(order.get("retailer_id"))
        if rid in users_map and rid in locs_map:
            loc = locs_map[rid]
            geo_orders.append({
                "id": str(order["id"]),
                "lat": loc["latitude"],
                "lon": loc["longitude"],
                "order": order,
                "retailer_name": users_map[rid]["name"],
                "retailer_address": loc["address"],
                "retailer_area": loc["area"]
            })

    if not geo_orders:
        raise HTTPException(
            status_code=400,
            detail="No pending orders with retailer GPS coordinates found",
        )

    eps_km = payload.get("eps_km", 2.0)
    min_samples = payload.get("min_samples", 2)
    raw_label_map = cluster_orders(
        [{"id": o["id"], "lat": o["lat"], "lon": o["lon"]} for o in geo_orders],
        eps_km=eps_km,
        min_samples=min_samples,
    )

    noise_count = sum(1 for label in raw_label_map.values() if label == -1)
    label_map = split_noise_into_solo_clusters(raw_label_map)

    clusters: dict = defaultdict(list)
    for o in geo_orders:
        clusters[label_map[o["id"]]].append(o)

    # Depot coordinates
    dist_loc_res = locations_table.select("*", user_id=current_user["id"])
    dist_loc = dist_loc_res[0] if dist_loc_res else None
    
    depot_lat = payload.get("depot_latitude") or (dist_loc["latitude"] if dist_loc else DEFAULT_DEPOT_LAT)
    depot_lon = payload.get("depot_longitude") or (dist_loc["longitude"] if dist_loc else DEFAULT_DEPOT_LON)
    depot_addr = payload.get("depot_address") or (dist_loc.get("address", DEFAULT_DEPOT_ADDR) if dist_loc else DEFAULT_DEPOT_ADDR)

    created_routes = []
    cluster_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for idx, (cluster_label, orders_in_cluster) in enumerate(sorted(clusters.items())):
        label_letter = cluster_letters[idx % len(cluster_letters)]
        area_names = list({
            o["retailer_area"]
            for o in orders_in_cluster
            if o.get("retailer_area")
        })
        area_str = ", ".join(area_names[:2]) if area_names else "Karachi"
        route_name = f"Cluster {label_letter} — {area_str}"

        route_data = {
            "distributor_id": current_user["id"],
            "name": route_name,
            "cluster_label": cluster_label,
            "status": "pending",
            "depot_latitude": depot_lat,
            "depot_longitude": depot_lon,
            "depot_address": depot_addr,
            "total_stops": len(orders_in_cluster),
        }
        route = delivery_routes_table.insert(route_data)
        
        stops_data = []
        for seq, o in enumerate(orders_in_cluster):
            order_obj = o["order"]
            stops_data.append({
                "route_id": route["id"],
                "order_id": order_obj["id"],
                "retailer_id": order_obj["retailer_id"],
                "stop_sequence": seq,
                "latitude": o["lat"],
                "longitude": o["lon"],
                "address": o.get("retailer_address"),
                "retailer_name": o.get("retailer_name"),
                "order_total": order_obj.get("total_amount", 0),
                "status": "pending",
            })
            # Mark order clustered
            orders_table.update(
                {"id": order_obj["id"]}, 
                {"status": "clustered", "distributor_id": current_user["id"]}
            )
            
        inserted_stops = route_stops_table.insert_many(stops_data)
        created_routes.append({"route": route, "stops": inserted_stops})

    return {
        "clusters_created": len(created_routes),
        "orders_clustered": len(geo_orders),
        "noise_orders": noise_count,
        "routes": [_route_summary(r["route"], r["stops"]) for r in created_routes],
    }


@router.get("/")
def list_routes(current_user=Depends(require_distributor)):
    routes = delivery_routes_table.select("*", distributor_id=current_user["id"])
    routes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    result = []
    for r in routes:
        stops = route_stops_table.select("status", route_id=r["id"])
        result.append(_route_summary(r, stops))
        
    return result


@router.get("/{route_id}")
def get_route(route_id: str, current_user=Depends(get_current_user)):
    routes = delivery_routes_table.select("*", id=route_id)
    if not routes:
        raise HTTPException(status_code=404, detail="Delivery route not found")
    r = routes[0]
    stops = route_stops_table.select("*", route_id=route_id)
    stops.sort(key=lambda x: x.get("stop_sequence", 0))
    return _route_detail(r, stops)


@router.post("/{route_id}/optimize")
def optimize_route(route_id: str, current_user=Depends(require_distributor)):
    routes = delivery_routes_table.select("*", id=route_id, distributor_id=current_user["id"])
    if not routes:
        raise HTTPException(status_code=404, detail="Delivery route not found")
    route = routes[0]
    
    stops = route_stops_table.select("*", route_id=route_id)
    stops_input = [
        {"id": str(s["id"]), "lat": s["latitude"], "lon": s["longitude"]}
        for s in stops
    ]

    result = solve_vrp(
        depot_lat=route.get("depot_latitude") or DEFAULT_DEPOT_LAT,
        depot_lon=route.get("depot_longitude") or DEFAULT_DEPOT_LON,
        stops=stops_input,
    )

    ordered_ids = result["ordered_stop_ids"]
    id_to_seq = {stop_id: idx for idx, stop_id in enumerate(ordered_ids)}

    for stop in stops:
        seq = id_to_seq.get(str(stop["id"]))
        if seq is not None:
            stop["stop_sequence"] = seq
            route_stops_table.update({"id": stop["id"]}, {"stop_sequence": seq})

    route_data = {
        "total_distance_km": result["total_distance_km"],
        "status": "in_progress"
    }
    updated_routes = delivery_routes_table.update({"id": route_id}, route_data)
    
    if updated_routes:
        route.update(updated_routes[0])
        
    stops.sort(key=lambda x: x.get("stop_sequence", 0))

    return {
        "route_id": route["id"],
        "total_stops": route["total_stops"],
        "total_distance_km": route.get("total_distance_km"),
        "stops": stops,
    }


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(route_id: str, current_user=Depends(require_distributor)):
    routes = delivery_routes_table.select("*", id=route_id, distributor_id=current_user["id"])
    if not routes:
        raise HTTPException(status_code=404, detail="Delivery route not found")
    if routes[0].get("status") == "completed":
        raise HTTPException(status_code=400, detail="Cannot delete a completed route")
        
    stops = route_stops_table.select("id,order_id", route_id=route_id)
    for stop in stops:
        orders_table.update(
            {"id": stop["order_id"]}, 
            {"status": "pending", "distributor_id": None}
        )
        
    delivery_routes_table.delete(id=route_id)
