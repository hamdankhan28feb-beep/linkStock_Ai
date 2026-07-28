# LinkStock AI — Complete Hackathon MVP Implementation Plan

## Overview

LinkStock AI is an AI-powered FMCG supply-chain platform that connects three actor roles — **Warehouse**, **Distributor**, and **Retailer** — in a single cohesive workflow. The core innovation is automatic DBSCAN-based geographic clustering of pending retailer orders, followed by Google OR-Tools VRP route optimization rendered on an interactive Leaflet/OpenStreetMap map.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript |
| Styling | Tailwind CSS v3 |
| Backend | Python 3.11, FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.x (async) + Alembic migrations |
| Auth | JWT (python-jose) + bcrypt |
| AI Clustering | scikit-learn DBSCAN |
| Route Optimization | Google OR-Tools (VRP) |
| Maps | Leaflet.js + OpenStreetMap tiles |
| Package Mgmt | pnpm (frontend), pip/venv (backend) |

---

## Monorepo Folder Structure

```
linkstock-ai/
│
├── frontend/                          # Next.js App
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root layout, providers
│   │   │   ├── page.tsx               # Landing / redirect
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   ├── retailer/
│   │   │   │   ├── layout.tsx         # Retailer sidebar layout
│   │   │   │   ├── dashboard/page.tsx
│   │   │   │   ├── products/page.tsx  # Browse & order
│   │   │   │   └── orders/page.tsx    # My orders history
│   │   │   ├── distributor/
│   │   │   │   ├── layout.tsx         # Distributor sidebar layout
│   │   │   │   ├── dashboard/page.tsx
│   │   │   │   ├── orders/page.tsx    # Pending order list
│   │   │   │   ├── clusters/page.tsx  # AI cluster view
│   │   │   │   └── route/[clusterId]/page.tsx  # Optimized route + map
│   │   │   └── warehouse/
│   │   │       ├── layout.tsx
│   │   │       ├── dashboard/page.tsx
│   │   │       └── inventory/page.tsx # Stock management + alerts
│   │   ├── components/
│   │   │   ├── ui/                    # Reusable: Button, Card, Badge, Modal
│   │   │   ├── auth/                  # LoginForm, AuthGuard
│   │   │   ├── map/
│   │   │   │   ├── RouteMap.tsx       # Leaflet dynamic map
│   │   │   │   └── ClusterMap.tsx     # Cluster visualization
│   │   │   ├── orders/
│   │   │   │   ├── OrderCard.tsx
│   │   │   │   └── OrderForm.tsx
│   │   │   ├── inventory/
│   │   │   │   ├── ProductCard.tsx
│   │   │   │   └── LowStockAlert.tsx
│   │   │   └── layout/
│   │   │       ├── Sidebar.tsx
│   │   │       └── Navbar.tsx
│   │   ├── context/
│   │   │   └── AuthContext.tsx        # JWT token, user role
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useOrders.ts
│   │   │   └── useInventory.ts
│   │   ├── lib/
│   │   │   ├── api.ts                 # Axios client with auth headers
│   │   │   └── utils.ts
│   │   └── types/
│   │       └── index.ts               # Shared TypeScript types
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   └── package.json
│
├── backend/                           # FastAPI App
│   ├── app/
│   │   ├── main.py                    # App entrypoint, CORS, router mount
│   │   ├── config.py                  # Settings (env vars via pydantic-settings)
│   │   ├── database.py                # Async SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # User, Role
│   │   │   ├── product.py             # Product
│   │   │   ├── inventory.py           # Inventory
│   │   │   ├── order.py               # Order, OrderItem
│   │   │   └── delivery.py            # DeliveryCluster, DeliveryStop
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── order.py
│   │   │   ├── inventory.py
│   │   │   └── delivery.py
│   │   ├── routers/
│   │   │   ├── auth.py                # /api/auth/login, /register, /me
│   │   │   ├── products.py            # /api/products
│   │   │   ├── inventory.py           # /api/inventory
│   │   │   ├── orders.py              # /api/orders
│   │   │   ├── clusters.py            # /api/clusters (DBSCAN trigger)
│   │   │   └── routes.py              # /api/routes/{cluster_id} (OR-Tools)
│   │   ├── services/
│   │   │   ├── auth_service.py        # JWT encode/decode, password hash
│   │   │   ├── clustering_service.py  # DBSCAN logic
│   │   │   ├── routing_service.py     # OR-Tools VRP solver
│   │   │   └── inventory_service.py   # Stock deduction, alert generation
│   │   ├── dependencies.py            # get_db, get_current_user
│   │   └── alembic/                   # DB migration files
│   ├── requirements.txt
│   ├── .env.example
│   └── seed.py                        # Demo data seeder
│
├── .env                               # Shared secrets (gitignored)
└── README.md
```

---

## Database Schema

### Table: `users`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(100) | |
| email | VARCHAR(150) | UNIQUE |
| password_hash | TEXT | bcrypt |
| role | ENUM | `warehouse`, `distributor`, `retailer` |
| latitude | FLOAT | For retailer geo-clustering |
| longitude | FLOAT | For retailer geo-clustering |
| address | TEXT | Human-readable |
| created_at | TIMESTAMP | |

### Table: `products`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(200) | |
| sku | VARCHAR(50) | UNIQUE |
| category | VARCHAR(100) | |
| unit_price | DECIMAL(10,2) | |
| unit | VARCHAR(20) | e.g. "carton", "kg" |
| image_url | TEXT | |
| created_at | TIMESTAMP | |

### Table: `inventory`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| product_id | UUID FK → products | |
| warehouse_id | UUID FK → users | |
| quantity | INTEGER | Current stock |
| low_stock_threshold | INTEGER | Default 50 |
| updated_at | TIMESTAMP | |

### Table: `orders`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| retailer_id | UUID FK → users | |
| distributor_id | UUID FK → users | nullable until assigned |
| status | ENUM | `pending`, `clustered`, `in_transit`, `delivered` |
| total_amount | DECIMAL(10,2) | |
| notes | TEXT | |
| created_at | TIMESTAMP | |
| delivered_at | TIMESTAMP | |

### Table: `order_items`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| order_id | UUID FK → orders | |
| product_id | UUID FK → products | |
| quantity | INTEGER | |
| unit_price | DECIMAL(10,2) | Snapshot at order time |

### Table: `delivery_clusters`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| distributor_id | UUID FK → users | |
| cluster_label | INTEGER | DBSCAN cluster ID |
| status | ENUM | `pending`, `in_progress`, `completed` |
| created_at | TIMESTAMP | |

### Table: `delivery_stops`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| cluster_id | UUID FK → delivery_clusters | |
| order_id | UUID FK → orders | |
| stop_sequence | INTEGER | OR-Tools output order |
| latitude | FLOAT | Retailer lat (denormalized for speed) |
| longitude | FLOAT | Retailer lon |
| status | ENUM | `pending`, `completed` |
| completed_at | TIMESTAMP | |

### Table: `low_stock_alerts`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| inventory_id | UUID FK → inventory | |
| triggered_at | TIMESTAMP | |
| resolved_at | TIMESTAMP | nullable |
| is_read | BOOLEAN | Default false |

---

## API Architecture

### Auth Routes (`/api/auth`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/register` | Public | Register user with role |
| POST | `/login` | Public | Returns JWT access token |
| GET | `/me` | Any | Get current user profile |

### Product Routes (`/api/products`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/` | Any | List all products with current stock |
| POST | `/` | Warehouse | Create product |
| PUT | `/{id}` | Warehouse | Update product |

### Inventory Routes (`/api/inventory`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/` | Warehouse | All inventory items + alerts |
| PATCH | `/{id}` | Warehouse | Manually adjust stock |
| GET | `/alerts` | Warehouse | Low stock alerts |

### Order Routes (`/api/orders`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/` | Retailer | Place a new order |
| GET | `/` | Retailer/Dist | List orders (filtered by role) |
| GET | `/{id}` | Any | Get order detail |

### Cluster Routes (`/api/clusters`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/generate` | Distributor | Trigger DBSCAN on pending orders |
| GET | `/` | Distributor | List existing clusters |
| GET | `/{id}` | Distributor | Cluster detail with orders |

### Route Routes (`/api/routes`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/{cluster_id}/optimize` | Distributor | Trigger OR-Tools VRP solver |
| GET | `/{cluster_id}` | Distributor | Get optimized stops list |
| PATCH | `/{cluster_id}/stops/{stop_id}/complete` | Distributor | Mark stop delivered → deduct inventory |

---

## AI & Optimization Services

### 1. DBSCAN Clustering (`clustering_service.py`)
- Fetches all `pending` orders with retailer lat/lon
- Runs `sklearn.cluster.DBSCAN(eps=0.05, min_samples=2)` on `[lat, lon]` pairs
- `eps` represents ~5km radius (degrees ≈ km / 111)
- Creates `DeliveryCluster` records per unique cluster label (noise points = solo delivery)
- Each order's status → `clustered`

### 2. OR-Tools VRP (`routing_service.py`)
- Input: list of stops (lat/lon) + depot (distributor warehouse lat/lon)
- Builds distance matrix using Haversine formula
- Configures single-vehicle VRP with `ortools.constraint_solver`
- Uses `PATH_CHEAPEST_ARC` first-solution strategy
- Returns ordered list of stop IDs with sequence numbers
- Saves `stop_sequence` to `delivery_stops`

### 3. Inventory Deduction (`inventory_service.py`)
- On stop completion: deduct `order_item.quantity` from `inventory.quantity`
- If `quantity < low_stock_threshold`: create `LowStockAlert`
- Returns updated inventory state

---

## Frontend Architecture

### Auth Flow
- `AuthContext` stores JWT + decoded `{ userId, role, name }`
- Role-based redirects: `/retailer/dashboard`, `/distributor/dashboard`, `/warehouse/dashboard`
- `AuthGuard` HOC wraps all protected routes

### Key Pages

#### Retailer
1. **Products** (`/retailer/products`) — product grid with "Add to Cart" → submit order
2. **Orders** (`/retailer/orders`) — list of past orders with status badges

#### Distributor
1. **Orders** (`/distributor/orders`) — table of pending orders with retailer names/addresses
2. **Clusters** (`/distributor/clusters`) — "Generate Clusters" button → calls DBSCAN API → shows cluster cards with order count
3. **Route View** (`/distributor/route/[clusterId]`) — "Optimize Route" button → calls OR-Tools API → renders Leaflet map with numbered stop markers + polyline → "Complete Stop" buttons

#### Warehouse
1. **Inventory** (`/warehouse/inventory`) — product table with current stock, edit qty, low-stock alert panel

### Map Component (`RouteMap.tsx`)
- Dynamically imported (SSR disabled) using `next/dynamic`
- Renders OpenStreetMap tiles via `react-leaflet`
- Shows depot marker (truck icon) + numbered stop markers
- Draws `Polyline` connecting stops in optimized sequence
- Popup on each marker: retailer name, address, order total

---

## Development Phases

### Phase 1 — Foundation (Day 1 AM)
- [ ] Initialize Next.js + Tailwind in `/frontend`
- [ ] Initialize FastAPI + SQLAlchemy + Alembic in `/backend`
- [ ] Create PostgreSQL DB + run initial migration
- [ ] Implement `users`, `products`, `inventory` models + auth endpoints
- [ ] Build Login/Register pages, AuthContext

### Phase 2 — Core Order Flow (Day 1 PM)
- [ ] Implement `orders`, `order_items` models + CRUD endpoints
- [ ] Build Retailer: Products page (browse + place order)
- [ ] Build Retailer: Orders history page
- [ ] Build Distributor: Pending orders list
- [ ] Seed demo data (3 retailers with geo coords, 10 products, 15 orders)

### Phase 3 — AI Clustering (Day 2 AM)
- [ ] Implement DBSCAN clustering service
- [ ] Build `/api/clusters/generate` endpoint
- [ ] Build Distributor Clusters page
- [ ] Add cluster map visualization (markers only, no route yet)

### Phase 4 — Route Optimization & Map (Day 2 PM)
- [ ] Implement OR-Tools VRP routing service
- [ ] Build `/api/routes/{cluster_id}/optimize` endpoint
- [ ] Build Route View page with Leaflet map
- [ ] Implement stop completion → inventory deduction flow
- [ ] Build Warehouse inventory + alerts page

### Phase 5 — Polish & Demo (Day 3)
- [ ] Add real-time low-stock badge in warehouse sidebar
- [ ] Add order status tracking badges
- [ ] Final UI polish (animations, empty states, loading skeletons)
- [ ] Write `seed.py` with realistic demo data
- [ ] README + demo walkthrough

---

## Open Questions

> [!IMPORTANT]
> **Depot Location**: What coordinates should be used for the distributor's warehouse depot (the VRP start/end point)? I'll hardcode a sensible default for the demo unless you prefer a specific city.

> [!IMPORTANT]
> **Number of Vehicles**: The MVP uses a single delivery vehicle per cluster. Should multi-vehicle VRP be supported (one truck per cluster simultaneously)?

> [!NOTE]
> **Real-time updates**: Should the distributor's order list auto-refresh via polling, or is a manual refresh button acceptable for the MVP?

> [!NOTE]
> **Authentication scope**: Should the Register page let any user pick their role, or should Warehouse and Distributor accounts be pre-seeded by an admin?

> [!NOTE]
> **Map tiles**: OpenStreetMap tiles are used (free, no API key). Should any other premium tile provider (Mapbox, Stadia) be used for better visuals?

---

## Verification Plan

### Backend
- Run `pytest` against auth, order creation, clustering, and routing endpoints
- Verify DBSCAN groups nearby retailers correctly with test coordinates
- Verify OR-Tools returns a valid ordered route (depot → stops → depot)

### Frontend
- Manual walkthrough: Retailer login → place order → Distributor login → generate clusters → optimize route → complete stops
- Verify inventory deduction reflects on Warehouse dashboard
- Verify low-stock alert appears after deduction

### Integration
- End-to-end test: place 6 orders from 3 retailers in 2 geographic zones → expect 2 clusters → 2 separate routes
