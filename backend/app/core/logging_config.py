"""
Security-focused logging configuration with JSON formatting and correlation IDs.
"""

import logging
import sys
import uuid
import json
from typing import Optional
from datetime import datetime
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context variable for correlation ID (thread-safe)
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record):
        record.correlation_id = correlation_id_var.get() or "none"
        return True


class SecurityJsonFormatter(logging.Formatter):
    """Custom JSON formatter with security-focused fields."""

    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "none"),
            "source": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Security event classification
        if hasattr(record, "event_type"):
            log_data["event_type"] = record.event_type
        if hasattr(record, "event_category"):
            log_data["event_category"] = record.event_category

        # User and request context
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "username"):
            log_data["username"] = record.username
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address
        if hasattr(record, "user_agent"):
            log_data["user_agent"] = record.user_agent
        if hasattr(record, "request_method"):
            log_data["request"] = {
                "method": record.request_method,
                "path": getattr(record, "request_path", "unknown"),
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_security_logging():
    """Configure structured JSON logging for security events."""

    # Create JSON formatter
    formatter = SecurityJsonFormatter()

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIdFilter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Configure uvicorn loggers to use JSON formatter
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(console_handler)
    uvicorn_logger.propagate = False

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.addHandler(console_handler)
    uvicorn_access.propagate = False

    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers.clear()
    uvicorn_error.addHandler(console_handler)
    uvicorn_error.propagate = False

    # Create security audit logger
    security_logger = logging.getLogger("security.audit")
    security_logger.setLevel(logging.INFO)

    return security_logger


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to requests."""

    async def dispatch(self, request: Request, call_next):
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Set in context variable
        correlation_id_var.set(correlation_id)

        # Add to request state for easy access
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


def log_security_event(
    event_type: str,
    message: str,
    level: int = logging.INFO,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    event_category: str = "security",
    **extra_fields
):
    """
    Log a security event with structured data.

    Args:
        event_type: Type of security event (e.g., "auth.login.success")
        message: Human-readable message
        level: Logging level (default: INFO)
        user_id: User ID if applicable
        username: Username if applicable
        ip_address: Client IP address
        user_agent: Client user agent
        request_method: HTTP method
        request_path: Request path
        event_category: Event category (default: "security")
        **extra_fields: Additional fields to include
    """
    logger = logging.getLogger("security.audit")

    extra = {
        "event_type": event_type,
        "event_category": event_category,
    }

    if user_id:
        extra["user_id"] = user_id
    if username:
        extra["username"] = username
    if ip_address:
        extra["ip_address"] = ip_address
    if user_agent:
        extra["user_agent"] = user_agent
    if request_method:
        extra["request_method"] = request_method
    if request_path:
        extra["request_path"] = request_path

    # Add any extra fields
    extra.update(extra_fields)

    logger.log(level, message, extra=extra)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request, considering proxies."""
    # Check X-Forwarded-For header (from proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"
