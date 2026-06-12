# ER-ServiceDesk/app/schemas/system_settings.py
# Pydantic schemas for SystemSetting entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning system‑wide configuration settings within the
# ER‑ServiceDesk application. System settings store dynamic key/value
# configuration data that administrators can modify without requiring
# a redeploy.

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class SystemSettingBase(BaseModel):
    key: str
    value: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class SystemSettingCreate(SystemSettingBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class SystemSettingUpdate(BaseModel):
    key: str | None = None
    value: str | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class SystemSetting(SystemSettingBase):
    id: int

    class Config:
        orm_mode = True