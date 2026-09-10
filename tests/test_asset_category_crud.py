# ER-ServiceDesk/tests/test_asset_category_crud.py
"""
Covers AssetCategory CRUD. Superuser-only, matching every other
Settings-level lookup table.
"""

from tests.factories import assert_crud_lifecycle


def test_asset_categories_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/inventory/asset_categories",
        {"name": "Laptop", "description": "Portable computers"},
        {"description": "Portable computers and tablets"},
        update_check_field="description",
    )
