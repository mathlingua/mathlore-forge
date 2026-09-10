"""Mathlingua authoring agent with self-repair compiler loops and guardrails."""

from dataclasses import dataclass
from pathlib import Path
from google.antigravity import Agent

from rich.console import Console
from mathlore_forge.agents.base import create_agent_config, run_agent_turn
from mathlore_forge.db.schema import GapRecord, PhaseType, TodoItemRecord, TodoStatus
from mathlore_forge.db.store import MathloreStore
from mathlore_forge.flywheel.learner import FeedbackLearner
from mathlore_forge.mlg.client import MlgClient
from mathlore_forge.telemetry.tracer import get_telemetry_manager

console = Console()


@dataclass
class AuthoringResult:
    item_id: str
    success: bool
    written_code: str = ""
    error_message: str | None = None
    gap_flagged: bool = False
    gap_details: dict[str, str] | None = None


class MathlinguaAuthorAgent:
    """Manages authoring of specific TODO items using Antigravity Agent and compiler checks."""

    def __init__(
        self,
        mlg_client: MlgClient,
        store: MathloreStore,
        learner: FeedbackLearner,
        model: str | None = None,
        skills_dir: Path | str = "./skills",
        max_compile_retries: int = 5,
    ):
        self.mlg_client = mlg_client
        self.store = store
        self.learner = learner
        self.model = model
        self.skills_dir = Path(skills_dir)
        self.max_compile_retries = max_compile_retries
        self.telemetry = get_telemetry_manager()

    def author_item(self, item: TodoItemRecord) -> AuthoringResult:
        """Authors a single TODO item serially with validation and error-recovery."""
        self.telemetry.set_activity("Authoring", f"Authoring item: {item.title} ({item.kind})")
        gap_detected: dict[str, str] | None = None

        def read_mathlore_file(path: str) -> str:
            """Reads the contents of a file in the Mathlore repo (e.g. content/02_relations.mlg)."""
            full_path = self.mlg_client.repo_path / path
            if not full_path.exists():
                return f"File '{path}' does not exist yet."
            return full_path.read_text(encoding="utf-8")

        def search_mathlore(query: str) -> str:
            """Searches existing Mathlore items by command key, heading, or keyword."""
            rep = self.mlg_client.search(query)
            if not rep.matches:
                return f"No items found matching '{query}'."
            out = [f"Found {rep.total_matches} match(es):"]
            for m in rep.matches[:6]:
                out.append(f"  - [{m.kind}] {m.heading} (file: {m.file_path}, keys: {m.definition_keys})")
            return "\n".join(out)

        def flag_mathlingua_gap(concept: str, description: str, attempted_representation: str = "") -> str:
            """Flags that Mathlingua language lacks expressiveness for a concept. Stops to notify user."""
            nonlocal gap_detected
            gap_detected = {
                "concept": concept,
                "description": description,
                "attempted_representation": attempted_representation,
            }
            # Record in database
            self.store.record_gap(
                GapRecord(
                    item_id=item.id,
                    concept=concept,
                    description=description,
                    attempted_representation=attempted_representation,
                )
            )
            self.store.update_todo_status(
                item.id,
                TodoStatus.BLOCKED_GAP,
                error_message=f"Language gap flagged for concept '{concept}': {description}",
            )
            return f"Language gap recorded for '{concept}'. Flagged for human developer review."

        learned_context = self.learner.get_prompt_context(PhaseType.AUTHORING)

        system_instructions = (
            "You are a master mathematical logician and author of Mathlingua (.mlg) documents for Mathlore.\n"
            "You strictly follow all Mathlingua syntax rules defined in your skills.\n"
            "CRITICAL RULES:\n"
            "1. You must write VALID Mathlingua code according to the structural and formulation language rules.\n"
            "2. For every new definition or theorem, you MUST include a reputable textbook or paper citation.\n"
            "3. Every top-level item (Defines, States, Theorem, Axiom) must omit `Id:`. Let `mlg check` generate the UUID.\n"
            "4. NEVER invent fake language features or unsupported syntax. If Mathlingua lacks a feature to express "
            "a concept, call `flag_mathlingua_gap` immediately so the language author can address it!\n"
            "5. Return only the new/updated Mathlingua code snippet to insert or append to the target file, enclosed in ```mathlingua code blocks.\n\n"
            f"{learned_context}"
        )

        all_skills = [p for p in self.skills_dir.iterdir() if p.is_dir()]
        agent_config = create_agent_config(
            system_instructions=system_instructions,
            skills_dirs=all_skills,
            tools=[read_mathlore_file, search_mathlore, flag_mathlingua_gap],
            model=self.model,
        )

        prompt = (
            f"Please author the following item for Mathlore:\n"
            f"Title: {item.title}\n"
            f"Target Section: {item.section_path}\n"
            f"Kind: {item.kind}\n"
            f"Purpose: {item.purpose}\n"
            f"What to cover: {item.what_to_cover}\n"
            f"Citations: {item.citations}\n\n"
            f"Check existing definitions in {item.section_path} or related files to ensure proper symbol usage. "
            f"Then produce the clean Mathlingua snippet."
        )

        agent = Agent(agent_config)
        import asyncio

        console.print(f"[bold cyan]✍ Authoring Mathlingua snippet for [bold]{item.title}[/bold] ({item.kind})...[/bold cyan]")
        response_text = asyncio.run(
            run_agent_turn(
                agent,
                prompt,
                span_name=f"author_item_{item.id}",
                status_message=f"Drafting initial formulation for {item.title}",
            )
        )

        if gap_detected:
            return AuthoringResult(
                item_id=item.id,
                success=False,
                gap_flagged=True,
                gap_details=gap_detected,
                error_message=f"Blocked by language gap: {gap_detected.get('concept')}",
            )

        # Extract code snippet
        code = self._extract_code(response_text)
        if not code.strip():
            return AuthoringResult(
                item_id=item.id,
                success=False,
                error_message="Agent did not produce any code block.",
            )

        # Verify citation guardrail
        if not self._verify_citations(code, item):
            return AuthoringResult(
                item_id=item.id,
                success=False,
                written_code=code,
                error_message="Item rejected: Missing valid citations from reputable sources.",
            )

        # Append or update target file
        target_path = self.mlg_client.repo_path / item.section_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        original_content = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        updated_content = (
            f"{original_content.rstrip()}\n\n{code.strip()}\n"
            if original_content.strip()
            else f"{code.strip()}\n"
        )
        target_path.write_text(updated_content, encoding="utf-8")

        # Compile self-repair loop
        for attempt in range(self.max_compile_retries):
            console.print(f"[dim]  Attempt {attempt + 1}/{self.max_compile_retries}: Validating with mlg check...[/dim]")
            check_rep = self.mlg_client.check(paths=[item.section_path])
            if check_rep.successful:
                # Format code
                self.mlg_client.format()
                final_code = target_path.read_text(encoding="utf-8")
                self.store.update_todo_status(item.id, TodoStatus.DONE, source_code=final_code)
                console.print("[bold green]  ✔ mlg check passed cleanly (0 errors).[/bold green]")
                return AuthoringResult(item_id=item.id, success=True, written_code=final_code)

            # Compiler found errors, let's trigger self-repair turn
            errors_summary = "\n".join([f"- line {d.row}: {d.message}" for d in check_rep.diagnostics[:5]])
            console.print(f"[yellow]  ⚠ Compiler reported {check_rep.issue_count} issue(s). Initiating self-repair attempt {attempt + 1}/{self.max_compile_retries}...[/yellow]")
            for d in check_rep.diagnostics[:3]:
                console.print(f"[dim red]    ↳ line {d.row}: {d.message}[/dim red]")

            repair_prompt = (
                f"The Mathlingua compiler `mlg check` reported the following errors in your code snippet:\n"
                f"{errors_summary}\n\n"
                f"Original snippet:\n```mathlingua\n{code}\n```\n\n"
                f"Please correct the syntax errors according to your skills and provide the corrected code block. "
                f"If the error is due to a missing feature in Mathlingua, call `flag_mathlingua_gap`."
            )

            repair_resp = asyncio.run(
                run_agent_turn(
                    agent,
                    repair_prompt,
                    span_name=f"repair_attempt_{attempt + 1}_{item.id}",
                    status_message=f"Self-repairing syntax diagnostics (attempt {attempt + 1})",
                )
            )
            if gap_detected:
                # Revert file
                target_path.write_text(original_content, encoding="utf-8")
                return AuthoringResult(
                    item_id=item.id,
                    success=False,
                    gap_flagged=True,
                    gap_details=gap_detected,
                    error_message=f"Blocked by language gap during repair: {gap_detected.get('concept')}",
                )

            repaired_code = self._extract_code(repair_resp)
            if repaired_code.strip():
                code = repaired_code
                updated_content = (
                    f"{original_content.rstrip()}\n\n{code.strip()}\n"
                    if original_content.strip()
                    else f"{code.strip()}\n"
                )
                target_path.write_text(updated_content, encoding="utf-8")

        # If we exhausted retries, revert changes and report failure
        target_path.write_text(original_content, encoding="utf-8")
        self.store.update_todo_status(
            item.id, TodoStatus.FAILED, error_message="Failed compiler check after maximum retries."
        )
        return AuthoringResult(
            item_id=item.id,
            success=False,
            written_code=code,
            error_message="Failed `mlg check` validation after self-repair retries.",
        )

    def _extract_code(self, text: str) -> str:
        if "```mathlingua" in text:
            return text.split("```mathlingua")[1].split("```")[0]
        elif "```mlg" in text:
            return text.split("```mlg")[1].split("```")[0]
        elif "```" in text:
            return text.split("```")[1].split("```")[0]
        return text

    def _verify_citations(self, code: str, item: TodoItemRecord) -> bool:
        """Verifies guardrails: citations must be present either in code or in item specifications."""
        lower_code = code.lower()
        has_citation_in_code = (
            "reference:" in lower_code
            or "resource:" in lower_code
            or "citation" in lower_code
            or "book:" in lower_code
            or "author:" in lower_code
            or "title:" in lower_code
        )
        has_item_citation = bool(item.citations and len(str(item.citations).strip()) > 3)
        return has_citation_in_code or has_item_citation
