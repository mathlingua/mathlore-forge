"""Sanitizer for agent generated summaries and text."""

from __future__ import annotations

import re


def sanitize_author_summary(text: str) -> str:
    """Cleans up author agent output, stripping permission denial messages and internal container paths."""
    if not text:
        return ""

    cleaned = text

    # Remove known noise prefixes
    cleaned = re.sub(r"Cannot search path file:///[^\n]*?\.", "", cleaned)
    cleaned = re.sub(r"error executing cascade step:[^\n]*?no such directory", "", cleaned)

    # Remove inline/multiline pre-tool hook access denials
    cleaned = re.sub(
        r"Access to path .*?\(\"denied by pre-tool hook:.*?\"\)",
        "",
        cleaned,
        flags=re.DOTALL,
    )

    # Filter any remaining lines that contain denial or installation noise
    lines = []
    for line in cleaned.splitlines():
        line_strip = line.strip()
        if "is denied" in line and "Access to path" in line:
            continue
        if "denied by pre-tool hook" in line:
            continue
        if "Cannot search path file:///" in line:
            continue
        if "error executing cascade step:" in line:
            continue
        if "An installation task is currently setting up the Rust toolchain" in line:
            continue
        if "An installation and compilation task for the `mlg` tool is currently running" in line:
            continue
        lines.append(line)

    cleaned = "\n".join(lines)

    # Strip container /tmp paths and replace with clean relative paths
    cleaned = re.sub(r"file:///tmp/forge_[^/]+/content/", "content/", cleaned)
    cleaned = re.sub(r"file:///tmp/forge_[^/]+/", "", cleaned)
    cleaned = re.sub(r"/tmp/forge_[^/]+/content/", "content/", cleaned)
    cleaned = re.sub(r"/tmp/forge_[^/]+/", "", cleaned)

    # Strip /workspace paths if any
    cleaned = re.sub(r"file:///workspace/", "", cleaned)
    cleaned = re.sub(r"/workspace/", "", cleaned)

    # Collapse multiple consecutive empty lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
