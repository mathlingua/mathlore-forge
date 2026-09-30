"""Intent classifier for routing GitHub issues to planning vs direct authoring."""

from __future__ import annotations

import enum
import re
from typing import Sequence


class IssueIntent(str, enum.Enum):
    """Categorization of an issue request."""
    DIRECT_AUTHORING = "DIRECT_AUTHORING"
    HIGHER_ORDER_PLANNING = "HIGHER_ORDER_PLANNING"


# Keywords indicating higher-order planning and curation
PLANNING_KEYWORDS = [
    r"\bplan\b",
    r"\bproposal\b",
    r"\bcurat(e|ion|ing)\b",
    r"\bnext\s+(logical\s+)?(chapter|section|topic|content)\b",
    r"\badd\s+more\s+\w+\s+content\b",
    r"\badd\s+\w+\s+content\b",
    r"\brestructure\b",
    r"\breorganiz(e|ation)\b",
    r"\btone\b",
    r"\btonal\b",
    r"\bprose\b",
    r"\bresources?\b",
    r"\broadmap\b",
    r"\bcurriculum\b",
    r"\boverhaul\b",
    r"\bwhat\s+should\s+be\s+added\b",
    r"\bwhat\s+to\s+add\b",
]

# File pattern for concrete files
MLG_FILE_PATTERN = re.compile(r"[\w/-]+\.mlg")


def classify_issue_intent(
    title: str,
    body: str,
    labels: Sequence[str] | None = None,
) -> IssueIntent:
    """Classifies whether an issue requires a high-level proposal/plan or direct authoring.

    Args:
        title: GitHub issue title.
        body: GitHub issue body text.
        labels: List of label names on the issue.

    Returns:
        IssueIntent.HIGHER_ORDER_PLANNING if abstract, pedagogical, or architectural;
        IssueIntent.DIRECT_AUTHORING if concrete single-item additions to specific files.
    """
    title_lower = title.lower()
    body_lower = (body or "").lower()
    combined_text = f"{title_lower}\n{body_lower}"

    labels = labels or []
    label_names = {l.lower() for l in labels}

    # 1. Explicit label or marker overrides
    if "plan" in label_names or "curation" in label_names or "proposal" in label_names:
        return IssueIntent.HIGHER_ORDER_PLANNING

    if "[plan]" in title_lower or "/plan" in combined_text or "[curate]" in title_lower:
        return IssueIntent.HIGHER_ORDER_PLANNING

    # 2. Check for planning keywords
    for pattern in PLANNING_KEYWORDS:
        if re.search(pattern, combined_text):
            return IssueIntent.HIGHER_ORDER_PLANNING

    # 3. If a specific .mlg file is explicitly targeted and there are no planning keywords,
    # it is likely a direct authoring request
    has_mlg_file = bool(MLG_FILE_PATTERN.search(combined_text))
    has_concrete_directive = any(k in combined_text for k in ["add theorem", "add definition", "add axiom", "insert after", "add proof"])

    if has_mlg_file and has_concrete_directive:
        return IssueIntent.DIRECT_AUTHORING

    # 4. Default: If ambiguous or open-ended, default to planning so Dominic can review proposal first
    if not has_mlg_file:
        return IssueIntent.HIGHER_ORDER_PLANNING

    return IssueIntent.DIRECT_AUTHORING
