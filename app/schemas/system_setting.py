# ER-ServiceDesk/app/schemas/system_setting.py
# Pydantic schemas for SystemSetting entities used to validate and structure a dynamic, admin-editable key/value configuration entry
"""
Pydantic schemas for SystemSetting entities used to validate and structure a dynamic, admin-editable key/value configuration entry.
"""

from pydantic import BaseModel

class SystemSettingBase(BaseModel):
    """Shared fields for SystemSetting across create/read/update."""
    key: str
    value: str | None = None

class SystemSettingCreate(SystemSettingBase):
    """Schema for creating a new SystemSetting record (client -> server)."""
    pass

class SystemSettingUpdate(BaseModel):
    """Schema for partially updating an existing SystemSetting record. All fields optional."""
    key: str | None = None
    value: str | None = None

class SystemSetting(SystemSettingBase):
    """Schema returned to the client for a SystemSetting record (server -> client)."""
    id: int
    class Config:
        orm_mode = True
