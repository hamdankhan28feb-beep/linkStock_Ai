from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.delivery import RouteStatus, StopStatus


# ─── Route Stop ────────────────────────────────────────────────────────────────

class RouteStopOut(BaseModel):
    id: UUID
    route_id: UUID
    order_id: UUID
    retailer_id: UUID
    stop_sequence: int
    latitude: float
    longitude: float
    address: Optional[str] = None
    retailer_name: Optional[str] = None
    order_total: Optional[Decimal] = None
    status: StopStatus
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class RouteStopComplete(BaseModel):
    notes: Optional[str] = None


# ─── Delivery Route ────────────────────────────────────────────────────────────

class DeliveryRouteOut(BaseModel):
    id: UUID
    distributor_id: UUID
    name: Optional[str] = None
    cluster_label: int
    status: RouteStatus
    depot_latitude: Optional[float] = None
    depot_longitude: Optional[float] = None
    depot_address: Optional[str] = None
    total_distance_km: Optional[float] = None
    total_stops: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stops: List[RouteStopOut] = []

    model_config = {"from_attributes": True}


class DeliveryRouteSummary(BaseModel):
    """Lightweight summary for route list view."""
    id: UUID
    name: Optional[str] = None
    cluster_label: int
    status: RouteStatus
    total_stops: Optional[int] = None
    total_distance_km: Optional[float] = None
    created_at: datetime
    completed_stops: Optional[int] = None

    model_config = {"from_attributes": True}


# ─── Cluster Generation Request ───────────────────────────────────────────────

class ClusterGenerateRequest(BaseModel):
    eps_km: float = 5.0           # clustering radius in km
    min_samples: int = 2           # minimum orders per cluster
    depot_latitude: Optional[float] = None
    depot_longitude: Optional[float] = None
    depot_address: Optional[str] = None


class ClusterGenerateResponse(BaseModel):
    clusters_created: int
    orders_clustered: int
    noise_orders: int              # singleton orders (DBSCAN label = -1)
    routes: List[DeliveryRouteSummary]


# ─── Route Optimization ───────────────────────────────────────────────────────

class RouteOptimizeResponse(BaseModel):
    route_id: UUID
    total_stops: int
    total_distance_km: float
    stops: List[RouteStopOut]
