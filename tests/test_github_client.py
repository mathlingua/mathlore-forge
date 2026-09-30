"""Tests for GitHub client and webhook signature verification."""

import hashlib
import hmac
import pytest

from mathlore_forge.workflows.github_client import (
    GitHubClient,
    GitHubIssue,
    GitHubPullRequest,
    GitHubReviewComment,
)


def test_webhook_signature_verification():
    secret = "my-test-webhook-secret-42"
    payload = b'{"action": "opened", "issue": {"number": 1}}'

    # Compute valid signature
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    sig_header = f"sha256={mac.hexdigest()}"

    assert GitHubClient.verify_webhook_signature(payload, sig_header, secret) is True
    assert GitHubClient.verify_webhook_signature(payload, "sha256=invalid", secret) is False
    assert GitHubClient.verify_webhook_signature(payload, sig_header, "wrong-secret") is False
    assert GitHubClient.verify_webhook_signature(payload, None, secret) is False


def test_models_parsing():
    issue = GitHubIssue(
        number=42,
        title="Add Euclidean domain",
        body="Formulate Euclidean domain in 03_rings.mlg",
        author="DominicKramer",
        labels=["forge", "algebra"],
    )
    assert issue.number == 42
    assert "forge" in issue.labels

    pr = GitHubPullRequest(
        number=43,
        title="[Forge] Add Euclidean domain",
        body="Resolves #42",
        head_branch="forge/issue-42-euclidean",
        base_branch="main",
        state="open",
        html_url="https://github.com/mathlingua/mathlore/pull/43",
    )
    assert pr.head_branch == "forge/issue-42-euclidean"
    assert pr.merged is False

    comment = GitHubReviewComment(
        id=123456,
        author="DominicKramer",
        body="Missing Documented: section",
        path="content/07_algebra/03_rings.mlg",
        line=18,
        created_at="2026-09-29T20:00:00Z",
    )
    assert comment.id == 123456
    assert comment.line == 18
