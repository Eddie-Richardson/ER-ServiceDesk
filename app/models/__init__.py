# ER-ServiceDesk/app/models/__init__.py
"""
Aggregates and re-exports every ORM model.

IMPORTANT: Alembic's env.py relies on `import app.models` to register every
model's table with Base.metadata before autogenerate runs. Any model left
out here is invisible to `alembic revision --autogenerate` and to
relationship() string lookups (e.g. relationship("Quote")) from other
models. If you add a new model file, add its import here too.
"""

from .audit_log import AuditLog
from .background_job import BackgroundJob
from .customer import Customer
from .device import Device
from .discount import Discount
from .invoice import Invoice
from .invoice_line_item import InvoiceLineItem
from .location import Location
from .asset import Asset
from .asset_category import AssetCategory
from .part import Part
from .part_location import PartLocation
from .ticket_part import TicketPart
from .message import Message
from .message_template import MessageTemplate
from .payment import Payment
from .payment_plan import PaymentPlan
from .payment_plan_installment import PaymentPlanInstallment
from .permission import Permission
from .quote import Quote
from .quote_line_item import QuoteLineItem
from .record_lock import RecordLock
from .role import Role
from .role_permission import RolePermission
from .service import Service
from .status_history import StatusHistory
from .system_setting import SystemSetting
from .tax_rate import TaxRate
from .ticket import Ticket
from .ticket_category import TicketCategory
from .ticket_stage import TicketStage
from .ticket_status import TicketStatus
from .ticket_type import TicketType
from .ticket_type_stage import TicketTypeStage
from .user import User
from .user_role import UserRole
