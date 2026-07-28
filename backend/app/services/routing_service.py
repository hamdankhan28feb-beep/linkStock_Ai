"""
Google OR-Tools Vehicle Routing Problem (VRP) solver.
Computes the optimal delivery sequence for a single vehicle starting from a depot.
"""
import math
from typing import List, Dict, Optional, Tuple

try:
    from ortools.constraint_solver import routing_enums_pb2, pywrapcp
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Return Haversine distance in whole metres (integer for OR-Tools)."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def build_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[int]]:
    """Build N×N Haversine distance matrix (in metres)."""
    n = len(locations)
    matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(0)
            else:
                dist = haversine_meters(
                    locations[i][0], locations[i][1],
                    locations[j][0], locations[j][1],
                )
                row.append(dist)
        matrix.append(row)
    return matrix


def solve_vrp(
    depot_lat: float,
    depot_lon: float,
    stops: List[Dict],
    time_limit_seconds: int = 15,
) -> Dict:
    """
    Solve the VRP for a single vehicle.

    Args:
        depot_lat / depot_lon: starting/ending point of the vehicle
        stops: list of dicts with keys: id (str), lat (float), lon (float)
        time_limit_seconds: OR-Tools time budget

    Returns:
        {
          "ordered_stop_ids": [str, ...],  # in optimized visit order
          "total_distance_km": float,
        }
    """
    if not stops:
        return {"ordered_stop_ids": [], "total_distance_km": 0.0}

    # Index 0 = depot, indices 1..N = stops
    locations: List[Tuple[float, float]] = [(depot_lat, depot_lon)] + [
        (s["lat"], s["lon"]) for s in stops
    ]
    n = len(locations)
    distance_matrix = build_distance_matrix(locations)

    if not ORTOOLS_AVAILABLE:
        # Greedy nearest-neighbour fallback
        return _greedy_nearest(depot_lat, depot_lon, stops, distance_matrix)

    # Create routing model
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)  # n nodes, 1 vehicle, depot at index 0
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        return distance_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_idx = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.FromSeconds(time_limit_seconds)

    solution = routing.SolveWithParameters(search_params)

    if solution:
        ordered_ids = []
        total_distance_m = 0
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:  # skip depot node
                ordered_ids.append(stops[node - 1]["id"])
            next_index = solution.Value(routing.NextVar(index))
            total_distance_m += distance_matrix[manager.IndexToNode(index)][manager.IndexToNode(next_index)]
            index = next_index
        return {
            "ordered_stop_ids": ordered_ids,
            "total_distance_km": round(total_distance_m / 1000, 2),
        }

    # If OR-Tools fails, use greedy fallback
    return _greedy_nearest(depot_lat, depot_lon, stops, distance_matrix)


def _greedy_nearest(
    depot_lat: float,
    depot_lon: float,
    stops: List[Dict],
    distance_matrix: List[List[int]],
) -> Dict:
    """Greedy nearest-neighbour heuristic fallback."""
    remaining = list(range(1, len(stops) + 1))  # indices into distance_matrix
    current = 0  # depot
    ordered = []
    total_dist = 0

    while remaining:
        nearest = min(remaining, key=lambda i: distance_matrix[current][i])
        total_dist += distance_matrix[current][nearest]
        ordered.append(stops[nearest - 1]["id"])
        remaining.remove(nearest)
        current = nearest

    # Return to depot
    total_dist += distance_matrix[current][0]

    return {
        "ordered_stop_ids": ordered,
        "total_distance_km": round(total_dist / 1000, 2),
    }
