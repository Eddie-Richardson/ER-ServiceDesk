# ER-ServiceDesk/tests/test_dev_seed_scripts.py
"""
Covers seed_test_inventory.py and seed_test_tickets.py -- both have
top-level module code (db = SessionLocal() at module scope, not
inside a function), so importing either one immediately, actually
executes it against whatever database SessionLocal resolves to. The
only safe way to test them is as a real, separate subprocess, with
DATABASE_URL genuinely overridden to point at the test database for
that subprocess specifically -- never imported directly here.

Focuses on the two genuinely meaningful, non-obvious properties each
script's own docstring explicitly claims: the real data it creates
(including the "split across multiple locations" part, the least
trivial shape either script produces), and real idempotency -- running
either one twice must not create duplicates.
"""

import os
import subprocess
import sys
from pathlib import Path

from app.models.asset import Asset
from app.models.part import Part
from app.models.part_location import PartLocation
from app.models.customer import Customer
from app.models.ticket import Ticket
from app.services.system_setting_service import system_setting_service
from tests.conftest import TEST_DATABASE_URL

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_seed_script(module_name: str):
    """
    Runs the given dev seed script as a genuinely separate subprocess,
    with DATABASE_URL overridden to the real test database -- the only
    safe way to run one of these scripts at all, since each one
    executes immediately on import rather than through a callable
    function.
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL
    result = subprocess.run(
        [sys.executable, "-m", module_name],
        cwd=_PROJECT_ROOT, capture_output=True, text=True, env=env,
    )
    return result


def test_seed_test_inventory_creates_the_real_expected_assets_and_parts(db):
    """Confirms the script's own real data -- including a part genuinely split across three separate locations, the least trivial shape it produces -- actually lands correctly, not just that the script exits cleanly."""
    from app.db.seed import seed_data
    seed_data(db)  # asset categories/locations/ticket data this script requires as real prerequisites

    result = _run_seed_script("app.db.seed_test_inventory")
    assert result.returncode == 0, result.stderr

    assert db.query(Asset).filter_by(name="Front Desk Laptop").first() is not None

    charger = db.query(Part).filter_by(name="Laptop Charger 65W").first()
    assert charger is not None
    charger_locations = db.query(PartLocation).filter_by(part_id=charger.id).all()
    assert len(charger_locations) == 3
    assert sum(loc.quantity for loc in charger_locations) == 4  # exactly at its own reorder_threshold of 4


def test_seed_test_inventory_is_genuinely_idempotent(db):
    """Running it twice must not create a second copy of anything."""
    from app.db.seed import seed_data
    seed_data(db)

    first_run = _run_seed_script("app.db.seed_test_inventory")
    assert first_run.returncode == 0, first_run.stderr
    asset_count_after_first = db.query(Asset).count()
    part_count_after_first = db.query(Part).count()

    second_run = _run_seed_script("app.db.seed_test_inventory")
    assert second_run.returncode == 0, second_run.stderr
    asset_count_after_second = db.query(Asset).count()
    part_count_after_second = db.query(Part).count()

    assert asset_count_after_first == asset_count_after_second
    assert part_count_after_first == part_count_after_second


def test_seed_test_tickets_creates_the_real_expected_customer_and_tickets(db):
    from app.db.seed import seed_data
    seed_data(db)

    result = _run_seed_script("app.db.seed_test_tickets")
    assert result.returncode == 0, result.stderr

    customer = db.query(Customer).filter_by(email="test.customer@example.com").first()
    assert customer is not None

    tickets = db.query(Ticket).filter_by(customer_id=customer.id).all()
    assert len(tickets) == 6
    assert any(t.title == "Cracked screen replacement" and t.priority == "Urgent" for t in tickets)


def test_seed_test_tickets_is_genuinely_idempotent(db):
    from app.db.seed import seed_data
    seed_data(db)

    first_run = _run_seed_script("app.db.seed_test_tickets")
    assert first_run.returncode == 0, first_run.stderr
    ticket_count_after_first = db.query(Ticket).count()

    second_run = _run_seed_script("app.db.seed_test_tickets")
    assert second_run.returncode == 0, second_run.stderr
    ticket_count_after_second = db.query(Ticket).count()

    assert ticket_count_after_first == ticket_count_after_second
