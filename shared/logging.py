"""Structured logging configuration with trace_id support."""

import logging
import sys

import structlog

from shared.config import get_settings


def configure_logging() -> None:
    """Configure structlog and stdlib logging."""
    settings = get_settings()
    is_dev = settings.app_env == "development"
    is_json = settings.log_format == "json" and not is_dev

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    # Shared processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]

    # Common processors after filtering
    render_processors = [
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if is_json:
        render_processors.append(structlog.processors.JSONRenderer())
    else:
        render_processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=shared_processors + render_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


def bind_trace_id(trace_id: str) -> None:
    """Bind trace_id to the current context."""
    structlog.contextvars.bind_contextvars(trace_id=trace_id)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
