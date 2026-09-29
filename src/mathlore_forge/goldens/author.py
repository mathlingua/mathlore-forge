"""Authoring utilities for generating new golden test cases with scaffolding."""

from __future__ import annotations

from pathlib import Path
import yaml

STARTER_TEST_YAML = """id: {test_id}
name: "{test_name}"
description: "{description}"
tags:
  - mathlingua
  - authoring
prompt: >-
  {prompt}

# Initial content in the workspace before the agent runs
scaffold:
  from_dir: scaffold
  include_default_mlg_json: true

# Verification checks
expectations:
  # Compiler check
  compiler:
    clean: true              # mlg check must find 0 issues

  # Expected file modifications
  files_created: []
  files_modified:
    - content/math.mlg
  files_deleted: []

  # Content assertions on files
  file_assertions:
    - path: content/math.mlg
      should_exist: true
      contains:
        - "Declares:"
      not_contains:
        - "TODO"

  # Trajectory assertions (tools & subagents)
  trajectory:
    tools:
      - name: mlg_check
        must_call: true
      - name: insert_item_after
        must_call: false
    forbidden_tools: []
    subagents: []
    forbidden_subagents: []
"""

STARTER_MLG = """Title: "Math Section"
Id: "11111111-1111-1111-1111-111111111111"


[\\set]
Declares: X
Documented:
. called: "set"
Id: "22222222-2222-2222-2222-222222222222"
"""

STARTER_MLG_JSON = """{
  "name": "MathloreGoldenTest",
  "version": "0",
  "margin": 80,
  "formatOnCheck": true,
  "outputDir": "docs"
}
"""


def scaffold_new_test_case(
    target_dir: Path | str,
    test_id: str,
    test_name: str | None = None,
    description: str | None = None,
    prompt: str | None = None,
) -> Path:
    """Scaffolds a new golden test case directory with test.yaml and starter scaffold files."""
    base_dir = Path(target_dir).resolve() / test_id
    base_dir.mkdir(parents=True, exist_ok=True)

    name = test_name or test_id.replace("-", " ").replace("_", " ").title()
    desc = description or f"Golden test for verifying agent handling of {test_id}."
    prm = prompt or "Author or update the Mathlingua definitions in content/math.mlg as specified."

    # 1. Write test.yaml
    test_yaml_content = STARTER_TEST_YAML.format(
        test_id=test_id,
        test_name=name,
        description=desc,
        prompt=prm,
    )
    (base_dir / "test.yaml").write_text(test_yaml_content, encoding="utf-8")

    # 2. Write scaffold directory
    scaffold_dir = base_dir / "scaffold"
    scaffold_content_dir = scaffold_dir / "content"
    scaffold_content_dir.mkdir(parents=True, exist_ok=True)

    (scaffold_dir / "mlg.json").write_text(STARTER_MLG_JSON, encoding="utf-8")
    (scaffold_content_dir / "math.mlg").write_text(STARTER_MLG, encoding="utf-8")

    return base_dir
