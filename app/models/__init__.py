# app/models/__init__.py
# Aggregates and exposes all model classes defined in this package.

# ---------------------------------------------------------------------------
# Model Exports
# ---------------------------------------------------------------------------

from .attachment import Attachment
from .audit_log import AuditLog
from .background_job import BackgroundJob
from .customer import Customer
from .device import Device
from .invoice import Invoice
from .message import Message
from .message_template import MessageTemplate
from .note import Note
from .payment import Payment
from .role import Role
from .ticket import Ticket
from .user import User
