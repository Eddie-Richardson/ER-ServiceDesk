# ER-ServiceDesk/app/models/__init__.py
"""
Aggregates and re-exports every ORM model.

IMPORTANT: Alembic's env.py relies on `import app.models` to register every
model's table with Base.metadata before autogenerate runs. Any model left
out here is invisible to `alembic revision --autogenerate` and to
relationship() string lookups (e.g. relationship("Quote")) from other
models. If you add a new model file, add its import here too.
"""

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
