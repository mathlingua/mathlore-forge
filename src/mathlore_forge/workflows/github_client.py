"""GitHub API client supporting GitHub App and PAT authentication."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Sequence
import httpx
from pydantic import BaseModel, Field

from mathlore_forge.config import ensure_env_loaded

ensure_env_loaded()


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
    head_sha: str = ""
    state: str
    html_url: str
    merged: bool = False


FORGE_BOT_MARKER = "<!-- mathlore-forge-bot -->"


class GitHubClient:
    """Client for interacting with the GitHub REST API."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
    ):
        ensure_env_loaded()
        raw_token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
        clean = raw_token.strip().strip("'\"")
        if clean.startswith("Bearer "):
            clean = clean[7:].strip()
        elif clean.startswith("token "):
            clean = clean[6:].strip()
        self.token = clean or None
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Mathlore-Forge",
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
                head_sha=data.get("head", {}).get("sha", ""),
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
                head_sha=data.get("head", {}).get("sha", ""),
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
        if FORGE_BOT_MARKER not in body:
            body = f"{FORGE_BOT_MARKER}\n\n{body}"
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
        if not self.token:
            raise ValueError(
                "GITHUB_TOKEN is missing or empty in the runtime environment. "
                "Please ensure GITHUB_TOKEN has an active version in GCP Secret Manager."
            )
        if FORGE_BOT_MARKER not in body:
            body = f"{FORGE_BOT_MARKER}\n\n{body}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/repos/{repo}/issues/{issue_or_pr_number}/comments",
                headers=self._headers(),
                json={"body": body},
                timeout=15.0,
            )
            if resp.status_code == 401:
                raise ValueError(
                    f"GitHub API rejected GITHUB_TOKEN (401 Unauthorized) when commenting on {repo}#{issue_or_pr_number}. "
                    "Please verify that GITHUB_TOKEN is valid, unexpired, and has 'Issues' (Read and Write) permissions."
                )
            if resp.status_code == 403:
                raise ValueError(
                    f"GitHub API returned 403 Forbidden when commenting on {repo}#{issue_or_pr_number}. "
                    "Please verify that GITHUB_TOKEN has write access to this repository."
                )
            resp.raise_for_status()
            data = resp.json()
            return data.get("html_url", "")

    async def list_issue_comments(self, repo: str, issue_number: int) -> list[dict[str, Any]]:
        """Lists all comments on an issue or pull request."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{repo}/issues/{issue_number}/comments",
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return []

    async def request_reviewers(self, repo: str, pr_number: int, reviewers: Sequence[str]) -> None:
        """Requests reviews from specified GitHub usernames."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/repos/{repo}/pulls/{pr_number}/requested_reviewers",
                    headers=self._headers(),
                    json={"reviewers": list(reviewers)},
                    timeout=15.0,
                )
                if resp.status_code == 422:
                    # 422 occurs if a requested reviewer is the PR author or already requested
                    return
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 422:
                return
            raise

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

    async def get_combined_status(self, repo: str, ref: str) -> str:
        """Returns the combined commit status: 'success', 'pending', 'failure', or 'none'."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{repo}/commits/{ref}/status",
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                total_count = data.get("total_count", 0)
                if total_count == 0:
                    return "none"
                return data.get("state", "none")
            return "none"

    async def get_check_runs_status(self, repo: str, ref: str) -> tuple[str, list[str]]:
        """Returns check runs status ('success', 'pending', 'failure', or 'none') and failing check names."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{repo}/commits/{ref}/check-runs",
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                runs = data.get("check_runs", [])
                if not runs:
                    return "none", []
                failing: list[str] = []
                has_pending = False
                for r in runs:
                    st = r.get("status")
                    conclusion = r.get("conclusion")
                    if st != "completed":
                        has_pending = True
                    elif conclusion not in ("success", "neutral", "skipped"):
                        failing.append(r.get("name", "check"))
                if failing:
                    return "failure", failing
                if has_pending:
                    return "pending", []
                return "success", []
            return "none", []

    async def wait_for_checks_to_pass(
        self,
        repo: str,
        ref: str,
        timeout_seconds: int = 180,
        poll_interval: int = 5,
    ) -> tuple[bool, str]:
        """Polls commit statuses and check runs until they succeed, fail, or timeout."""
        import asyncio

        start = time.perf_counter()
        while time.perf_counter() - start < timeout_seconds:
            status = await self.get_combined_status(repo, ref)
            check_status, failing = await self.get_check_runs_status(repo, ref)

            if status == "failure" or check_status == "failure":
                failing_names = ", ".join(failing) if failing else "commit status check"
                return False, f"Check run failed ({failing_names})"

            # If both are 'none', there are no GitHub Actions or status checks configured
            if status in ("success", "none") and check_status in ("success", "none"):
                return True, "All checks passed (or no checks configured)"

            await asyncio.sleep(poll_interval)

        return False, f"Timed out waiting for checks to complete after {timeout_seconds}s"
