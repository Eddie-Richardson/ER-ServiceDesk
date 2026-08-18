# ER-ServiceDesk/app/db/init_db.py
# Database initialization / seeding placeholder
"""
Initialization hook for database seeding, called at startup/deployment.
"""

from sqlalchemy.orm import Session

def init_db(db: Session):
    """
    Placeholder until additional seeding requirements beyond app.db.seed
    are needed (e.g. default admin user, baseline roles/permissions).
    """
    pass
