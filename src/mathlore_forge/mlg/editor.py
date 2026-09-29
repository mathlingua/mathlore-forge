"""Content editor and parser helpers for Mathlingua (.mlg) files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ItemInfo:
    """Information about an identified item within a Mathlingua file."""
    id: str
    file_path: Path
    relative_path: str
    start_line: int  # 1-indexed
    end_line: int    # 1-indexed
    content: str


@dataclass
class InsertResult:
    """Result of inserting an item into a Mathlingua file."""
    file_path: Path
    relative_path: str
    after_id: str
    inserted_line: int
    preview: str


@dataclass
class ReplaceResult:
    """Result of replacing an item in a Mathlingua file."""
    file_path: Path
    relative_path: str
    item_id: str
    start_line: int
    end_line: int
    preview: str


def clean_item_id(item_id: str) -> str:
    """Normalizes an item ID string by removing quotes, whitespace, and 'Id:' prefix."""
    s = item_id.strip()
    if s.startswith("Id:"):
        s = s[3:].strip()
    return s.strip("\"'")


def resolve_file_path(content_root: Path, file_path: str | Path) -> Path:
    """Resolves a file path against the content root, supporting relative, short, and absolute paths."""
    root = content_root.resolve()
    p = Path(file_path)

    # 1. Absolute path check
    if p.is_absolute():
        if p.exists():
            return p
        # Check if absolute path was given relative to some other root
        candidate = root / p.relative_to(p.anchor)
        if candidate.exists():
            return candidate

    # 2. Direct relative to root
    direct = root / p
    if direct.exists():
        return direct

    # 3. Under content/ subdirectory if root has content/
    if (root / "content").is_dir() and not str(p).startswith("content"):
        content_rel = root / "content" / p
        if content_rel.exists():
            return content_rel

    # 4. Search recursively for matching filename
    filename = p.name
    for match in root.rglob(filename):
        if match.is_file():
            return match

    # 5. Fallback for new files: if content/ exists and path doesn't start with content, put in content/
    if (root / "content").is_dir() and not str(p).startswith("content"):
        return root / "content" / p
    return direct


def read_content_file(content_root: Path, file_path: str | Path) -> str:
    """Reads a Mathlingua file from the collection."""
    resolved = resolve_file_path(content_root, file_path)
    if not resolved.is_file():
        raise FileNotFoundError(f"File not found: {file_path} (resolved to {resolved})")
    return resolved.read_text(encoding="utf-8")


def write_content_file(content_root: Path, file_path: str | Path, content: str) -> Path:
    """Writes or overwrites a Mathlingua file in the collection, creating directories if needed."""
    resolved = resolve_file_path(content_root, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return resolved


def _find_item_in_text(text: str, target_id: str, file_path: Path, content_root: Path) -> ItemInfo | None:
    lines = text.splitlines()
    cleaned_target = clean_item_id(target_id)
    id_pattern = re.compile(rf'^\s*Id:\s*["\']?{re.escape(cleaned_target)}["\']?\s*$')

    target_idx = None
    for i, line in enumerate(lines):
        if id_pattern.match(line):
            target_idx = i
            break

    if target_idx is None:
        return None

    # Scan backwards to locate start of this top-level group
    start_idx = target_idx
    while start_idx > 0 and lines[start_idx - 1].strip():
        start_idx -= 1

    item_lines = lines[start_idx : target_idx + 1]
    item_content = "\n".join(item_lines)

    try:
        rel_path = str(file_path.relative_to(content_root))
    except ValueError:
        rel_path = str(file_path)

    return ItemInfo(
        id=cleaned_target,
        file_path=file_path,
        relative_path=rel_path,
        start_line=start_idx + 1,
        end_line=target_idx + 1,
        content=item_content,
    )


def find_item_by_id(
    content_root: Path,
    item_id: str,
    file_path: str | Path | None = None,
) -> ItemInfo | None:
    """Locates an item by its ID across the collection or in a specific file."""
    root = content_root.resolve()

    # If specific file is given, check it first
    if file_path:
        try:
            resolved = resolve_file_path(root, file_path)
            if resolved.is_file():
                info = _find_item_in_text(resolved.read_text(encoding="utf-8"), item_id, resolved, root)
                if info:
                    return info
        except Exception:
            pass

    # Search all .mlg files in content_root
    for path in root.rglob("*.mlg"):
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
                info = _find_item_in_text(text, item_id, path, root)
                if info:
                    return info
            except Exception:
                continue

    return None


def insert_item_after_id(
    content_root: Path,
    file_path: str | Path | None,
    after_id: str,
    new_content: str,
) -> InsertResult:
    """Inserts `new_content` immediately after the item with ID `after_id`.

    Maintains standard two-blank-line separation between top-level groups.
    """
    root = content_root.resolve()
    cleaned_after_id = clean_item_id(after_id)

    # Find the target item
    item_info = find_item_by_id(root, cleaned_after_id, file_path=file_path)
    if not item_info:
        raise ValueError(
            f"Target item with ID '{cleaned_after_id}' was not found"
            + (f" in {file_path}" if file_path else " in collection")
        )

    target_file = item_info.file_path
    text = target_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    # The item's trailing Id: line is at (item_info.end_line - 1)
    target_idx = item_info.end_line - 1

    # Skip any existing empty lines immediately after target_idx
    next_idx = target_idx + 1
    while next_idx < len(lines) and not lines[next_idx].strip():
        next_idx += 1

    before = lines[: target_idx + 1]
    after = lines[next_idx:]
    new_lines = new_content.strip().splitlines()

    result_lines = before + ["", ""] + new_lines
    if after:
        result_lines += ["", ""] + after

    updated_text = "\n".join(result_lines) + "\n"
    target_file.write_text(updated_text, encoding="utf-8")

    # Preview around insertion
    inserted_line = len(before) + 3
    preview_start = max(0, target_idx - 2)
    preview_end = min(len(result_lines), inserted_line + len(new_lines) + 3)
    preview = "\n".join(result_lines[preview_start:preview_end])

    return InsertResult(
        file_path=target_file,
        relative_path=item_info.relative_path,
        after_id=cleaned_after_id,
        inserted_line=inserted_line,
        preview=preview,
    )


def replace_item_by_id(
    content_root: Path,
    file_path: str | Path | None,
    item_id: str,
    new_content: str,
) -> ReplaceResult:
    """Replaces the item with ID `item_id` with `new_content`."""
    root = content_root.resolve()
    cleaned_id = clean_item_id(item_id)

    item_info = find_item_by_id(root, cleaned_id, file_path=file_path)
    if not item_info:
        raise ValueError(f"Target item with ID '{cleaned_id}' was not found")

    target_file = item_info.file_path
    text = target_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    start_idx = item_info.start_line - 1
    end_idx = item_info.end_line - 1

    before = lines[:start_idx]
    after = lines[end_idx + 1 :]
    new_lines = new_content.strip().splitlines()

    result_lines = before + new_lines + after
    updated_text = "\n".join(result_lines) + "\n"
    target_file.write_text(updated_text, encoding="utf-8")

    preview_start = max(0, start_idx - 2)
    preview_end = min(len(result_lines), start_idx + len(new_lines) + 2)
    preview = "\n".join(result_lines[preview_start:preview_end])

    return ReplaceResult(
        file_path=target_file,
        relative_path=item_info.relative_path,
        item_id=cleaned_id,
        start_line=item_info.start_line,
        end_line=start_idx + len(new_lines),
        preview=preview,
    )
