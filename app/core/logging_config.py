# ER-ServiceDesk/app/core/logging_config.py
"""
Configures console + rotating JSON file logging for the whole app.
Call setup_logging() once, early during startup.

The active log file is named with today's date (app-2026-01-15.log,
not a plain app.log that only gets a date suffix once it rotates) --
that way, every day already has its own distinctly-named file the
moment it starts, so log lines from different days are never mixed
into one identically-named file that only reveals which day is which
by unzipping old, suffixed backups. DatedRotatingFileHandler below is
what makes this happen; Python's stock TimedRotatingFileHandler
doesn't support it directly.

Kept 30 days, not 14 -- this is a low-volume file (INFO+ level, mostly
just warnings/errors, not routine request logging), so the disk-space
argument for a shorter window barely applies, while 30 days gives
real, meaningfully more room to look back when someone reports an
issue that's been happening "for a few weeks."
"""

import logging
import logging.config
import logging.handlers
import os
import re
import json
import glob
import datetime

LOG_DIR = os.path.join("logs", "backend")
os.makedirs(LOG_DIR, exist_ok=True)

RETENTION_DAYS = 30
_DATE_SUFFIX_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.log$")


class DatedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    A TimedRotatingFileHandler whose ACTIVE file is already named with
    today's date (e.g. app-2026-01-15.log), not just the rotated-away
    backups. Rotates at midnight; getFilesToDelete() is overridden to
    clean up by the date embedded in each file's own name (not file
    mtime, which a copy/backup/restore could disturb), rather than
    relying on the stock backupCount mechanism, which assumes the
    default "base name + suffix" scheme this class doesn't use.

    Args:
        dir_path: Directory the dated log files live in.
        prefix: Filename prefix before the date, e.g. "app" -> app-2026-01-15.log.
        retention_days: Files whose embedded date is older than this
            many days are deleted on each rollover.
    """

    def __init__(self, dir_path: str, prefix: str, retention_days: int = RETENTION_DAYS, encoding: str = "utf-8"):
        self.dir_path = dir_path
        self.prefix = prefix
        self.retention_days = retention_days
        initial_path = self._path_for_date(datetime.date.today())
        super().__init__(initial_path, when="midnight", interval=1, backupCount=0, encoding=encoding)

    def _path_for_date(self, day: datetime.date) -> str:
        return os.path.join(self.dir_path, f"{self.prefix}-{day.isoformat()}.log")

    def doRollover(self):
        """
        The stock implementation renames the current file with a
        computed suffix and reopens the original base filename -- both
        wrong for this class's own naming scheme, since there is no
        fixed base filename. Overridden to just point at a brand new,
        today-dated file instead of renaming anything, then run the
        real retention sweep.
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        self.baseFilename = self._path_for_date(datetime.date.today())
        self.stream = self._open()

        current_time = int(datetime.datetime.now().timestamp())
        new_rollover_at = self.computeRollover(current_time)
        while new_rollover_at <= current_time:
            new_rollover_at += self.interval
        self.rolloverAt = new_rollover_at

        for old_path in self.getFilesToDelete():
            try:
                os.remove(old_path)
            except OSError:
                pass

    def getFilesToDelete(self):
        """Every file in dir_path matching this handler's own prefix, whose embedded date is older than retention_days -- not the stock implementation, which assumes the default naming scheme."""
        cutoff = datetime.date.today() - datetime.timedelta(days=self.retention_days)
        to_delete = []
        for path in glob.glob(os.path.join(self.dir_path, f"{self.prefix}-*.log")):
            match = _DATE_SUFFIX_RE.search(path)
            if not match:
                continue
            try:
                file_date = datetime.date.fromisoformat(match.group(1))
            except ValueError:
                continue
            if file_date < cutoff:
                to_delete.append(path)
        return to_delete


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
    Apply the app's logging configuration.

    Sets up a human-readable console handler (INFO+) and a JSON file
    handler (see DatedRotatingFileHandler) writing to
    logs/backend/app-{date}.log, rotating at midnight and keeping 30
    days of history.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    file_handler = DatedRotatingFileHandler(LOG_DIR, "app")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JsonFormatter())

    root_logger.handlers = [console_handler, file_handler]
