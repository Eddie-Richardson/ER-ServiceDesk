# ER-ServiceDesk/app/models/system_setting.py
# ORM model for a dynamic, admin-editable key/value configuration entry
"""
ORM model for a dynamic, admin-editable key/value configuration entry.
"""

from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

class SystemSetting(Base):
    """
    Represents a single system-wide configuration value that can change without a redeploy.

    Attributes:
        key: Unique setting name (e.g. 'site_name').
    """
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=True)
