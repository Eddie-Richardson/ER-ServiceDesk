# ER-ServiceDesk/app/db/seed_test_inventory.py

"""
One-off script that seeds a handful of assets and parts spanning
different categories, locations, statuses, and stock levels.

Not part of the normal seed_data() flow -- this exists purely to give
the desktop Inventory window's tabs (and the Low Stock filter
specifically) something with real variety to click through during
development. Safe to re-run; it checks for existing records by name
before creating anything.
"""

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.asset_category import AssetCategory
from app.models.part import Part
from app.models.location import Location

db = SessionLocal()

categories = {c.name: c for c in db.query(AssetCategory).all()}
locations = {l.name: l for l in db.query(Location).all()}

if not categories or not locations:
    print("No asset categories or locations found -- run your normal seed_data() first.")
    db.close()
    exit(1)

sample_assets = [
    # (name, category, manufacturer, model, sku, serial, status, location, condition)
    ("Front Desk Laptop", "Laptop", "Dell", "Latitude 5420", "AST-LAP-DELL-5420", "FD-LAP-001", "Active", "Front Desk", "Good"),
    ("Bench 1 Diagnostic Laptop", "Laptop", "Lenovo", "ThinkPad T14", "AST-LAP-LEN-T14", "BENCH1-LAP-001", "In Repair", "Bench 1", "Fair"),
    ("Shop Desktop", "Desktop", "HP", "EliteDesk 800", "AST-DSK-HP-800", "DESK-001", "Active", "Bench 2", "Good"),
    ("Waiting Room Monitor", "Monitor", "Dell", "P2419H", "AST-MON-DELL-P2419H", "MON-001", "Active", "Front Desk", "New"),
    ("Retired Test Laptop", "Laptop", "Acer", "Aspire 5", "AST-LAP-ACER-A5", "OLD-LAP-001", "Retired", "Parts Shelf", "Damaged"),
    ("Shop WiFi Router", "Networking Equipment", "Ubiquiti", "UniFi AP", "AST-NET-UBNT-AP", "NET-001", "Active", "Front Desk", "Good"),
]

created_assets = 0
updated_assets = 0
for name, category_name, manufacturer, model, sku, serial, status, location_name, condition in sample_assets:
    existing = db.query(Asset).filter_by(name=name).first()
    if existing:
        # Handles the case where this script ran once before a field
        # (like sku) was added to it -- backfill rather than leave
        # already-seeded rows silently stuck without it.
        if not existing.sku:
            existing.sku = sku
            updated_assets += 1
        continue

    category = categories.get(category_name)
    location = locations.get(location_name)
    if not category or not location:
        print(f"Skipping asset '{name}' -- missing category/location seed data ({category_name}/{location_name})")
        continue

    asset = Asset(
        name=name,
        sku=sku,
        category_id=category.id,
        manufacturer=manufacturer,
        model=model,
        serial_number=serial,
        status=status,
        location_id=location.id,
        condition=condition,
    )
    db.add(asset)
    created_assets += 1

db.commit()
print(f"Created {created_assets} new test asset(s), backfilled sku on {updated_assets} existing one(s).")

sample_parts = [
    # (name, sku, quantity_on_hand, reorder_threshold, supplier, location_name)
    ("SSD 500GB", "PART-SSD-500", 3, 5, "Newegg Business", "Parts Shelf"),      # low stock
    ("SSD 1TB", "PART-SSD-1TB", 12, 5, "Newegg Business", "Parts Shelf"),       # healthy
    ("RAM 8GB DDR4", "PART-RAM-8GB", 2, 10, "CDW", "Parts Shelf"),              # low stock
    ("RAM 16GB DDR4", "PART-RAM-16GB", 20, 10, "CDW", "Parts Shelf"),           # healthy
    ("Laptop Charger 65W", "PART-CHG-65W", 4, 4, "Amazon Business", "Bench 1"), # exactly at threshold, low stock
    ("HDMI Cable 6ft", "PART-HDMI-6", 30, 5, "Amazon Business", "Bench 2"),     # healthy
]

created_parts = 0
for name, sku, quantity, threshold, supplier, location_name in sample_parts:
    if db.query(Part).filter_by(name=name).first():
        continue

    location = locations.get(location_name)
    if not location:
        print(f"Skipping part '{name}' -- missing location seed data ({location_name})")
        continue

    part = Part(
        name=name,
        sku=sku,
        quantity_on_hand=quantity,
        reorder_threshold=threshold,
        supplier=supplier,
        location_id=location.id,
    )
    db.add(part)
    created_parts += 1

db.commit()
print(f"Created {created_parts} new test part(s).")
db.close()