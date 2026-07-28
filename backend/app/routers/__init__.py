from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.inventory import router as inventory_router
from app.routers.orders import router as orders_router
from app.routers.delivery_routes import router as delivery_routes_router, routes_router
from app.routers.route_stops import router as route_stops_router

__all__ = [
    "auth_router",
    "products_router",
    "inventory_router",
    "orders_router",
    "delivery_routes_router",
    "routes_router",
    "route_stops_router",
]
