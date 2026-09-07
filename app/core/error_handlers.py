# ER-ServiceDesk/app/core/error_handlers.py
"""
Registers exception handlers on the FastAPI app so every error response --
whether a raised HTTPException, a Pydantic validation failure, or an
unhandled exception -- follows the same {"error": {"code", "message"}}
JSON shape.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError


def error_response(status_code: int, code: str, message: str):
    """
    Args:
        code: Machine-readable error code (e.g. "ASSET_NOT_FOUND").
        message: Human-readable explanation.
    """
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}}
    )


def _format_validation_errors(errors: list[dict]) -> str:
    """
    Turns pydantic's raw errors() list into one readable string, e.g.
    "body -> email: field required; body -> price: value is not a
    valid decimal". Field-level detail, not a generic message --
    this is what the desktop app actually shows the person, and
    "invalid input" alone gives them nothing to act on.
    """
    parts = []
    for err in errors:
        loc = " -> ".join(str(p) for p in err.get("loc", []))
        msg = err.get("msg", "invalid value")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) if parts else "Invalid input provided."


def register_error_handlers(app: FastAPI):
    """Must be called once from main.py during app startup."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        """
        Maps common status codes to a stable error code, falling back
        to deriving one from the exception detail text. Registered on
        the base StarletteHTTPException, not fastapi.HTTPException --
        the latter is just a subclass, and several genuinely common
        cases (a routing 404 for a nonexistent path, a 405 for the
        wrong HTTP method) are raised internally as the base class,
        which would otherwise bypass this handler entirely and fall
        through to Starlette's own raw {"detail": ...} shape instead
        of this app's {"error": {...}} one.
        """
        code_map = {
            400: "INVALID_INPUT",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
        }
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        code = code_map.get(exc.status_code, detail.upper().replace(" ", "_"))
        return error_response(exc.status_code, code, detail)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(_request: Request, exc: RequestValidationError):
        """
        Handles FastAPI's own request-body/query/path validation
        failures -- a different exception than plain pydantic
        ValidationError below, and the one that actually fires for a
        malformed request body reaching a route. Previously
        unhandled entirely, meaning these fell through to FastAPI's
        own default {"detail": [...]} shape instead of this app's
        {"error": {...}} one. Status stays 422 (FastAPI's own
        convention for this specific failure, distinct from a plain
        400), only the response shape and message detail change.
        """
        return error_response(422, "INVALID_INPUT", _format_validation_errors(exc.errors()))

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(_request: Request, exc: ValidationError):
        """Handles a raw pydantic ValidationError raised directly by application code (not a request body -- see RequestValidationError above for that)."""
        return error_response(400, "INVALID_INPUT", _format_validation_errors(exc.errors()))

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, _exc: Exception):
        """Catch-all handler for any unhandled exception -- prevents stack traces or internals from ever reaching the client."""
        return error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred.")
