"""
DBSCAN-based geographic clustering of pending retailer orders.
Groups nearby retailers into delivery clusters for efficient batching.
"""
from typing import List, Dict, Tuple
import math
from collections import defaultdict

try:
    import numpy as np
    from sklearn.cluster import DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometres between two GPS points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cluster_orders(
    orders: List[Dict],
    eps_km: float = 5.0,
    min_samples: int = 2,
) -> Dict[str, int]:
    """
    Run DBSCAN on order retailer coordinates.

    Args:
        orders: list of dicts with keys: id (str), lat (float), lon (float)
        eps_km: neighbourhood radius in km
        min_samples: minimum orders per cluster

    Returns:
        dict mapping order_id (str) -> cluster_label (int)
        Cluster label -1 = noise (standalone order, gets its own solo route)
    """
    if not orders:
        return {}

    if not SKLEARN_AVAILABLE:
        # Fallback: treat all orders as one cluster
        return {o["id"]: 0 for o in orders}

    coords = np.array([[o["lat"], o["lon"]] for o in orders], dtype=float)
    coords_rad = np.radians(coords)

    # eps in radians: km / Earth_radius_km
    eps_rad = eps_km / 6371.0

    db = DBSCAN(
        eps=eps_rad,
        min_samples=min_samples,
        algorithm="ball_tree",
        metric="haversine",
    )
    labels = db.fit_predict(coords_rad)

    return {orders[i]["id"]: int(labels[i]) for i in range(len(orders))}


def split_noise_into_solo_clusters(label_map: Dict[str, int]) -> Dict[str, int]:
    """
    DBSCAN marks singleton orders as label -1 (noise).
    This converts each noise order into its own unique cluster label
    so every order gets its own DeliveryRoute.
    """
    next_label = max(label_map.values(), default=-1) + 1
    result = {}
    for order_id, label in label_map.items():
        if label == -1:
            result[order_id] = next_label
            next_label += 1
        else:
            result[order_id] = label
    return result


def build_cluster_summaries(geo_orders: List[Dict], label_map: Dict[str, int]) -> List[Dict]:
    """Build human-readable summaries for each geographic cluster."""
    grouped: Dict[int, List[Dict]] = defaultdict(list)
    for order in geo_orders:
        grouped[label_map[order["id"]]].append(order)

    summaries = []
    for cluster_label, orders_in_cluster in sorted(grouped.items()):
        if not orders_in_cluster:
            continue

        centroid_lat = sum(o["lat"] for o in orders_in_cluster) / len(orders_in_cluster)
        centroid_lon = sum(o["lon"] for o in orders_in_cluster) / len(orders_in_cluster)

        distances = [
            haversine_km(centroid_lat, centroid_lon, o["lat"], o["lon"])
            for o in orders_in_cluster
        ]
        radius_km = max(distances, default=0.0)

        summaries.append({
            "cluster_id": f"cluster-{cluster_label}",
            "retailers": [o.get("retailer_name") for o in orders_in_cluster if o.get("retailer_name")],
            "orders": [o["order"] for o in orders_in_cluster],
            "total_order_volume": sum(int(o["order"].get("total_amount", 0) or 0) for o in orders_in_cluster),
            "approximate_area": {
                "center": {"lat": round(centroid_lat, 4), "lon": round(centroid_lon, 4)},
                "radius_km": round(radius_km, 2),
            },
        })

    return summaries
