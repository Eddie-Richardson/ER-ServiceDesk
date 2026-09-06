# ER-ServiceDesk/app/core/error_handlers.py
"""
Registers exception handlers on the FastAPI app so every error response --
whether a raised HTTPException, a Pydantic validation failure, or an
unhandled exception -- follows the same {"error": {"code", "message"}}
JSON shape.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
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


def register_error_handlers(app: FastAPI):
    """Must be called once from main.py during app startup."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException):
        """Maps common status codes to a stable error code, falling back to deriving one from the exception detail text."""
        code_map = {
            400: "INVALID_INPUT",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
        }
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        code = code_map.get(exc.status_code, detail.upper().replace(" ", "_"))
        return error_response(exc.status_code, code, detail)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(_request: Request, _exc: ValidationError):
        """Always returns HTTP 400 with a generic message, to avoid leaking internal validation details to the client."""
        return error_response(400, "INVALID_INPUT", "Invalid input provided.")

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, _exc: Exception):
        """Catch-all handler for any unhandled exception -- prevents stack traces or internals from ever reaching the client."""
        return error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred.")
