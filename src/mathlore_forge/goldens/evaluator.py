"""Evaluation engine for validating agent results against golden expectations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from mathlore_forge.goldens.models import GoldenTestCase
from mathlore_forge.goldens.sandbox import FileDiffSummary
from mathlore_forge.goldens.trajectory import Trajectory
from mathlore_forge.mlg.client import MlgClient


class AssertionResult(BaseModel):
    """Result of an individual check."""

    name: str = Field(description="Name or description of the assertion.")
    category: str = Field(description="Category (compiler, files, content, trajectory).")
    passed: bool
    expected: Any = None
    actual: Any = None
    message: str = ""


class EvaluationReport(BaseModel):
    """Aggregated evaluation report for a test run."""

    test_id: str
    test_name: str
    passed: bool
    assertions: list[AssertionResult] = Field(default_factory=list)
    failure_messages: list[str] = Field(default_factory=list)
    summary: str = ""

    def save_json(self, path: Path | str) -> None:
        """Saves the report as a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, default=str)


class Evaluator:
    """Evaluates agent performance against a golden test case."""

    def __init__(self, mlg_bin: str = "mlg"):
        self.mlg_bin = mlg_bin

    def run_check(
        self,
        workspace_dir: Path,
        paths: list[str] | None = None,
    ) -> tuple[bool, int, list[str]]:
        """Runs compiler check on workspace using MlgClient."""
        client = MlgClient(content_root=workspace_dir, mlg_bin=self.mlg_bin)
        report = client.check(paths=paths)
        messages = [d.format_line() for d in report.diagnostics]
        return report.successful, report.issue_count, messages

    def evaluate(
        self,
        test_case: GoldenTestCase,
        workspace_dir: Path,
        diff: FileDiffSummary,
        trajectory: Trajectory,
    ) -> EvaluationReport:
        """Executes all verifications and returns a comprehensive report."""
        assertions: list[AssertionResult] = []
        expectations = test_case.expectations

        # ---------------------------------------------------------------------
        # 1. Compiler Expectations
        # ---------------------------------------------------------------------
        if expectations.compiler and expectations.compiler.enabled:
            successful, err_count, msgs = self.run_check(
                workspace_dir,
                paths=expectations.compiler.paths,
            )

            if expectations.compiler.clean:
                clean_pass = successful and err_count == 0
                assertions.append(
                    AssertionResult(
                        name="compiler_clean_check",
                        category="compiler",
                        passed=clean_pass,
                        expected="0 errors, successful check",
                        actual=f"{err_count} error(s): {', '.join(msgs[:3])}" if not clean_pass else "0 errors",
                        message="" if clean_pass else f"Compiler check failed with {err_count} errors: {', '.join(msgs[:3])}",
                    )
                )
            elif expectations.compiler.max_errors is not None:
                max_err_pass = err_count <= expectations.compiler.max_errors
                assertions.append(
                    AssertionResult(
                        name="compiler_max_errors",
                        category="compiler",
                        passed=max_err_pass,
                        expected=f"<= {expectations.compiler.max_errors} error(s)",
                        actual=f"{err_count} error(s)",
                        message="" if max_err_pass else f"Compiler reported {err_count} errors (max allowed: {expectations.compiler.max_errors}).",
                    )
                )

        # ---------------------------------------------------------------------
        # 2. File Change Expectations
        # ---------------------------------------------------------------------
        for expected_created in expectations.files_created:
            passed = expected_created in diff.created_files
            assertions.append(
                AssertionResult(
                    name=f"file_created_{expected_created}",
                    category="files",
                    passed=passed,
                    expected=f"Created: {expected_created}",
                    actual=f"Created files: {diff.created_files}",
                    message="" if passed else f"Expected file '{expected_created}' to be created, but it was not.",
                )
            )

        for expected_mod in expectations.files_modified:
            passed = expected_mod in diff.modified_files
            assertions.append(
                AssertionResult(
                    name=f"file_modified_{expected_mod}",
                    category="files",
                    passed=passed,
                    expected=f"Modified: {expected_mod}",
                    actual=f"Modified files: {diff.modified_files}",
                    message="" if passed else f"Expected file '{expected_mod}' to be modified, but it was not.",
                )
            )

        for expected_del in expectations.files_deleted:
            passed = expected_del in diff.deleted_files
            assertions.append(
                AssertionResult(
                    name=f"file_deleted_{expected_del}",
                    category="files",
                    passed=passed,
                    expected=f"Deleted: {expected_del}",
                    actual=f"Deleted files: {diff.deleted_files}",
                    message="" if passed else f"Expected file '{expected_del}' to be deleted, but it was not.",
                )
            )

        # ---------------------------------------------------------------------
        # 3. File Content Assertions
        # ---------------------------------------------------------------------
        for fa in expectations.file_assertions:
            target_file = workspace_dir / fa.path
            file_exists = target_file.is_file()

            if fa.should_exist:
                assertions.append(
                    AssertionResult(
                        name=f"file_exists_{fa.path}",
                        category="content",
                        passed=file_exists,
                        expected="File exists",
                        actual="File exists" if file_exists else "File does not exist",
                        message="" if file_exists else f"File '{fa.path}' was expected to exist.",
                    )
                )

                if file_exists:
                    content = target_file.read_text(encoding="utf-8", errors="replace")

                    # Check contains
                    for sub in fa.contains:
                        sub_pass = sub in content
                        assertions.append(
                            AssertionResult(
                                name=f"contains_{fa.path}",
                                category="content",
                                passed=sub_pass,
                                expected=f"Contains: '{sub}'",
                                actual="Present" if sub_pass else "Not found in content",
                                message="" if sub_pass else f"File '{fa.path}' did not contain expected substring '{sub}'.",
                            )
                        )

                    # Check not contains
                    for nsub in fa.not_contains:
                        nsub_pass = nsub not in content
                        assertions.append(
                            AssertionResult(
                                name=f"not_contains_{fa.path}",
                                category="content",
                                passed=nsub_pass,
                                expected=f"Does NOT contain: '{nsub}'",
                                actual="Absent" if nsub_pass else "Found forbidden substring in content",
                                message="" if nsub_pass else f"File '{fa.path}' contained forbidden substring '{nsub}'.",
                            )
                        )

                    # Check regex
                    for pattern in fa.matches_regex:
                        rgx_pass = bool(re.search(pattern, content, re.MULTILINE))
                        assertions.append(
                            AssertionResult(
                                name=f"regex_match_{fa.path}",
                                category="content",
                                passed=rgx_pass,
                                expected=f"Matches regex: /{pattern}/",
                                actual="Matched" if rgx_pass else "Pattern did not match",
                                message="" if rgx_pass else f"File '{fa.path}' did not match regex /{pattern}/.",
                            )
                        )

                    for npattern in fa.not_matches_regex:
                        nrgx_pass = not bool(re.search(npattern, content, re.MULTILINE))
                        assertions.append(
                            AssertionResult(
                                name=f"not_regex_match_{fa.path}",
                                category="content",
                                passed=nrgx_pass,
                                expected=f"Does NOT match regex: /{npattern}/",
                                actual="Did not match" if nrgx_pass else "Matched forbidden pattern",
                                message="" if nrgx_pass else f"File '{fa.path}' matched forbidden regex /{npattern}/.",
                            )
                        )

                    # Exact content
                    if fa.exact_content is not None:
                        exact_pass = (content.strip() == fa.exact_content.strip())
                        assertions.append(
                            AssertionResult(
                                name=f"exact_content_{fa.path}",
                                category="content",
                                passed=exact_pass,
                                expected="Exact content match",
                                actual="Exact match" if exact_pass else "Content differs",
                                message="" if exact_pass else f"File '{fa.path}' did not match exact expected content.",
                            )
                        )
            else:
                # File should not exist
                assertions.append(
                    AssertionResult(
                        name=f"file_not_exists_{fa.path}",
                        category="content",
                        passed=not file_exists,
                        expected="File should not exist",
                        actual="File does not exist" if not file_exists else "File exists",
                        message="" if not file_exists else f"File '{fa.path}' exists, but was expected to be absent.",
                    )
                )

        # ---------------------------------------------------------------------
        # 4. Trajectory Assertions
        # ---------------------------------------------------------------------
        traj_exp = expectations.trajectory

        # Tool calls
        for tool_exp in traj_exp.tools:
            calls = trajectory.get_tool_calls(tool_exp.name)
            call_count = len(calls)

            if tool_exp.must_call:
                must_pass = call_count > 0
                assertions.append(
                    AssertionResult(
                        name=f"tool_must_call_{tool_exp.name}",
                        category="trajectory",
                        passed=must_pass,
                        expected=f"Tool '{tool_exp.name}' called at least once",
                        actual=f"Called {call_count} time(s)",
                        message="" if must_pass else f"Required tool '{tool_exp.name}' was never called.",
                    )
                )

            if tool_exp.min_calls is not None:
                min_pass = call_count >= tool_exp.min_calls
                assertions.append(
                    AssertionResult(
                        name=f"tool_min_calls_{tool_exp.name}",
                        category="trajectory",
                        passed=min_pass,
                        expected=f">= {tool_exp.min_calls} call(s)",
                        actual=f"{call_count} call(s)",
                        message="" if min_pass else f"Tool '{tool_exp.name}' called {call_count} times, expected >= {tool_exp.min_calls}.",
                    )
                )

            if tool_exp.max_calls is not None:
                max_pass = call_count <= tool_exp.max_calls
                assertions.append(
                    AssertionResult(
                        name=f"tool_max_calls_{tool_exp.name}",
                        category="trajectory",
                        passed=max_pass,
                        expected=f"<= {tool_exp.max_calls} call(s)",
                        actual=f"{call_count} call(s)",
                        message="" if max_pass else f"Tool '{tool_exp.name}' called {call_count} times, expected <= {tool_exp.max_calls}.",
                    )
                )

            if tool_exp.with_args:
                args_matched = False
                for c in calls:
                    match = all(c.args.get(k) == v for k, v in tool_exp.with_args.items())
                    if match:
                        args_matched = True
                        break
                assertions.append(
                    AssertionResult(
                        name=f"tool_args_match_{tool_exp.name}",
                        category="trajectory",
                        passed=args_matched,
                        expected=f"Args matching: {tool_exp.with_args}",
                        actual="Matched call found" if args_matched else f"No call matched in {len(calls)} call(s)",
                        message="" if args_matched else f"Tool '{tool_exp.name}' was not called with expected arguments {tool_exp.with_args}.",
                    )
                )

        # Forbidden tools
        for forb_tool in traj_exp.forbidden_tools:
            forb_pass = not trajectory.has_tool_call(forb_tool)
            assertions.append(
                AssertionResult(
                    name=f"forbidden_tool_{forb_tool}",
                    category="trajectory",
                    passed=forb_pass,
                    expected=f"Tool '{forb_tool}' must NOT be called",
                    actual="Not called" if forb_pass else f"Called {trajectory.count_tool_calls(forb_tool)} time(s)",
                    message="" if forb_pass else f"Forbidden tool '{forb_tool}' was called.",
                )
            )

        # Subagents
        for sub_exp in traj_exp.subagents:
            sub_count = trajectory.count_subagent_runs(sub_exp.name)
            if sub_exp.must_run:
                sub_pass = sub_count > 0
                assertions.append(
                    AssertionResult(
                        name=f"subagent_must_run_{sub_exp.name}",
                        category="trajectory",
                        passed=sub_pass,
                        expected=f"Subagent '{sub_exp.name}' run at least once",
                        actual=f"Run {sub_count} time(s)",
                        message="" if sub_pass else f"Required subagent '{sub_exp.name}' was not run.",
                    )
                )

        for forb_sub in traj_exp.forbidden_subagents:
            forb_sub_pass = not trajectory.has_subagent_run(forb_sub)
            assertions.append(
                AssertionResult(
                    name=f"forbidden_subagent_{forb_sub}",
                    category="trajectory",
                    passed=forb_sub_pass,
                    expected=f"Subagent '{forb_sub}' must NOT run",
                    actual="Not run" if forb_sub_pass else f"Run {trajectory.count_subagent_runs(forb_sub)} time(s)",
                    message="" if forb_sub_pass else f"Forbidden subagent '{forb_sub}' was executed.",
                )
            )

        # Total tool limits
        total_calls = len(trajectory.tool_calls)
        if traj_exp.min_total_tool_calls is not None:
            tot_min_pass = total_calls >= traj_exp.min_total_tool_calls
            assertions.append(
                AssertionResult(
                    name="min_total_tool_calls",
                    category="trajectory",
                    passed=tot_min_pass,
                    expected=f">= {traj_exp.min_total_tool_calls}",
                    actual=str(total_calls),
                    message="" if tot_min_pass else f"Total tool calls {total_calls} < min {traj_exp.min_total_tool_calls}.",
                )
            )

        if traj_exp.max_total_tool_calls is not None:
            tot_max_pass = total_calls <= traj_exp.max_total_tool_calls
            assertions.append(
                AssertionResult(
                    name="max_total_tool_calls",
                    category="trajectory",
                    passed=tot_max_pass,
                    expected=f"<= {traj_exp.max_total_tool_calls}",
                    actual=str(total_calls),
                    message="" if tot_max_pass else f"Total tool calls {total_calls} > max {traj_exp.max_total_tool_calls}.",
                )
            )

        # ---------------------------------------------------------------------
        # Final Aggregation
        # ---------------------------------------------------------------------
        failures = [a.message for a in assertions if not a.passed and a.message]
        passed = len(failures) == 0
        summary = (
            f"PASSED ({len(assertions)} assertions verified)"
            if passed
            else f"FAILED ({len(failures)} of {len(assertions)} assertions failed)"
        )

        return EvaluationReport(
            test_id=test_case.id,
            test_name=test_case.name,
            passed=passed,
            assertions=assertions,
            failure_messages=failures,
            summary=summary,
        )
