# ER-ServiceDesk/app/core/logging_config.py
"""
Configures console + rotating JSON file logging for the whole app.
Call setup_logging() once, early during startup.
"""

import logging
import logging.config
import os
import json
import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON, including stack traces."""

    def format(self, record):
        """
        Returns:
            A JSON-encoded string with timestamp, level, message, logger
            name, and (if present) the exception stack trace.
        """
        log_record = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            log_record["stack_trace"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logging():
    """
    Apply the app's logging configuration via dictConfig.

    Sets up a human-readable console handler (INFO+) and a JSON file
    handler that rotates nightly and keeps 14 days of history.
    """
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {"format": "%(asctime)s - %(levelname)s - %(message)s"},
            "json": {"()": JsonFormatter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": "INFO",
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "json",
                "filename": f"{LOG_DIR}/app.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 14,
                "encoding": "utf-8",
                "level": "INFO",
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    }
    logging.config.dictConfig(logging_config)
