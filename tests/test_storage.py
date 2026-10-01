"""Tests for SQLite/PostgreSQL storage models and database operations."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mathlore_forge.storage.db import (
    AgentRunRecord,
    Base,
    IssueRecord,
    PullRequestRecord,
    ReviewCommentRecord,
    RunStatus,
    RunType,
    TrajectoryRecord,
    reconcile_stray_review_runs,
)


@pytest.fixture
def session():
    """In-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_issue_and_pull_request_creation(session):
    issue = IssueRecord(
        repo="mathlingua/mathlore",
        issue_number=101,
        title="Add vector space definition",
        body="Define a real vector space",
        author="DominicKramer",
    )
    session.add(issue)
    session.commit()

    assert issue.id is not None
    assert issue.status == "QUEUED"

    pr = PullRequestRecord(
        repo="mathlingua/mathlore",
        pr_number=102,
        branch_name="forge/issue-101-add-vector-space",
        title="[Forge] Add vector space definition",
        issue_id=issue.id,
        status="OPEN",
    )
    session.add(pr)
    session.commit()

    assert pr.id is not None
    assert len(issue.pull_requests) == 1
    assert issue.pull_requests[0].pr_number == 102


def test_agent_run_and_trajectory_recording(session):
    run = AgentRunRecord(
        id="run_test_123",
        run_type=RunType.INITIAL_AUTHORING,
        status=RunStatus.RUNNING,
        repo="mathlingua/mathlore",
        issue_number=101,
        prompt="Author vector space definition",
    )
    session.add(run)
    session.commit()

    traj = TrajectoryRecord(
        run_id=run.id,
        trajectory_json='{"thoughts": ["Inspecting 01_algebra.mlg"], "tool_calls": []}',
        markdown_summary="### Trajectory",
    )
    session.add(traj)
    session.commit()

    assert run.trajectory is not None
    assert "Inspecting" in run.trajectory.trajectory_json


def test_review_comment_resolution(session):
    pr = PullRequestRecord(
        repo="mathlingua/mathlore",
        pr_number=105,
        branch_name="forge/issue-105-fix",
        title="[Forge] Fix group axioms",
    )
    session.add(pr)
    session.commit()

    comment = ReviewCommentRecord(
        pr_id=pr.id,
        pr_number=105,
        comment_github_id=98765,
        author="DominicKramer",
        body="Preconditions should be inside when: section",
        file_path="content/07_algebra/01_monoids.mlg",
        line=42,
        addressed=False,
    )
    session.add(comment)
    session.commit()

    assert comment.addressed is False
    comment.addressed = True
    comment.reply_body = "Moved preconditions into when: block"
    session.commit()

    updated = session.query(ReviewCommentRecord).filter_by(comment_github_id=98765).first()
    assert updated.addressed is True
    assert "Moved" in updated.reply_body


def test_reconcile_stray_review_runs(session):
    # 1. Create issue that is resolved
    issue = IssueRecord(
        repo="mathlingua/mathlore",
        issue_number=201,
        title="Issue 201",
        status="RESOLVED",
        plan_status="COMPLETED",
    )
    session.add(issue)
    session.flush()

    # 2. Create PR that is merged
    pr = PullRequestRecord(
        repo="mathlingua/mathlore",
        pr_number=201,
        branch_name="forge/issue-201",
        title="PR 201",
        issue_id=issue.id,
        status="MERGED",
    )
    session.add(pr)
    session.flush()

    # 3. Create run that is still AWAITING_REVIEW
    run = AgentRunRecord(
        id="run_exec_stray_201",
        repo="mathlingua/mathlore",
        run_type=RunType.PLAN_EXECUTION,
        status=RunStatus.AWAITING_REVIEW,
        issue_id=issue.id,
        issue_number=201,
        pr_id=pr.id,
        pr_number=201,
    )
    session.add(run)
    session.commit()

    assert run.status == RunStatus.AWAITING_REVIEW

    # 4. Run reconciler
    fixed = reconcile_stray_review_runs(session)
    assert fixed == 1

    # 5. Verify run is now COMPLETED
    session.refresh(run)
    assert run.status == RunStatus.COMPLETED
    assert run.completed_at is not None

