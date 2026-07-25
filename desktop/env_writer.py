# ER-ServiceDesk/desktop/env_writer.py

"""
Generates and writes the .env file the backend needs to run, as part of
the Setup Wizard's first-run flow.

Postgres credentials are pure internal plumbing -- nobody running the
Setup Wizard needs to think about a database username or password, so
those are auto-generated/fixed rather than asked for, same reasoning
already applied to the database's own name (erservicedesk) elsewhere
in this project. SECRET_KEY is auto-generated for the same reason: it
should never be a value a person chooses by hand.

Gmail credentials and the shop's business name genuinely are
per-install choices, so those come from what the wizard collected.
"""

import secrets
from pathlib import Path

POSTGRES_USER = "erservicedesk_user"
POSTGRES_DB = "erservicedesk"


def generate_secret_key() -> str:
    """
    Returns a cryptographically random string suitable for SECRET_KEY --
    long enough that brute-forcing it is infeasible, and never a value
    a person is asked to choose or type themselves.
    """
    return secrets.token_urlsafe(64)


def generate_postgres_password() -> str:
    """Returns a cryptographically random password for the Postgres user this install creates."""
    return secrets.token_urlsafe(32)


def build_env_contents(
    gmail_address: str,
    gmail_app_password: str,
    business_name: str,
    postgres_password: str,
    secret_key: str,
) -> str:
    """
    Builds the full contents of a .env file from the values collected
    during setup.

    Args:
        gmail_address: The Gmail account outbound/inbound mail uses.
        gmail_app_password: That account's app password (not its normal
            login password -- see app/core/email.py for why).
        business_name: The shop's display name, picked up by
            app/db/run_seed.py and written into system_settings.
        postgres_password: A freshly generated password for this
            install's Postgres user -- see generate_postgres_password().
        secret_key: A freshly generated value for SECRET_KEY -- see
            generate_secret_key().

    Returns:
        The complete text to write to .env.
    """
    database_url = f"postgresql+psycopg2://{POSTGRES_USER}:{postgres_password}@db:5432/{POSTGRES_DB}"

    return (
        f"POSTGRES_USER={POSTGRES_USER}\n"
        f"POSTGRES_PASSWORD={postgres_password}\n"
        f"POSTGRES_DB={POSTGRES_DB}\n"
        f"DATABASE_URL={database_url}\n"
        f"SECRET_KEY={secret_key}\n"
        f"GMAIL_ADDRESS={gmail_address}\n"
        f"GMAIL_APP_PASSWORD={gmail_app_password}\n"
        f"BUSINESS_NAME={business_name}\n"
    )


def write_env_file(
    compose_dir: str,
    gmail_address: str,
    gmail_app_password: str,
    business_name: str,
) -> str:
    """
    Generates a fresh SECRET_KEY and Postgres password, builds the full
    .env contents, and writes it to the project's compose directory.

    Args:
        compose_dir: Directory containing docker-compose.yml -- .env is
            written alongside it, since that's where Docker Compose
            looks for it (env_file: .env in docker-compose.yml).
        gmail_address: The Gmail account outbound/inbound mail uses.
        gmail_app_password: That account's app password.
        business_name: The shop's display name.

    Returns:
        The full contents that were written, mainly useful for tests --
        callers don't normally need this.
    """
    contents = build_env_contents(
        gmail_address=gmail_address,
        gmail_app_password=gmail_app_password,
        business_name=business_name,
        postgres_password=generate_postgres_password(),
        secret_key=generate_secret_key(),
    )

    env_path = Path(compose_dir) / ".env"
    env_path.write_text(contents, encoding="utf-8")
    return contents
