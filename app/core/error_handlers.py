# ER-ServiceDesk/app/core/error_handlers.py
# Centralized error handling
"""
Registers exception handlers on the FastAPI app so every error response --
whether a raised HTTPException, a Pydantic validation failure, or an
unhandled exception -- follows the same {"error": {"code", "message"}}
JSON shape. Ported from InventoryHub and applied app-wide.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def error_response(status_code: int, code: str, message: str):
    """
    Build a standardized JSON error response.

    Args:
        status_code: HTTP status code to return.
        code: Machine-readable error code (e.g. "ASSET_NOT_FOUND").
        message: Human-readable explanation.

    Returns:
        A JSONResponse with the standard {"error": {...}} structure.
    """
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}}
    )


def register_error_handlers(app: FastAPI):
    """
    Attach all custom exception handlers to the given FastAPI app.

    Must be called once from main.py during app startup.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException):
        """
        Handle HTTPException raised anywhere in routers or services.

        Maps common status codes to a stable error code, falling back to
        deriving one from the exception detail text.
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

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(_request: Request, _exc: ValidationError):
        """
        Handle Pydantic ValidationError from malformed request data.

        Always returns HTTP 400 with a generic message, to avoid leaking
        internal validation details to the client.
        """
        return error_response(400, "INVALID_INPUT", "Invalid input provided.")

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, _exc: Exception):
        """
        Catch-all handler for any unhandled exception.

        Prevents stack traces or internals from ever reaching the client.
        """
        return error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred.")
