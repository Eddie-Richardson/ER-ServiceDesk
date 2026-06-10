# ER-ServiceDesk
ER‑ServiceDesk is a lightweight service desk system for small computer repair shops. It helps track device intake, repair jobs, customer updates, and workflow in a simple, technician‑friendly way.

```
ER-ServiceDesk/
│
├── app/
│   ├── api/
│   │   ├── v1/
│   │   └── __init__.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── __init__.py
│   │
│   ├── db/
│   │   ├── session.py
│   │   ├── base.py
│   │   ├── init_db.py
│   │   ├── seed.py
│   │   └── __init__.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── attachment.py
│   │   ├── audit_log.py
│   │   ├── background_job.py
│   │   ├── customer.py
│   │   ├── device.py
│   │   ├── invoice.py
│   │   ├── message.py
│   │   ├── message_template.py
│   │   ├── note.py
│   │   ├── payment.py
│   │   ├── permission.py
│   │   ├── quote.py
│   │   ├── role.py
│   │   ├── role_permission.py
│   │   ├── status_history.py
│   │   ├── system_setting.py
│   │   ├── ticket.py
│   │   ├── ticket_category.py
│   │   ├── ticket_status.py
│   │   ├── ticket_type.py
│   │   ├── user.py
│   │   └── user_role.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── attachment.py
│   │   ├── audit_log.py
│   │   ├── background_job.py
│   │   ├── customer.py
│   │   ├── device.py
│   │   ├── invoice.py
│   │   ├── message.py
│   │   ├── message_template.py
│   │   ├── note.py
│   │   ├── payment.py
│   │   ├── permission.py
│   │   ├── quote.py
│   │   ├── role.py
│   │   ├── role_permission.py
│   │   ├── status_history.py
│   │   ├── system_setting.py
│   │   ├── ticket.py
│   │   ├── ticket_category.py
│   │   ├── ticket_status.py
│   │   ├── ticket_type.py
│   │   ├── user.py
│   │   └── user_role.py
│   │
│   ├── services/
│   │   └── __init__.py
│   │
│   ├── workers/
│   │   ├── tasks.py
│   │   ├── worker.py
│   │   └── __init__.py
│   │
│   ├── main.py
│   └── __init__.py
│
├── alembic/
│   ├── versions/
│   └── env.py
│
├── alembic.ini
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```