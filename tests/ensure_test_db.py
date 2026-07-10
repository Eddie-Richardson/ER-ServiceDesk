# ER-ServiceDesk/tests/ensure_test_db.py
# Ensures the test database exists before the test suite runs.
#
# Run this before pytest (see run_tests.ps1). It connects to Postgres's
# default 'postgres' maintenance database using the same credentials as
# TEST_DATABASE_URL, checks whether the target test database exists, and
# creates it if not. This makes "the test db doesn't exist yet" a problem
# that fixes itself instead of a confusing connection-time failure.

import os
import sys
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def ensure_test_db():
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        print("TEST_DATABASE_URL is not set -- skipping test DB check.")
        return

    parsed = urlparse(test_url)
    db_name = parsed.path.lstrip("/")
    host = parsed.hostname
    port = parsed.port or 5432
    user = parsed.username
    password = parsed.password

    if not db_name:
        print("Could not parse a database name from TEST_DATABASE_URL.")
        sys.exit(1)

    # Connect to the default 'postgres' maintenance database -- you can't
    # check for or create a database while connected to it.
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            host=host,
            port=port,
            user=user,
            password=password,
        )
    except psycopg2.OperationalError as e:
        print(f"Could not connect to Postgres to check the test database: {e}")
        sys.exit(1)

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # CREATE DATABASE can't run in a transaction
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone() is not None

            if exists:
                print(f"Test database '{db_name}' already exists.")
            else:
                print(f"Test database '{db_name}' not found -- creating it.")
                # Database names can't be parameterized; db_name comes from
                # our own TEST_DATABASE_URL env var, not external input.
                cur.execute(f'CREATE DATABASE "{db_name}"')
                print(f"Created test database '{db_name}'.")
    finally:
        conn.close()


if __name__ == "__main__":
    ensure_test_db()