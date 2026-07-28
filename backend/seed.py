"""
LinkStock AI — Database Seed Script
Populates the database with realistic demo data:
  - 1 Warehouse admin
  - 2 Distributors (Karachi)
  - 10 Retailers (spread across Karachi with GPS coordinates)
  - 20 FMCG products
  - Inventory for each product
  - 15 sample orders from retailers
"""
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from app.database import SessionLocal, create_tables
import app.models  # noqa — register all models

from app.models.user import User, UserRole
from app.models.location import Location
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem, OrderStatus
from app.services.auth_service import hash_password


# ─── Demo Users ───────────────────────────────────────────────────────────────

WAREHOUSE = {
    "name": "LinkStock Warehouse Admin",
    "email": "warehouse@linkstock.ai",
    "password": "warehouse123",
    "phone": "+92-21-35001234",
    "role": UserRole.warehouse,
    "location": {
        "address": "Plot ST-1, Bin Qasim Industrial Zone, Port Qasim",
        "area": "Port Qasim",
        "city": "Karachi",
        "latitude": 24.7910,
        "longitude": 67.1530,
    },
}

DISTRIBUTORS = [
    {
        "name": "Ali Traders Distribution",
        "email": "ali.dist@linkstock.ai",
        "password": "dist123",
        "phone": "+92-21-32561234",
        "role": UserRole.distributor,
        "location": {
            "address": "Plot 45, SITE Industrial Area, Karachi",
            "area": "SITE Area",
            "city": "Karachi",
            "latitude": 24.8850,
            "longitude": 67.0100,
        },
    },
    {
        "name": "Korangi Express Logistics",
        "email": "korangi.dist@linkstock.ai",
        "password": "dist123",
        "phone": "+92-21-35121234",
        "role": UserRole.distributor,
        "location": {
            "address": "Sector 23, Korangi Industrial Area, Karachi",
            "area": "Korangi Industrial",
            "city": "Karachi",
            "latitude": 24.8300,
            "longitude": 67.1200,
        },
    },
]

# 10 Retailers spread across Karachi for good DBSCAN clustering demo
# Designed so ~6 cluster into 2 groups, ~4 are outliers
RETAILERS = [
    # Cluster 1: North Karachi / Gulshan area
    {
        "name": "Gulshan General Store",
        "email": "gulshan@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234501",
        "role": UserRole.retailer,
        "location": {
            "address": "Shop 12, Main Rashid Minhas Road, Gulshan-e-Iqbal Block 7",
            "area": "Gulshan-e-Iqbal",
            "city": "Karachi",
            "latitude": 24.9215,
            "longitude": 67.0977,
        },
    },
    {
        "name": "North City Mart",
        "email": "northcity@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234502",
        "role": UserRole.retailer,
        "location": {
            "address": "Block 11, North Karachi Township",
            "area": "North Karachi",
            "city": "Karachi",
            "latitude": 24.9750,
            "longitude": 67.0614,
        },
    },
    {
        "name": "Nazimabad Provisions",
        "email": "nazimabad@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234503",
        "role": UserRole.retailer,
        "location": {
            "address": "Shop 5, Nazimabad No.3, Near Nagan Chowrangi",
            "area": "Nazimabad",
            "city": "Karachi",
            "latitude": 24.9062,
            "longitude": 67.0488,
        },
    },
    # Cluster 2: South Karachi / Clifton / DHA area
    {
        "name": "Clifton Super Store",
        "email": "clifton@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234504",
        "role": UserRole.retailer,
        "location": {
            "address": "Block 4, Clifton, Near Do Talwar",
            "area": "Clifton",
            "city": "Karachi",
            "latitude": 24.8143,
            "longitude": 67.0322,
        },
    },
    {
        "name": "DHA Food Palace",
        "email": "dha@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234505",
        "role": UserRole.retailer,
        "location": {
            "address": "Phase 6, DHA, Bukhari Commercial Lane 2",
            "area": "DHA Phase 6",
            "city": "Karachi",
            "latitude": 24.7935,
            "longitude": 67.0748,
        },
    },
    {
        "name": "Saddar Quick Mart",
        "email": "saddar@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234506",
        "role": UserRole.retailer,
        "location": {
            "address": "Shop 22, Zaibunissa Street, Saddar",
            "area": "Saddar",
            "city": "Karachi",
            "latitude": 24.8569,
            "longitude": 67.0104,
        },
    },
    # Cluster 3: East Karachi
    {
        "name": "Korangi Family Store",
        "email": "korangi@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234507",
        "role": UserRole.retailer,
        "location": {
            "address": "Sector 31-G, Korangi Town",
            "area": "Korangi",
            "city": "Karachi",
            "latitude": 24.8361,
            "longitude": 67.1310,
        },
    },
    {
        "name": "Landhi Daily Needs",
        "email": "landhi@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234508",
        "role": UserRole.retailer,
        "location": {
            "address": "Block 6, Landhi Town, Main Road",
            "area": "Landhi",
            "city": "Karachi",
            "latitude": 24.8558,
            "longitude": 67.1820,
        },
    },
    # Outlier retailers (will be solo clusters or noise)
    {
        "name": "Malir Super Center",
        "email": "malir@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234509",
        "role": UserRole.retailer,
        "location": {
            "address": "Malir City, Near Malir Halt Station",
            "area": "Malir",
            "city": "Karachi",
            "latitude": 24.8943,
            "longitude": 67.2001,
        },
    },
    {
        "name": "Orangi Town Wholesale",
        "email": "orangi@retailer.com",
        "password": "retail123",
        "phone": "+92-333-1234510",
        "role": UserRole.retailer,
        "location": {
            "address": "Sector 11/2, Orangi Town",
            "area": "Orangi Town",
            "city": "Karachi",
            "latitude": 24.9545,
            "longitude": 66.9901,
        },
    },
]


# ─── 20 FMCG Products ─────────────────────────────────────────────────────────

PRODUCTS = [
    # Edible Oils
    {"name": "Dalda Cooking Oil 5L", "sku": "DALDA-5L", "category": "Edible Oils",
     "description": "Dalda banaspati ghee substitute cooking oil, 5 litre tin", "unit_price": 1850.00, "unit": "tin"},
    {"name": "Sufi Sunflower Oil 3L", "sku": "SUFI-3L", "category": "Edible Oils",
     "description": "Sufi sunflower cooking oil, 3 litre PET bottle", "unit_price": 1240.00, "unit": "bottle"},
    {"name": "Habib Canola Oil 1L", "sku": "HABIB-CANOLA-1L", "category": "Edible Oils",
     "description": "Habib canola oil, 1 litre bottle", "unit_price": 495.00, "unit": "bottle"},

    # Flour & Grains
    {"name": "Sunridge Flour 10kg", "sku": "SUNRIDGE-FLOUR-10", "category": "Flour & Grains",
     "description": "Premium wheat flour, 10 kg bag", "unit_price": 950.00, "unit": "bag"},
    {"name": "Basmati Rice Premium 5kg", "sku": "BASMATI-5KG", "category": "Flour & Grains",
     "description": "Super Kernel Basmati rice, 5 kg pack", "unit_price": 1450.00, "unit": "pack"},
    {"name": "Maize Flour 2kg", "sku": "MAIZE-2KG", "category": "Flour & Grains",
     "description": "Yellow maize flour, 2 kg pack", "unit_price": 280.00, "unit": "pack"},

    # Sugar & Sweeteners
    {"name": "Refined Sugar 1kg", "sku": "SUGAR-1KG", "category": "Sugar & Sweeteners",
     "description": "White refined cane sugar, 1 kg packet", "unit_price": 175.00, "unit": "packet"},
    {"name": "Brown Sugar 500g", "sku": "BROWN-SUGAR-500G", "category": "Sugar & Sweeteners",
     "description": "Natural brown cane sugar, 500g pouch", "unit_price": 145.00, "unit": "pouch"},

    # Tea & Beverages
    {"name": "Tapal Danedar 900g", "sku": "TAPAL-900G", "category": "Tea & Beverages",
     "description": "Tapal Danedar black tea, 900g jar", "unit_price": 980.00, "unit": "jar"},
    {"name": "Lipton Yellow Label 400g", "sku": "LIPTON-400G", "category": "Tea & Beverages",
     "description": "Lipton Yellow Label tea bags box, 400g", "unit_price": 760.00, "unit": "box"},
    {"name": "Nestle Milo 400g", "sku": "MILO-400G", "category": "Tea & Beverages",
     "description": "Milo chocolate malt drink, 400g tin", "unit_price": 620.00, "unit": "tin"},

    # Dairy
    {"name": "Olpers Full Cream Milk 1L", "sku": "OLPERS-1L", "category": "Dairy",
     "description": "Olpers full cream UHT milk, 1 litre Tetra Pak", "unit_price": 285.00, "unit": "pack"},
    {"name": "Nestle Yoghurt 1kg", "sku": "NESTLE-YOGURT-1KG", "category": "Dairy",
     "description": "Nestle plain yoghurt, 1 kg cup", "unit_price": 340.00, "unit": "cup"},

    # Spices & Condiments
    {"name": "National Biryani Masala 50g", "sku": "NATL-BIRYANI-50G", "category": "Spices",
     "description": "National Biryani mix spice, 50g packet", "unit_price": 85.00, "unit": "packet"},
    {"name": "Shan Karahi Masala 100g", "sku": "SHAN-KARAHI-100G", "category": "Spices",
     "description": "Shan Karahi gosht spice mix, 100g", "unit_price": 120.00, "unit": "packet"},
    {"name": "Heinz Tomato Ketchup 800g", "sku": "HEINZ-KETCHUP-800G", "category": "Spices",
     "description": "Heinz classic tomato ketchup, 800g squeeze bottle", "unit_price": 395.00, "unit": "bottle"},

    # Hygiene & Cleaning
    {"name": "Surf Excel 1kg", "sku": "SURF-EXCEL-1KG", "category": "Cleaning",
     "description": "Surf Excel laundry detergent powder, 1 kg pack", "unit_price": 420.00, "unit": "pack"},
    {"name": "Safeguard Soap Bar (Pack of 4)", "sku": "SAFEGUARD-4PK", "category": "Hygiene",
     "description": "Safeguard antibacterial soap bars, pack of 4×115g", "unit_price": 380.00, "unit": "pack"},

    # Snacks
    {"name": "Lays Classic Chips 34g (Box of 24)", "sku": "LAYS-34G-24PK", "category": "Snacks",
     "description": "Lay's salted potato chips 34g, carton of 24 packets", "unit_price": 1440.00, "unit": "carton"},
    {"name": "Peek Freans Sooper Biscuits 6pk", "sku": "SOOPER-6PK", "category": "Snacks",
     "description": "Peek Freans Sooper biscuits, 6-pack family bundle", "unit_price": 290.00, "unit": "bundle"},
]

# ─── Inventory quantities per product ─────────────────────────────────────────
# (quantity, low_stock_threshold)
INVENTORY_DATA = {
    "DALDA-5L":         (180, 30),
    "SUFI-3L":          (240, 40),
    "HABIB-CANOLA-1L":  (320, 50),
    "SUNRIDGE-FLOUR-10":(150, 25),
    "BASMATI-5KG":      (200, 30),
    "MAIZE-2KG":        (180, 30),
    "SUGAR-1KG":        (500, 80),
    "BROWN-SUGAR-500G": (220, 40),
    "TAPAL-900G":       (120, 20),
    "LIPTON-400G":      (140, 25),
    "MILO-400G":        (90,  15),
    "OLPERS-1L":        (300, 50),
    "NESTLE-YOGURT-1KG":(80,  15),
    "NATL-BIRYANI-50G": (400, 60),
    "SHAN-KARAHI-100G": (350, 55),
    "HEINZ-KETCHUP-800G":(160, 25),
    "SURF-EXCEL-1KG":   (210, 35),
    "SAFEGUARD-4PK":    (180, 30),
    "LAYS-34G-24PK":    (95,  15),
    "SOOPER-6PK":       (130, 20),
}

# ─── Sample Orders ─────────────────────────────────────────────────────────────
# (retailer_email, [(sku, qty), ...])
SAMPLE_ORDERS = [
    ("gulshan@retailer.com", [
        ("SUGAR-1KG", 20),
        ("TAPAL-900G", 5),
        ("OLPERS-1L", 12),
        ("SURF-EXCEL-1KG", 8),
    ]),
    ("gulshan@retailer.com", [
        ("DALDA-5L", 6),
        ("SUNRIDGE-FLOUR-10", 10),
        ("NATL-BIRYANI-50G", 20),
    ]),
    ("northcity@retailer.com", [
        ("BASMATI-5KG", 8),
        ("SUGAR-1KG", 15),
        ("LIPTON-400G", 6),
        ("LAYS-34G-24PK", 3),
    ]),
    ("nazimabad@retailer.com", [
        ("SUFI-3L", 10),
        ("SURF-EXCEL-1KG", 12),
        ("SAFEGUARD-4PK", 10),
        ("SOOPER-6PK", 8),
    ]),
    ("clifton@retailer.com", [
        ("DALDA-5L", 8),
        ("NESTLE-YOGURT-1KG", 10),
        ("MILO-400G", 6),
        ("HEINZ-KETCHUP-800G", 4),
    ]),
    ("clifton@retailer.com", [
        ("LIPTON-400G", 10),
        ("TAPAL-900G", 4),
        ("BROWN-SUGAR-500G", 8),
    ]),
    ("dha@retailer.com", [
        ("OLPERS-1L", 20),
        ("NESTLE-YOGURT-1KG", 8),
        ("MILO-400G", 10),
        ("SOOPER-6PK", 12),
    ]),
    ("saddar@retailer.com", [
        ("SUNRIDGE-FLOUR-10", 15),
        ("SUGAR-1KG", 25),
        ("NATL-BIRYANI-50G", 30),
        ("SHAN-KARAHI-100G", 20),
    ]),
    ("korangi@retailer.com", [
        ("DALDA-5L", 12),
        ("SUFI-3L", 8),
        ("SURF-EXCEL-1KG", 10),
        ("SAFEGUARD-4PK", 15),
    ]),
    ("landhi@retailer.com", [
        ("BASMATI-5KG", 12),
        ("MAIZE-2KG", 10),
        ("SUGAR-1KG", 20),
        ("LAYS-34G-24PK", 5),
    ]),
    ("malir@retailer.com", [
        ("TAPAL-900G", 8),
        ("OLPERS-1L", 15),
        ("HABIB-CANOLA-1L", 10),
    ]),
    ("orangi@retailer.com", [
        ("SUNRIDGE-FLOUR-10", 20),
        ("SUGAR-1KG", 30),
        ("NATL-BIRYANI-50G", 25),
        ("SHAN-KARAHI-100G", 15),
    ]),
    ("northcity@retailer.com", [
        ("SURF-EXCEL-1KG", 15),
        ("SAFEGUARD-4PK", 12),
        ("SOOPER-6PK", 10),
    ]),
    ("dha@retailer.com", [
        ("HABIB-CANOLA-1L", 8),
        ("BROWN-SUGAR-500G", 12),
        ("HEINZ-KETCHUP-800G", 6),
    ]),
    ("gulshan@retailer.com", [
        ("LAYS-34G-24PK", 4),
        ("SOOPER-6PK", 6),
        ("MILO-400G", 5),
        ("LIPTON-400G", 8),
    ]),
]


# ─── Seed Function ────────────────────────────────────────────────────────────

def seed():
    print("[*] Starting database seed...")
    create_tables()
    db = SessionLocal()

    try:
        # Check if already seeded
        existing = db.query(User).filter(User.email == WAREHOUSE["email"]).first()
        if existing:
            print("[!] Database already seeded. Skipping.")
            print("    To re-seed: drop all tables and run again.")
            return

        print("  Creating warehouse admin...")
        warehouse_user = _create_user(db, WAREHOUSE)
        db.flush()

        print("  Creating distributors...")
        distributor_users = []
        for d in DISTRIBUTORS:
            u = _create_user(db, d)
            distributor_users.append(u)
        db.flush()

        print("  Creating retailers...")
        retailer_map = {}
        for r in RETAILERS:
            u = _create_user(db, r)
            retailer_map[r["email"]] = u
        db.flush()

        print("  Creating products & inventory...")
        product_map = {}
        for p_data in PRODUCTS:
            product = Product(
                name=p_data["name"],
                sku=p_data["sku"],
                category=p_data["category"],
                description=p_data.get("description"),
                unit_price=Decimal(str(p_data["unit_price"])),
                unit=p_data["unit"],
                is_active=True,
            )
            db.add(product)
            db.flush()

            qty, threshold = INVENTORY_DATA.get(p_data["sku"], (100, 20))
            inv = Inventory(
                product_id=product.id,
                warehouse_user_id=warehouse_user.id,
                quantity=qty,
                low_stock_threshold=threshold,
            )
            db.add(inv)
            product_map[p_data["sku"]] = product

        db.flush()

        print("  Creating sample orders...")
        for retailer_email, items_data in SAMPLE_ORDERS:
            retailer = retailer_map.get(retailer_email)
            if not retailer:
                print(f"    [!] Retailer {retailer_email} not found, skipping order")
                continue

            order = Order(
                retailer_id=retailer.id,
                status=OrderStatus.pending,
                total_amount=0,
            )
            db.add(order)
            db.flush()

            total = Decimal("0.00")
            for sku, qty in items_data:
                product = product_map.get(sku)
                if not product:
                    print(f"    [!] Product {sku} not found, skipping item")
                    continue
                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=product.unit_price,
                )
                db.add(item)
                total += product.unit_price * qty

            order.total_amount = total
            db.flush()

        db.commit()
        print()
        print("[OK] Seed completed successfully!")
        print()
        print("=" * 55)
        print("  Demo Credentials")
        print("=" * 55)
        print("  [W] Warehouse    : warehouse@linkstock.ai / warehouse123")
        print("  [D] Distributor 1: ali.dist@linkstock.ai / dist123")
        print("  [D] Distributor 2: korangi.dist@linkstock.ai / dist123")
        print("  [R] Retailer     : gulshan@retailer.com / retail123")
        print("  [R] Retailer     : clifton@retailer.com / retail123")
        print("  [R] Retailer     : dha@retailer.com / retail123")
        print("=" * 55)
        print(f"  Products : {len(PRODUCTS)}")
        print(f"  Orders   : {len(SAMPLE_ORDERS)}")
        print(f"  Users    : {1 + len(DISTRIBUTORS) + len(RETAILERS)}")
        print("=" * 55)

    except Exception as e:
        db.rollback()
        print(f"[FAIL] Seed failed: {e}")
        raise
    finally:
        db.close()


def _create_user(db, user_data: dict) -> User:
    user = User(
        name=user_data["name"],
        email=user_data["email"],
        phone=user_data.get("phone"),
        password_hash=hash_password(user_data["password"]),
        role=user_data["role"],
        is_active=True,
    )
    db.add(user)
    db.flush()

    loc_data = user_data.get("location")
    if loc_data:
        loc = Location(
            user_id=user.id,
            address=loc_data.get("address"),
            area=loc_data.get("area"),
            city=loc_data.get("city", "Karachi"),
            latitude=loc_data["latitude"],
            longitude=loc_data["longitude"],
        )
        db.add(loc)

    return user


if __name__ == "__main__":
    seed()
