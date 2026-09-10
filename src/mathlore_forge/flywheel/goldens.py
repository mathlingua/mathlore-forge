"""Golden test case generator and regression test evaluation suite."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mathlore_forge.db.schema import GoldenRecord
from mathlore_forge.db.store import MathloreStore
from mathlore_forge.mlg.client import MlgClient


@dataclass
class EvalCaseResult:
    case_id: str
    name: str
    passed: bool
    compiler_clean: bool
    symbols_verified: bool
    citations_verified: bool
    error_details: list[str]


@dataclass
class EvalResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_results: list[EvalCaseResult]


class GoldenManager:
    """Creates golden test cases from approved sessions and runs regression evaluations."""

    def __init__(self, store: MathloreStore, goldens_dir: Path | str = "./goldens"):
        self.store = store
        self.goldens_dir = Path(goldens_dir)
        self.goldens_dir.mkdir(parents=True, exist_ok=True)

    def record_golden(
        self,
        session_id: str,
        name: str,
        prompt: str,
        plan_summary: str,
        expected_symbols: list[str],
        generated_source: str,
        citations: list[str],
    ) -> GoldenRecord:
        """Saves a golden test case into JSON file and DB record."""
        case_id = f"golden_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{session_id[:8]}"
        file_path = self.goldens_dir / f"{case_id}.json"

        data = {
            "id": case_id,
            "name": name,
            "session_id": session_id,
            "prompt": prompt,
            "plan_summary": plan_summary,
            "expected_symbols": expected_symbols,
            "expected_source": generated_source,
            "citations": citations,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        record = GoldenRecord(
            id=case_id,
            name=name,
            prompt=prompt,
            plan_summary=plan_summary,
            expected_symbols=expected_symbols,
            expected_source=generated_source,
            citations=citations,
            file_path=str(file_path),
        )

        self.store.save_golden(record)
        return record

    def run_eval(self, mlg_client: MlgClient) -> EvalResult:
        """Runs regression checks across all golden test cases."""
        case_files = sorted(self.goldens_dir.glob("*.json"))
        results: list[EvalCaseResult] = []

        for cf in case_files:
            with open(cf, "r", encoding="utf-8") as f:
                case_data = json.load(f)

            case_id = case_data.get("id", cf.stem)
            name = case_data.get("name", "Unnamed Test Case")
            expected_source = case_data.get("expected_source", "")
            expected_symbols = case_data.get("expected_symbols", [])
            citations = case_data.get("citations", [])

            errors: list[str] = []
            symbols_ok = True
            citations_ok = True

            # Verify symbols
            for sym in expected_symbols:
                if sym not in expected_source:
                    symbols_ok = False
                    errors.append(f"Missing expected symbol: '{sym}'")

            # Verify citations
            if not citations or len(citations) == 0:
                citations_ok = False
                errors.append("Golden case lacks reputable citations")

            # Check compiler validity by running mlg check on mathlore collection
            check_rep = mlg_client.check()
            compiler_ok = check_rep.successful

            if not compiler_ok:
                errors.append(f"Compiler check has {check_rep.issue_count} error(s)")

            passed = compiler_ok and symbols_ok and citations_ok
            results.append(
                EvalCaseResult(
                    case_id=case_id,
                    name=name,
                    passed=passed,
                    compiler_clean=compiler_ok,
                    symbols_verified=symbols_ok,
                    citations_verified=citations_ok,
                    error_details=errors,
                )
            )

        total = len(results)
        passed_cnt = sum(1 for r in results if r.passed)
        failed_cnt = total - passed_cnt

        return EvalResult(
            total_cases=total,
            passed_cases=passed_cnt,
            failed_cases=failed_cnt,
            case_results=results,
        )
