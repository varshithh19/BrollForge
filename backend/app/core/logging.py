import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variables for correlation ID and job ID in async execution
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id", default=None)


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records as structured JSON according to Integration Standard Point 8.
    Fields: timestamp, level, message, logger, job_id, correlation_id, extra.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include contextual IDs
        corr_id = correlation_id_ctx.get()
        if corr_id or hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = corr_id or getattr(record, "correlation_id")

        j_id = job_id_ctx.get()
        if j_id or hasattr(record, "job_id"):
            log_entry["job_id"] = j_id or getattr(record, "job_id")

        # Include structured extra fields if passed
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            # Sanitize to never leak secrets
            sanitized = {}
            for k, v in record.extra_data.items():
                if any(sec in k.lower() for sec in ["secret", "password", "token", "key", "authorization"]):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = v
            log_entry["details"] = sanitized

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logger(name: str = "brollforge", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logger()
