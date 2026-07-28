from __future__ import annotations

import logging
from typing import Any

import structlog
from asgi_correlation_id import correlation_id
from structlog.types import EventDict, WrappedLogger


def _add_request_id(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Attach the current request's correlation id to every log line."""
    request_id = correlation_id.get()
    if request_id is not None:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging(level: str = "INFO", *, json_logs: bool = True) -> None:
    """Configure structlog for the process. JSON in production, console in dev.

    The console renderer uses a traceback formatter that does NOT dump frame
    locals. Frame locals can contain the user's message, which may hold PII.
    """
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        # Do not cache: reconfiguration at startup (and in tests) must take effect
        # for already-created module-level loggers.
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)
