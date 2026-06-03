# ER-ServiceDesk/app/models/system_setting.py
# ORM model for storing system-wide configuration settings
#
# This model represents key/value configuration entries used by the
# ER‑ServiceDesk application. These settings allow administrators to
# store dynamic configuration values without redeploying the system.

from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

# ---------------------------------------------------------------------------
# SystemSetting Model
# ---------------------------------------------------------------------------
class SystemSetting(Base):
    __tablename__ = "system_settings"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Unique key name for the setting (e.g., "site_name", "support_email")
    key = Column(String, unique=True, nullable=False)

    # Arbitrary text value for the setting
    value = Column(Text, nullable=True)
