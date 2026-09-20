"""
Vehicle Routing Engine — Pure Python Implementation.
No Django imports.
Implements D3 §9, §12:
Vehicle assignment, distance matrix with road factor 1.35, and nearest-neighbour / CVRP sequence solver.
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple


@dataclass
class RouteNode:
    id: str
    name: str
    latitude: float
    longitude: float
    demand_kg: float
    node_type: str  # BASE | PICKUP | AGGREGATION | DELIVERY


@dataclass
class RouteSolution:
    vehicle_id: str
    stop_sequence: List[Dict[str, Any]]
    total_distance_km: float
    total_duration_hours: float
    solver: str
    is_feasible: bool
    error_message: str = ""


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float, road_factor: float = 1.35) -> float:
    """Great-circle distance multiplied by rural road detour factor (1.35)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c * road_factor, 2)


def solve_cvrp_route(
    depot_node: RouteNode,
    pickup_nodes: List[RouteNode],
    delivery_node: RouteNode,
    vehicle_capacity_kg: float,
    vehicle_id: str,
    avg_speed_kmph: float = 35.0
) -> RouteSolution:
    """
    Capacity-constrained sequence optimization.
    Route: Depot -> Pickups (sequenced nearest-neighbour) -> Delivery.
    """
    total_demand = sum(p.demand_kg for p in pickup_nodes)
    if total_demand > vehicle_capacity_kg:
        return RouteSolution(
            vehicle_id=vehicle_id,
            stop_sequence=[],
            total_distance_km=0.0,
            total_duration_hours=0.0,
            solver="FAILED",
            is_feasible=False,
            error_message=f"Total load {total_demand}kg exceeds vehicle capacity {vehicle_capacity_kg}kg."
        )

    # Nearest-neighbour ordering of pickup stops
    unvisited = list(pickup_nodes)
    current_lat, current_lon = depot_node.latitude, depot_node.longitude
    ordered_pickups: List[RouteNode] = []

    while unvisited:
        nearest_idx = 0
        min_dist = float('inf')
        for idx, node in enumerate(unvisited):
            d = haversine_km(current_lat, current_lon, node.latitude, node.longitude)
            if d < min_dist:
                min_dist = d
                nearest_idx = idx
        chosen = unvisited.pop(nearest_idx)
        ordered_pickups.append(chosen)
        current_lat, current_lon = chosen.latitude, chosen.longitude

    # Full sequence: Depot -> Pickups -> Delivery
    sequence = []
    total_km = 0.0
    cur_lat, cur_lon = depot_node.latitude, depot_node.longitude

    # Depot
    sequence.append({
        "sequence": 1,
        "stop_type": "BASE",
        "name": depot_node.name,
        "latitude": depot_node.latitude,
        "longitude": depot_node.longitude,
        "quantity_kg": 0.0,
        "cumulative_distance_km": 0.0
    })

    seq_num = 2
    for p in ordered_pickups:
        d = haversine_km(cur_lat, cur_lon, p.latitude, p.longitude)
        total_km += d
        sequence.append({
            "sequence": seq_num,
            "stop_type": "PICKUP",
            "contribution_id": p.id,
            "name": p.name,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "quantity_kg": p.demand_kg,
            "cumulative_distance_km": round(total_km, 2)
        })
        cur_lat, cur_lon = p.latitude, p.longitude
        seq_num += 1

    # Delivery
    d = haversine_km(cur_lat, cur_lon, delivery_node.latitude, delivery_node.longitude)
    total_km += d
    sequence.append({
        "sequence": seq_num,
        "stop_type": "DELIVERY",
        "name": delivery_node.name,
        "latitude": delivery_node.latitude,
        "longitude": delivery_node.longitude,
        "quantity_kg": total_demand,
        "cumulative_distance_km": round(total_km, 2)
    })

    duration_hours = round(total_km / avg_speed_kmph, 2)

    return RouteSolution(
        vehicle_id=vehicle_id,
        stop_sequence=sequence,
        total_distance_km=round(total_km, 2),
        total_duration_hours=duration_hours,
        solver="NEAREST_NEIGHBOUR_FALLBACK",
        is_feasible=True
    )
