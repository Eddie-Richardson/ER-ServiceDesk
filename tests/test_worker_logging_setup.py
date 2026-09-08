# ER-ServiceDesk/tests/test_worker_logging_setup.py
"""
Regression test: app/workers/worker.py and app/workers/scheduler.py
previously never called setup_logging() at all, meaning every
logger.warning()/error()/exception() call made from inside either
process (poll_inbound_email's "unmatched, needs manual triage"
warning, notify_customer_of_part_status_change's failure logging,
etc.) was never actually written to logs/app.log.

Genuinely running either entrypoint would start a real, blocking
worker/scheduler loop (they're `if __name__ == "__main__":` scripts,
not importable functions), so this can't be tested by actually
executing them the normal way. Instead, parses each file's real
source with Python's own ast module and confirms setup_logging() is
genuinely called somewhere in the file -- not a fragile string search
that could false-positive on a comment merely mentioning the name.
"""

import ast
from pathlib import Path

_WORKERS_DIR = Path(__file__).resolve().parent.parent / "app" / "workers"


def _calls_setup_logging(file_path: Path) -> bool:
    """
    Returns:
        True if the given file's source genuinely contains a call to
        setup_logging() anywhere in its AST, however it's referenced
        (setup_logging() or module.setup_logging()).
    """
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "setup_logging":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "setup_logging":
                return True
    return False


def test_worker_entrypoint_calls_setup_logging():
    assert _calls_setup_logging(_WORKERS_DIR / "worker.py")


def test_scheduler_entrypoint_calls_setup_logging():
    assert _calls_setup_logging(_WORKERS_DIR / "scheduler.py")
