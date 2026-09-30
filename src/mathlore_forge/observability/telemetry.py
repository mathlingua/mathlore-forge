"""OpenTelemetry and structured logging configuration for GCP Cloud Trace and Cloud Logging."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


class StructuredLogFormatter(logging.Formatter):
    """Formats log records as structured JSON compatible with Google Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        current_span = trace.get_current_span()
        span_ctx = current_span.get_span_context() if current_span else None

        trace_id = format(span_ctx.trace_id, "032x") if span_ctx and span_ctx.is_valid else None
        span_id = format(span_ctx.span_id, "016x") if span_ctx and span_ctx.is_valid else None

        log_payload: dict[str, Any] = {
            "message": record.getMessage(),
            "severity": record.levelname,
            "timestamp": self.formatTime(record, self.datefmt),
            "logger": record.name,
        }

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        if trace_id and project_id:
            log_payload["logging.googleapis.com/trace"] = f"projects/{project_id}/traces/{trace_id}"
        if span_id:
            log_payload["logging.googleapis.com/spanId"] = span_id

        if hasattr(record, "run_id"):
            log_payload["run_id"] = getattr(record, "run_id")
        if hasattr(record, "repo"):
            log_payload["repo"] = getattr(record, "repo")

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def setup_logging(level: int = logging.INFO) -> None:
    """Configures root and forge loggers with structured JSON output."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def setup_telemetry(service_name: str = "mathlore-forge") -> trace.Tracer:
    """Initializes OpenTelemetry TracerProvider."""
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.1.0",
        }
    )
    provider = TracerProvider(resource=resource)

    # In GCP environment, export to Cloud Trace if available or Console exporter
    if os.getenv("ENABLE_CONSOLE_TRACES") == "true":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return trace.get_tracer("mathlore-forge")


def get_tracer() -> trace.Tracer:
    """Returns the application tracer."""
    return trace.get_tracer("mathlore-forge")
