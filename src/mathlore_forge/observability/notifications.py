"""Notification service for dispatching operator alerts and updates to Dominic Kramer."""

from __future__ import annotations

import email.message
import logging
import os
import smtplib
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_OPERATOR_EMAIL = os.getenv("ALLOWED_ADMIN_EMAIL", "DominicKramer@gmail.com")


class NotificationService:
    """Dispatches notifications to the operator via email and logs."""

    def __init__(self, recipient_email: str | None = None):
        self.recipient_email = recipient_email or os.getenv("ALLOWED_ADMIN_EMAIL", DEFAULT_OPERATOR_EMAIL)
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SMTP_FROM", "forge@mathlore.org")

    def notify_plan_ready(
        self,
        repo: str,
        issue_number: int,
        issue_title: str,
        revision: int = 1,
        issue_url: str | None = None,
    ) -> bool:
        """Dispatches an alert that a new plan/proposal is ready for Dominic's review."""
        issue_link = issue_url or f"https://github.com/{repo}/issues/{issue_number}"
        subject = f"[Mathlore Forge] Plan Proposal Revision {revision} ready for Issue #{issue_number}: {issue_title}"
        body = (
            f"Hello Dominic,\n\n"
            f"The Mathlore Forge Curator Agent has formulated an architectural plan for issue #{issue_number}:\n"
            f"\"{issue_title}\"\n\n"
            f"Review the proposal and leave feedback or approve it on GitHub:\n"
            f"{issue_link}\n\n"
            f"When you are satisfied with the plan, reply to the issue with:\n"
            f"/forge accept\n\n"
            f"---\n"
            f"Mathlore Forge Autonomous Engine"
        )
        return self.send_email(subject=subject, body=body)

    def notify_plan_approved(
        self,
        repo: str,
        issue_number: int,
        issue_title: str,
    ) -> bool:
        """Dispatches an alert that a plan has been approved and execution started."""
        subject = f"[Mathlore Forge] Plan Approved & Execution Started for Issue #{issue_number}: {issue_title}"
        body = (
            f"Hello Dominic,\n\n"
            f"Your approval for issue #{issue_number} (\"{issue_title}\") was received.\n"
            f"The Mathlore Forge authoring worker has started implementing the approved plan.\n\n"
            f"Track live progress on the dashboard: http://localhost:8080\n"
        )
        return self.send_email(subject=subject, body=body)

    def send_email(self, subject: str, body: str) -> bool:
        """Sends an email notification if SMTP is configured; logs otherwise."""
        if not self.smtp_host:
            logger.info("Notification dispatched to %s: %s", self.recipient_email, subject)
            return True

        try:
            msg = email.message.EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            msg.set_content(body)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info("Email notification successfully sent to %s", self.recipient_email)
            return True
        except Exception as e:
            logger.warning("Could not send email notification via SMTP: %s", e)
            return False
