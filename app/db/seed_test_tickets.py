# ER-ServiceDesk/app/db/seed_test_tickets.py

"""
One-off script that seeds a test customer, device, and a handful of
tickets spanning different categories, statuses, and priorities.

Not part of the normal seed_data() flow -- this exists purely to give
the desktop Tickets window's filters something with real variety to
click through during development. Safe to re-run; it checks for
existing records by name/email before creating anything.
"""

from app.db.session import SessionLocal
from app.models.customer import Customer
from app.models.device import Device
from app.models.ticket import Ticket
from app.models.ticket_category import TicketCategory
from app.models.ticket_type import TicketType
from app.models.ticket_status import TicketStatus

db = SessionLocal()

customer = db.query(Customer).filter_by(email="test.customer@example.com").first()
if not customer:
    customer = Customer(
        first_name="Test",
        last_name="Customer",
        email="test.customer@example.com",
        phone="555-0100",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    print(f"Created customer: {customer.first_name} {customer.last_name} (id={customer.id})")
else:
    print(f"Using existing customer id={customer.id}")

device = db.query(Device).filter_by(customer_id=customer.id).first()
if not device:
    device = Device(
        customer_id=customer.id,
        device_type="Laptop",
        brand="Dell",
        model="XPS 13",
        serial_number="TEST-SN-001",
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    print(f"Created device: {device.device_type} (id={device.id})")
else:
    print(f"Using existing device id={device.id}")

categories = {c.name: c for c in db.query(TicketCategory).all()}
statuses = {s.name: s for s in db.query(TicketStatus).all()}
ticket_type = db.query(TicketType).first()

if not ticket_type:
    print("No ticket types found -- run your normal seed_data() first.")
    db.close()
    exit(1)

sample_tickets = [
    ("Laptop won't power on", "Hardware", "Open", "High"),
    ("Blue screen on startup", "Software", "Open", "Low"),
    ("Wifi keeps disconnecting", "Network", "In Progress", "High"),
    ("Cracked screen replacement", "Hardware", "Waiting on Parts", "Urgent"),
    ("New build for video editing", "Custom Build", "Resolved", "Medium"),
    ("Slow performance", "Software", "Closed", "Low"),
]

created = 0
for title, category_name, status_name, priority in sample_tickets:
    category = categories.get(category_name)
    status = statuses.get(status_name)
    if not category or not status:
        print(f"Skipping '{title}' -- missing category/status seed data ({category_name}/{status_name})")
        continue

    exists = db.query(Ticket).filter_by(title=title, customer_id=customer.id).first()
    if exists:
        continue

    ticket = Ticket(
        customer_id=customer.id,
        device_id=device.id,
        category_id=category.id,
        type_id=ticket_type.id,
        status_id=status.id,
        title=title,
        priority=priority,
    )
    db.add(ticket)
    created += 1

db.commit()
print(f"Created {created} new test ticket(s).")
db.close()