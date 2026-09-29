"""Unit tests for SessionManager and sequential session IDs."""

from pathlib import Path
from mathlore_forge.goldens.session import SessionManager


def test_sequential_session_ids(tmp_path: Path):
    mgr = SessionManager(runs_dir=tmp_path)

    s1 = mgr.create_session("test-1", "First Test")
    assert s1.meta.session_id == "session-1"
    assert s1.meta.session_number == 1
    assert Path(s1.meta.session_dir) is not None
    assert (Path(s1.meta.session_dir) / "meta.json").is_file()

    s2 = mgr.create_session("test-2", "Second Test")
    assert s2.meta.session_id == "session-2"
    assert s2.meta.session_number == 2

    s3 = mgr.create_session("test-3", "Third Test")
    assert s3.meta.session_id == "session-3"
    assert s3.meta.session_number == 3

    # Listing
    sessions = mgr.list_sessions()
    assert len(sessions) == 3
    assert [s.session_id for s in sessions] == ["session-1", "session-2", "session-3"]

    # Retrieval
    found = mgr.get_session("2")
    assert found is not None
    assert found.session_id == "session-2"


def test_session_cleanup(tmp_path: Path):
    mgr = SessionManager(runs_dir=tmp_path)
    s1 = mgr.create_session("t1", "T1")
    s2 = mgr.create_session("t2", "T2")

    s1.finish("PASSED", duration_seconds=1.5)
    s2.finish("FAILED", duration_seconds=2.0)

    # Clean only passed
    cleaned = mgr.clean_all(status_filter="PASSED")
    assert cleaned == 1

    remaining = mgr.list_sessions()
    assert len(remaining) == 1
    assert remaining[0].session_id == "session-2"
