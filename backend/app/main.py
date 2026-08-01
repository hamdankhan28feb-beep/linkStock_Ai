"""
LinkStock AI — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

from app.routers import (
    auth_router,
    products_router,
    inventory_router,
    orders_router,
    delivery_routes_router,
    routes_router,
    route_stops_router,
)
from fastapi import status


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[OK] {settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"[INFO] Using Supabase REST API for data access.")
    print(f"[INFO] Docs: http://localhost:8000/docs")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered FMCG supply-chain platform connecting Warehouse, Distributor, and Retailer",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    redirect_slashes=True,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(orders_router)
app.include_router(delivery_routes_router)
app.include_router(routes_router)
app.include_router(route_stops_router)



# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["Health"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }


@app.post("/api/ext/activate", tags=["Extensions"])
def activate_extension():
    return {"ok": True, "status": "activated", "service": "fastapi"}


@app.post("/api/ext/auth-token", tags=["Extensions"])
def auth_token_extension():
    return {"ok": True, "status": "token-ready", "service": "fastapi"}
