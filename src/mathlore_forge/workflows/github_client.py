"""GitHub API client supporting GitHub App and PAT authentication."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Sequence
import httpx
from pydantic import BaseModel, Field


class GitHubReviewComment(BaseModel):
    """Represents a code review comment on a Pull Request."""

    id: int
    pull_request_review_id: int | None = None
    author: str
    body: str
    path: str | None = None
    line: int | None = None
    diff_hunk: str | None = None
    created_at: str
    html_url: str | None = None


class GitHubIssue(BaseModel):
    """Represents a GitHub issue."""

    number: int
    title: str
    body: str
    author: str
    labels: list[str] = Field(default_factory=list)
    state: str = "open"
    html_url: str = ""


class GitHubPullRequest(BaseModel):
    """Represents a GitHub Pull Request."""

    number: int
    title: str
    body: str
    head_branch: str
    base_branch: str
    state: str
    html_url: str
    merged: bool = False


class GitHubClient:
    """Client for interacting with the GitHub REST API."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
    ):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def verify_webhook_signature(payload_bytes: bytes, signature_header: str | None, secret: str) -> bool:
        """Verifies the GitHub webhook HMAC SHA256 signature."""
        if not signature_header or not secret:
            return False
        if not signature_header.startswith("sha256="):
            return False

        expected_sig = signature_header[7:]
        mac = hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
        computed_sig = mac.hexdigest()
        return hmac.compare_digest(computed_sig, expected_sig)

    async def get_issue(self, repo: str, issue_number: int) -> GitHubIssue:
        """Fetches issue details from GitHub."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{repo}/issues/{issue_number}",
                headers=self._headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return GitHubIssue(
                number=data["number"],
                title=data.get("title", ""),
                body=data.get("body", "") or "",
                author=data.get("user", {}).get("login", ""),
                labels=[l["name"] for l in data.get("labels", []) if isinstance(l, dict) and "name" in l],
                state=data.get("state", "open"),
                html_url=data.get("html_url", ""),
            )

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> GitHubPullRequest:
        """Creates a Pull Request in the target repository."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/repos/{repo}/pulls",
                headers=self._headers(),
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return GitHubPullRequest(
                number=data["number"],
                title=data["title"],
                body=data.get("body", "") or "",
                head_branch=data["head"]["ref"],
                base_branch=data["base"]["ref"],
                state=data["state"],
                html_url=data["html_url"],
            )

    async def get_pull_request(self, repo: str, pr_number: int) -> GitHubPullRequest:
        """Fetches Pull Request details."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{repo}/pulls/{pr_number}",
                headers=self._headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return GitHubPullRequest(
                number=data["number"],
                title=data["title"],
                body=data.get("body", "") or "",
                head_branch=data["head"]["ref"],
                base_branch=data["base"]["ref"],
                state=data["state"],
                html_url=data["html_url"],
                merged=data.get("merged", False),
            )

    async def list_review_comments(self, repo: str, pr_number: int) -> list[GitHubReviewComment]:
        """Lists inline code review comments for a Pull Request."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{repo}/pulls/{pr_number}/comments",
                headers=self._headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            raw_comments = resp.json()

            results: list[GitHubReviewComment] = []
            for c in raw_comments:
                results.append(
                    GitHubReviewComment(
                        id=c["id"],
                        pull_request_review_id=c.get("pull_request_review_id"),
                        author=c.get("user", {}).get("login", ""),
                        body=c.get("body", ""),
                        path=c.get("path"),
                        line=c.get("line") or c.get("original_line"),
                        diff_hunk=c.get("diff_hunk"),
                        created_at=c.get("created_at", ""),
                        html_url=c.get("html_url"),
                    )
                )
            return results

    async def reply_to_review_comment(self, repo: str, pr_number: int, comment_id: int, body: str) -> None:
        """Replies to a specific review comment thread on a Pull Request."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/repos/{repo}/pulls/{pr_number}/comments/{comment_id}/replies",
                headers=self._headers(),
                json={"body": body},
                timeout=15.0,
            )
            resp.raise_for_status()

    async def create_issue_comment(self, repo: str, issue_or_pr_number: int, body: str) -> str:
        """Adds a top-level conversation comment to an issue or PR."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/repos/{repo}/issues/{issue_or_pr_number}/comments",
                headers=self._headers(),
                json={"body": body},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("html_url", "")

    async def request_reviewers(self, repo: str, pr_number: int, reviewers: Sequence[str]) -> None:
        """Requests reviews from specified GitHub usernames."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/repos/{repo}/pulls/{pr_number}/requested_reviewers",
                headers=self._headers(),
                json={"reviewers": list(reviewers)},
                timeout=15.0,
            )
            resp.raise_for_status()

    async def merge_pull_request(
        self,
        repo: str,
        pr_number: int,
        commit_title: str | None = None,
        merge_method: str = "squash",
    ) -> bool:
        """Merges a Pull Request."""
        payload: dict[str, Any] = {"merge_method": merge_method}
        if commit_title:
            payload["commit_title"] = commit_title

        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/repos/{repo}/pulls/{pr_number}/merge",
                headers=self._headers(),
                json=payload,
                timeout=20.0,
            )
            if resp.status_code == 200:
                return True
            return False

    async def close_issue(self, repo: str, issue_number: int, comment: str | None = None) -> None:
        """Closes a GitHub issue, optionally adding a final comment."""
        if comment:
            await self.create_issue_comment(repo, issue_number, comment)

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self.base_url}/repos/{repo}/issues/{issue_number}",
                headers=self._headers(),
                json={"state": "closed"},
                timeout=15.0,
            )
            resp.raise_for_status()
