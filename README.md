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
│   ├── crud/
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
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── attachments.py
│   │   ├── audit_logs.py
│   │   ├── auth.py
│   │   ├── background_jobs.py
│   │   ├── customers.py
│   │   ├── devices.py
│   │   ├── invoices.py
│   │   ├── messages.py
│   │   ├── message_templates.py
│   │   ├── notes.py
│   │   ├── payments.py
│   │   ├── permissions.py
│   │   ├── quotes.py
│   │   ├── roles.py
│   │   ├── role_permissions.py
│   │   ├── status_histories.py
│   │   ├── system_settings.py
│   │   ├── tickets.py
│   │   ├── ticket_categories.py
│   │   ├── ticket_statuses.py
│   │   ├── ticket_types.py
│   │   ├── users.py
│   │   └── user_roles.py
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
│   │   ├── __init__.py
│   │   ├── attachment_service.py
│   │   ├── audit_log_service.py
│   │   ├── auth_service.py
│   │   ├── background_job_service.py
│   │   ├── customer_service.py
│   │   ├── device_service.py
│   │   ├── invoice_service.py
│   │   ├── message_service.py
│   │   ├── message_template_service.py
│   │   ├── note_service.py
│   │   ├── payment_service.py
│   │   ├── permission_service.py
│   │   ├── quote_service.py
│   │   ├── role_service.py
│   │   ├── role_permission_service.py
│   │   ├── status_history_service.py
│   │   ├── system_setting_service.py
│   │   ├── ticket_service.py
│   │   ├── ticket_category_service.py
│   │   ├── ticket_status_service.py
│   │   ├── ticket_type_service.py
│   │   ├── user_service.py
│   │   └── user_role_service.py
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