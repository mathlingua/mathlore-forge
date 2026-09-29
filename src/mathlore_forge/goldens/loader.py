"""Discovery and loading of golden test cases from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence
import yaml

from mathlore_forge.goldens.models import GoldenTestCase


def load_test_case_from_path(file_path: Path | str) -> GoldenTestCase:
    """Loads a single GoldenTestCase from a YAML or JSON file."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Test case file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(f)
        elif path.suffix == ".json":
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}. Expected .yaml, .yml, or .json")

    case = GoldenTestCase.model_validate(data)
    case.base_dir = path.parent

    # Auto-detect scaffold directory if not specified
    if not case.scaffold.from_dir:
        scaffold_candidate = path.parent / "scaffold"
        if scaffold_candidate.is_dir():
            case.scaffold.from_dir = "scaffold"

    return case


def discover_test_cases(
    root_dir: Path | str = "./golden_tests",
    patterns: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
) -> list[GoldenTestCase]:
    """Recursively discovers all golden test cases under root_dir."""
    root = Path(root_dir).resolve()
    cases: list[GoldenTestCase] = []

    if not root.is_dir():
        # Fallback check for "goldens" directory if golden_tests does not exist
        if (root.parent / "goldens").is_dir():
            root = root.parent / "goldens"
        else:
            return cases

    candidate_files: list[Path] = []
    for ext in ("*.yaml", "*.yml", "*.json"):
        for p in root.rglob(ext):
            name_lower = p.name.lower()
            if name_lower in ("test.yaml", "test.yml", "test.json") or name_lower.endswith("_test.yaml"):
                candidate_files.append(p)

    for cf in sorted(candidate_files):
        try:
            tc = load_test_case_from_path(cf)
            if patterns:
                matched = any(
                    pat.lower() in tc.id.lower() or pat.lower() in tc.name.lower()
                    for pat in patterns
                )
                if not matched:
                    continue

            if tags:
                if not any(t in tc.tags for t in tags):
                    continue

            cases.append(tc)
        except Exception:
            continue

    return cases
