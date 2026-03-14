"""Request ID middleware.

Reads X-Request-ID from incoming headers (echoes it if present, generates a
UUID4 if absent), binds it to structlog contextvars for the duration of the
request, then sets X-Request-ID on the response before clearing contextvars.
"""
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Always clear first to prevent leakage from a previous request on the
        # same thread/task context.
        structlog.contextvars.clear_contextvars()

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Emit an explicit log event with request_id as a kwarg so that
        # structlog.testing.capture_logs() can see it regardless of which
        # processor chain is active (capture_logs replaces the chain).
        logger.info("request_started", request_id=request_id)

        response: Response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        # Clear after so contextvars don't bleed into the next request.
        structlog.contextvars.clear_contextvars()

        return response
