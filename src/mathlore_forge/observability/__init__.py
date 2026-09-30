"""Observability module for Google Cloud Logging, Cloud Trace, and OpenTelemetry."""

from mathlore_forge.observability.telemetry import (
    get_tracer,
    setup_logging,
    setup_telemetry,
)

__all__ = ["setup_telemetry", "setup_logging", "get_tracer"]
