import structlog
import sys
import os
from app.core.config import settings

# Configure structlog
def _get_structlog_processors():
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.LOG_FORMAT.lower() == "console":
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.ConsoleRenderer.EXCEPTION_FORMATTER,
            )
        )
    else:
        processors.append(structlog.processors.JSONRenderer())

    return processors


structlog.configure(
    processors=_get_structlog_processors(),
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

def setup_logging():
    """Setup logging configuration"""
    import logging

    logging.basicConfig(format="%(message)s", stream=sys.stdout)
    logging.getLogger().setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    log_environment = os.getenv("LOG_FORMAT", settings.LOG_FORMAT)

    logger.info(
        "Logging initialized",
        level=settings.LOG_LEVEL,
        format=log_environment,
    )
