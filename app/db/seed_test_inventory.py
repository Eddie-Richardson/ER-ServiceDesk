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
from app.models.part_location import PartLocation
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
    # (name, sku, reorder_threshold, supplier, [(location_name, quantity), ...])
    ("SSD 500GB", "PART-SSD-500", 5, "Newegg Business",
        [("Parts Shelf", 3)]),                                          # low stock: 3 <= 5
    ("SSD 1TB", "PART-SSD-1TB", 5, "Newegg Business",
        [("Parts Shelf", 12)]),                                         # healthy
    ("RAM 8GB DDR4", "PART-RAM-8GB", 10, "CDW",
        [("Parts Shelf", 2)]),                                          # low stock: 2 <= 10
    ("RAM 16GB DDR4", "PART-RAM-16GB", 10, "CDW",
        [("Parts Shelf", 20)]),                                         # healthy
    ("Laptop Charger 65W", "PART-CHG-65W", 4, "Amazon Business",
        [("Bench 1", 1), ("Bench 2", 1), ("Parts Shelf", 2)]),          # split across 3 locations, total 4 -- exactly at threshold, low stock
    ("HDMI Cable 6ft", "PART-HDMI-6", 5, "Amazon Business",
        [("Bench 2", 30)]),                                             # healthy
]

created_parts = 0
backfilled_locations = 0
for name, sku, threshold, supplier, location_breakdown in sample_parts:
    existing = db.query(Part).filter_by(name=name).first()

    if existing:
        # Handles the case where this script ran once before Part
        # switched from a single location_id/quantity_on_hand to the
        # part_locations breakdown -- an already-existing part with no
        # location rows yet gets backfilled rather than left empty.
        if not existing.part_locations:
            for location_name, quantity in location_breakdown:
                location = locations.get(location_name)
                if location:
                    db.add(PartLocation(part_id=existing.id, location_id=location.id, quantity=quantity))
            backfilled_locations += 1
        continue

    part = Part(name=name, sku=sku, reorder_threshold=threshold, supplier=supplier)
    db.add(part)
    db.flush()  # assigns part.id without needing a full commit yet

    for location_name, quantity in location_breakdown:
        location = locations.get(location_name)
        if not location:
            print(f"Skipping a location entry for '{name}' -- missing location seed data ({location_name})")
            continue
        db.add(PartLocation(part_id=part.id, location_id=location.id, quantity=quantity))

    created_parts += 1

db.commit()
print(f"Created {created_parts} new test part(s), backfilled locations on {backfilled_locations} existing one(s).")
db.close()