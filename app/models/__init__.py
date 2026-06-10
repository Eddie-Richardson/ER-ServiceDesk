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
from .permission import Permission
from .quote import Quote
from .role import Role
from .role_permission import RolePermission
from .status_history import StatusHistory
from .system_setting import SystemSetting
from .ticket import Ticket
from .ticket_category import TicketCategory
from .ticket_status import TicketStatus
from .ticket_type import TicketType
from .user import User
from .user_role import UserRole
