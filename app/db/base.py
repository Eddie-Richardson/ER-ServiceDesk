# ER-ServiceDesk/app/db/base.py
# SQLAlchemy Base class for ORM models
#
# This module defines the shared SQLAlchemy Base class used by all ORM models
# in the ER‑ServiceDesk application. Every model inherits from this Base so
# that SQLAlchemy can track metadata, generate tables, and integrate with
# Alembic for migrations.

from sqlalchemy.orm import declarative_base

# ---------------------------------------------------------------------------
# SQLAlchemy Declarative Base
# ---------------------------------------------------------------------------
# The declarative_base() function returns a base class that all ORM models
# must inherit from. It stores metadata about tables, columns, and mappings.
# Alembic uses this metadata during autogenerate operations.
Base = declarative_base()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
# Import ALL models so Alembic can detect them
# DO NOT REMOVE — required for migrations

from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.background_job import BackgroundJob
from app.models.customer import Customer
from app.models.device import Device
from app.models.invoice import Invoice
from app.models.message import Message
from app.models.message_template import MessageTemplate
from app.models.note import Note
from app.models.payment import Payment
from app.models.permission import Permission
from app.models.quote import Quote
from app.models.role import Role
from app.models.status_history import StatusHistory
from app.models.system_setting import SystemSetting
from app.models.ticket import Ticket
from app.models.ticket_category import TicketCategory
from app.models.ticket_status import TicketStatus
from app.models.ticket_type import TicketType
from app.models.user import User
from app.models.user_role import UserRole