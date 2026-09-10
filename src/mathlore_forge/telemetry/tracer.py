"""OpenTelemetry tracer and execution event tracker."""

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode


class JsonSpanExporter(SpanExporter):
    """Exports finished OpenTelemetry spans into memory and JSON files for inspection."""

    def __init__(self, traces_dir: Path | str | None = None):
        self.traces_dir = Path(traces_dir) if traces_dir else Path("./traces")
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.completed_spans: list[dict[str, Any]] = []

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            events_data = []
            for ev in span.events:
                events_data.append({
                    "name": ev.name,
                    "timestamp": ev.timestamp / 1e9,
                    "attributes": dict(ev.attributes or {}),
                })

            span_dict = {
                "name": span.name,
                "context": {
                    "trace_id": format(span.context.trace_id, "032x"),
                    "span_id": format(span.context.span_id, "016x"),
                },
                "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
                "start_time": span.start_time / 1e9 if span.start_time else None,
                "end_time": span.end_time / 1e9 if span.end_time else None,
                "duration_seconds": (
                    (span.end_time - span.start_time) / 1e9
                    if (span.end_time and span.start_time)
                    else 0.0
                ),
                "status": span.status.status_code.name,
                "status_description": span.status.description,
                "attributes": dict(span.attributes or {}),
                "events": events_data,
            }
            self.completed_spans.append(span_dict)

            # Persist trace log
            trace_id_hex = span_dict["context"]["trace_id"]
            trace_file = self.traces_dir / f"trace_{trace_id_hex}.jsonl"
            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(span_dict) + "\n")

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class TelemetryManager:
    """Central manager for OpenTelemetry tracing and live agent monitoring."""

    _instance: "TelemetryManager | None" = None

    def __init__(self, traces_dir: Path | str = "./traces", service_name: str = "mathlore-forge"):
        self.traces_dir = Path(traces_dir)
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.resource = Resource.create({"service.name": service_name})
        self.provider = TracerProvider(resource=self.resource)
        self.exporter = JsonSpanExporter(traces_dir=self.traces_dir)
        self.processor = SimpleSpanProcessor(self.exporter)
        self.provider.add_span_processor(self.processor)
        try:
            trace.set_tracer_provider(self.provider)
        except Exception:
            pass
        self.tracer = self.provider.get_tracer("mathlore.agent")
        TelemetryManager._instance = self

        # Active state tracking for live viewing
        self.active_tasks: dict[str, dict[str, Any]] = {}
        self.current_activity: str = "Idle"
        self.current_phase: str = "Ready"

    def set_traces_dir(self, traces_dir: Path | str) -> None:
        self.traces_dir = Path(traces_dir)
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.exporter.traces_dir = self.traces_dir

    @classmethod
    def get_instance(cls, traces_dir: Path | str = "./traces") -> "TelemetryManager":
        if cls._instance is None:
            cls._instance = cls(traces_dir=traces_dir)
        elif traces_dir:
            cls._instance.set_traces_dir(traces_dir)
        return cls._instance

    def set_activity(self, phase: str, activity: str) -> None:
        self.current_phase = phase
        self.current_activity = activity

    def get_live_status(self) -> dict[str, Any]:
        return {
            "phase": self.current_phase,
            "activity": self.current_activity,
            "active_tasks": list(self.active_tasks.values()),
        }

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Generator[trace.Span, None, None]:
        clean_attrs = attributes or {}
        task_id = f"{name}-{time.time()}"
        self.active_tasks[task_id] = {
            "name": name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "attributes": clean_attrs,
        }
        with self.tracer.start_as_current_span(name, attributes=clean_attrs) as span:
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            finally:
                self.active_tasks.pop(task_id, None)

    def record_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.add_event(name, attributes=attributes or {})


def get_telemetry_manager(traces_dir: Path | str = "./traces") -> TelemetryManager:
    return TelemetryManager.get_instance(traces_dir=traces_dir)


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[trace.Span, None, None]:
    manager = get_telemetry_manager()
    with manager.span(name, attributes=attributes) as span:
        yield span
