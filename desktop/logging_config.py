# ER-ServiceDesk/desktop/logging_config.py
"""
Sets up the desktop app's own logging -- separate from the backend's
(desktop/ never imports from app/, and is packaged into its own,
standalone .exe), but using the same date-stamped file naming and
30-day retention, in the same shared ProgramData location, so every
log source in the whole application -- backend and desktop alike --
lives under one consistent root a person can browse without hunting
across %TEMP%, Program Files, and a project folder for different
pieces.

Covers two of this app's three previously-separate logging
mechanisms directly:
  - General application logging (replaces the old debug_log() raw
    file-append helper) -- routed through Python's real logging
    module now, e.g. logger.info(), logger.warning().
  - Uncaught Python exceptions (sys.excepthook) -- now written via
    the same logger, at ERROR level, instead of its own separate
    raw file.

faulthandler (native/C-level crashes) is NOT covered by this module --
it writes directly to an open file handle from a C-level signal
handler, entirely bypassing Python's own logging machinery by design
(that's exactly why it can capture a crash that kills Python itself).
See get_crash_log_path() below for its own, separate, correctly-named
path -- main.py opens that file itself and hands it to
faulthandler.enable(file=...) directly.
"""

import logging
import logging.handlers
import os
import re
import glob
import datetime

APP_DATA_DIR_NAME = "ER-ServiceDesk"
RETENTION_DAYS = 30
_DATE_SUFFIX_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.log$")


def get_log_dir() -> str:
    """
    Returns the shared desktop log directory --
    C:\\ProgramData\\ER-ServiceDesk\\logs\\desktop\\ -- creating it if
    it doesn't exist yet.

    ProgramData, not Program Files or %TEMP%: unlike Program Files,
    it's genuinely writable by any user account on the machine, not
    just whoever ran the installer -- the real scenario this project
    already documents elsewhere (app_paths.py): installed once by an
    admin, but a different, non-admin employee may log into the same
    PC and use it later in Client mode. The installer grants the
    built-in Users group write access to this one folder specifically
    (see setup.iss) to make that actually work. Unlike %TEMP%, it's
    also one single, stable, shared location, not scattered per-user
    temp folders that differ by whoever's currently logged in.
    """
    program_data = os.environ.get("ProgramData", r"C:\ProgramData")
    log_dir = os.path.join(program_data, APP_DATA_DIR_NAME, "logs", "desktop")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_crash_log_path() -> str:
    """
    Returns today's dated path for the native/C-level crash log
    (faulthandler's own target) -- crash-{date}.log. Callers are
    responsible for opening this themselves; faulthandler needs a
    genuinely open file object, not a path.
    """
    return os.path.join(get_log_dir(), f"crash-{datetime.date.today().isoformat()}.log")


class DatedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Same real behavior as the backend's own DatedRotatingFileHandler
    (app/core/logging_config.py) -- kept as a separate copy rather
    than a shared import, since desktop/ is packaged standalone and
    never imports from app/ at all. See that module's own docstring
    for the full reasoning.
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


def setup_logging():
    """
    Applies the desktop app's own logging configuration. Call once,
    early in main.py's own startup -- same intent as the backend's
    setup_logging(), just a genuinely separate implementation for a
    genuinely separate, standalone package.

    Sets up one file handler (app-{date}.log, in the same shared
    ProgramData/desktop/ folder as everything else here), at INFO
    level. No console handler -- this is a console=False, windowed
    PyInstaller build, so there's no terminal for one to write to.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    file_handler = DatedRotatingFileHandler(get_log_dir(), "app")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))

    root_logger.handlers = [file_handler]


def install_exception_logging():
    """
    Replaces sys.excepthook so an uncaught Python exception is
    genuinely logged (ERROR level, full traceback) through the same
    logger this module sets up, instead of failing silently -- this
    app's console=False build has no terminal an uncaught exception's
    default traceback could ever be seen on anyway.

    Call once, after setup_logging(), early in main.py's own startup.
    """
    import sys

    logger = logging.getLogger("uncaught")

    def _log_unhandled_exception(exc_type, exc_value, exc_traceback):
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = _log_unhandled_exception
