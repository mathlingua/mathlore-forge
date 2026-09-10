"""Tests for OpenTelemetry telemetry manager and trace viewer."""

import json
from pathlib import Path
from mathlore_forge.telemetry.tracer import TelemetryManager
from mathlore_forge.telemetry.viewer import TraceViewer


def test_telemetry_span_and_export(tmp_path: Path):
    tm = TelemetryManager(traces_dir=tmp_path)
    with tm.span("test_workflow_step", attributes={"step_number": 1}):
        tm.record_event("test_event", {"info": "step in progress"})

    # Check that a trace file was written
    trace_files = list(tmp_path.glob("trace_*.jsonl"))
    assert len(trace_files) >= 1

    with open(trace_files[0], "r", encoding="utf-8") as f:
        data = json.loads(f.readline())
        assert data["name"] == "test_workflow_step"
        assert data["status"] == "OK"
        assert len(data["events"]) == 1


def test_trace_viewer(tmp_path: Path):
    tm = TelemetryManager(traces_dir=tmp_path)
    with tm.span("root_task", attributes={"agent": "planner"}):
        with tm.span("child_task", attributes={"tool": "search"}):
            pass

    viewer = TraceViewer(traces_dir=tmp_path)
    traces = viewer.list_traces()
    assert len(traces) >= 1
    assert traces[0]["spans_count"] == 2
