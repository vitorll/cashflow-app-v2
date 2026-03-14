"""Structlog global configuration.

Call configure_structlog() once at module import time so that
structlog.testing.capture_logs() sees merge_contextvars in the processor chain.
"""
import structlog


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


# Called at import time so that any module importing from app.main (including
# the test suite) gets the configured processor chain before any log calls fire.
configure_structlog()
