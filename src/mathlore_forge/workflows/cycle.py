"""DBOS durable execution workflow for the 12-step Mathlore generation cycle."""

import asyncio
import json
import time
import uuid
from typing import Any
from dbos import DBOS, DBOSConfig
from pydantic import BaseModel, Field
from rich.console import Console
from rich.prompt import Prompt

from mathlore_forge.config import AppConfig
from mathlore_forge.db.schema import PhaseType, TodoItemRecord, TodoStatus
from mathlore_forge.db.store import MathloreStore
from mathlore_forge.flywheel.goldens import GoldenManager
from mathlore_forge.flywheel.learner import FeedbackLearner
from mathlore_forge.mlg.client import MlgClient
from mathlore_forge.agents.base import run_agent_turn
from mathlore_forge.agents.planner import (
    DetailedPlan,
    HighLevelPlan,
    new_detailed_planner_agent,
    new_high_level_planner_agent,
)
from mathlore_forge.agents.author import MathlinguaAuthorAgent

console = Console()


class WorkflowOptions(BaseModel):
    steering_prompt: str = Field(default="")
    interactive: bool = Field(default=True)
    max_iterations: int = Field(default=1)
    iteration_id: str = Field(default_factory=lambda: f"cycle_{int(time.time())}")


class WorkflowResult(BaseModel):
    iteration_id: str
    successful: bool
    high_level_plan: dict[str, Any] = Field(default_factory=dict)
    detailed_items_count: int = 0
    authored_items_count: int = 0
    golden_test_id: str | None = None
    gaps_count: int = 0
    error_message: str | None = None
    interactive: bool = True


def _prompt_user_decision(prompt_text: str, default: str = "y") -> tuple[bool, str, bool]:
    """
    Prompts user with choices:
      - 'y' / 'yes': approve current step, stay interactive
      - 'a' / 'auto' / 'all' / 'yes to all': approve current step, switch to autonomous mode for all remaining steps
      - 'f' / 'feedback' / <custom critique>: provide guidance or critique

    Returns:
        (approved: bool, feedback: str, switch_to_auto: bool)
    """
    choice = Prompt.ask(
        f"{prompt_text} ([green]y[/green]es / [cyan]a[/cyan]uto / [yellow]f[/yellow]eedback)",
        default=default,
    ).strip()

    choice_lower = choice.lower()
    if choice_lower in ("a", "auto", "all", "yes to all", "yall", "auto-all", "run on auto", "ok run on auto now"):
        console.print("[bold cyan]⚡ Switched to Autonomous Mode: Automatically approving all remaining steps for this run.[/bold cyan]")
        return True, "", True

    if choice_lower in ("y", "yes"):
        return True, "", False

    if choice_lower in ("f", "feedback"):
        fb = Prompt.ask("Enter feedback/guidance")
        return False, fb, False

    # The user directly typed their feedback into the prompt
    return False, choice, False


# --- DBOS Steps ---

@DBOS.step()
def dbos_step_0_sync_layout(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Step 0: Synchronize layout from mlg structure and seed metadata."""
    cfg = AppConfig.model_validate(config_dict)
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    structure = client.structure()
    sections = store.sync_from_collection_structure(structure)
    return {
        "title": structure.title,
        "directories_count": len(structure.directories),
        "files_count": len(structure.files),
        "sections_count": len(sections),
    }


@DBOS.step()
def dbos_step_1_high_level_plan(
    config_dict: dict[str, Any], steering_prompt: str, iteration_id: str
) -> dict[str, Any]:
    """Step 1: Research and produce focused high-level plan."""
    cfg = AppConfig.model_validate(config_dict)
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    learner = FeedbackLearner(store, cfg.paths.flywheel_dir, cfg.paths.skills_dir)
    planner = new_high_level_planner_agent(client, store, learner, model=cfg.models.planner, skills_dir=cfg.paths.skills_dir)

    prompt = (
        "Please propose a focused high-level plan for the next mathematical content to add to Mathlore.\n"
    )
    if steering_prompt:
        prompt += f"User steering instruction: '{steering_prompt}'. Incorporate this directly into the plan.\n"

    raw_response = asyncio.run(
        run_agent_turn(
            planner,
            prompt,
            span_name="plan_high_level",
            status_message="Curriculum Planner reasoning about Mathlore hierarchy and topic expansion",
        )
    )

    # Parse JSON plan
    plan_dict = _extract_json_block(raw_response)
    plan = HighLevelPlan.model_validate(plan_dict)
    return plan.model_dump()


@DBOS.step()
def dbos_step_4_update_hl_flywheel(
    config_dict: dict[str, Any], iteration_id: str, feedback_text: str, plan_summary: str
) -> None:
    """Step 4: Distill user feedback and update planning flywheel skills."""
    if not feedback_text.strip():
        return
    cfg = AppConfig.model_validate(config_dict)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    learner = FeedbackLearner(store, cfg.paths.flywheel_dir, cfg.paths.skills_dir)
    learner.process_feedback(
        iteration_id=iteration_id,
        phase=PhaseType.HIGH_LEVEL_PLAN,
        user_feedback=feedback_text,
        context_summary=plan_summary,
    )


@DBOS.step()
def dbos_step_5_detailed_plan(
    config_dict: dict[str, Any], hl_plan_dict: dict[str, Any], iteration_id: str
) -> dict[str, Any]:
    """Step 5: Create detailed serial TODO specification."""
    cfg = AppConfig.model_validate(config_dict)
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    learner = FeedbackLearner(store, cfg.paths.flywheel_dir, cfg.paths.skills_dir)
    planner = new_detailed_planner_agent(client, store, learner, model=cfg.models.planner, skills_dir=cfg.paths.skills_dir)

    prompt = (
        f"Based on the following approved HighLevelPlan, create a DetailedPlan of serial items:\n"
        f"{json.dumps(hl_plan_dict, indent=2)}\n\n"
        f"Ensure every item includes exact citations and target file paths under content/."
    )

    raw_response = asyncio.run(
        run_agent_turn(
            planner,
            prompt,
            span_name="plan_detailed",
            status_message="Detailed Planner formulating serial TODO items, symbols, and citations",
        )
    )
    detailed_dict = _extract_json_block(raw_response)
    detailed = DetailedPlan.model_validate(detailed_dict)
    return detailed.model_dump()


@DBOS.step()
def dbos_step_7_update_detailed_flywheel(
    config_dict: dict[str, Any], iteration_id: str, feedback_text: str, plan_summary: str
) -> None:
    """Step 7: Record feedback from detailed plan review."""
    if not feedback_text.strip():
        return
    cfg = AppConfig.model_validate(config_dict)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    learner = FeedbackLearner(store, cfg.paths.flywheel_dir, cfg.paths.skills_dir)
    learner.process_feedback(
        iteration_id=iteration_id,
        phase=PhaseType.DETAILED_PLAN,
        user_feedback=feedback_text,
        context_summary=plan_summary,
    )


@DBOS.step()
def dbos_step_8_persist_todo(
    config_dict: dict[str, Any], detailed_plan_dict: dict[str, Any], iteration_id: str
) -> list[str]:
    """Step 8: Persist planned items as TODO in durable store."""
    cfg = AppConfig.model_validate(config_dict)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    items_raw = detailed_plan_dict.get("items", [])

    todo_records = []
    item_ids = []
    for it in items_raw:
        item_id = it.get("id") or f"todo_{uuid.uuid4().hex[:8]}"
        item_ids.append(item_id)
        todo_records.append(
            TodoItemRecord(
                id=item_id,
                iteration_id=iteration_id,
                section_path=it.get("section_path", "content/00_logic/00_logic.mlg"),
                title=it.get("title", "Untitled Item"),
                kind=it.get("kind", "Defines"),
                purpose=it.get("purpose", ""),
                what_to_cover=it.get("what_to_cover", ""),
                citations=it.get("citations", []),
                status=TodoStatus.TODO,
            )
        )

    store.add_todo_items(todo_records)
    return item_ids


@DBOS.step()
def dbos_step_9_10_author_item(
    config_dict: dict[str, Any], item_id: str
) -> dict[str, Any]:
    """Steps 9 & 10: Author single item serially with mlg check self-repair."""
    cfg = AppConfig.model_validate(config_dict)
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    learner = FeedbackLearner(store, cfg.paths.flywheel_dir, cfg.paths.skills_dir)

    todos = store.get_todo_items(status=None)
    target_item = next((t for t in todos if t.id == item_id), None)
    if not target_item:
        return {"success": False, "error": f"Item {item_id} not found."}

    store.update_todo_status(item_id, TodoStatus.IN_PROGRESS)

    author = MathlinguaAuthorAgent(
        mlg_client=client,
        store=store,
        learner=learner,
        model=cfg.models.author,
        skills_dir=cfg.paths.skills_dir,
        max_compile_retries=cfg.execution.max_compile_retries,
    )

    result = author.author_item(target_item)
    return {
        "success": result.success,
        "item_id": result.item_id,
        "written_code": result.written_code,
        "gap_flagged": result.gap_flagged,
        "gap_details": result.gap_details,
        "error_message": result.error_message,
    }


@DBOS.step()
def dbos_step_12_update_authoring_flywheel(
    config_dict: dict[str, Any], iteration_id: str, item_id: str, feedback_text: str
) -> None:
    """Step 12: Record authoring feedback and update writing flywheel."""
    if not feedback_text.strip():
        return
    cfg = AppConfig.model_validate(config_dict)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    learner = FeedbackLearner(store, cfg.paths.flywheel_dir, cfg.paths.skills_dir)
    learner.process_feedback(
        iteration_id=iteration_id,
        phase=PhaseType.AUTHORING,
        user_feedback=feedback_text,
        context_summary=f"Item {item_id}",
    )


@DBOS.step()
def dbos_step_record_golden(
    config_dict: dict[str, Any], iteration_id: str, prompt: str, plan_summary: str, generated_code: str
) -> str:
    """Creates a golden test case capturing this successful iteration."""
    cfg = AppConfig.model_validate(config_dict)
    store = MathloreStore(cfg.dbos_system_database_url or f"sqlite:///{cfg.paths.db_path}")
    goldens = GoldenManager(store, cfg.paths.goldens_dir)

    record = goldens.record_golden(
        session_id=iteration_id,
        name=f"Golden Case {iteration_id}",
        prompt=prompt,
        plan_summary=plan_summary,
        expected_symbols=["\\"],
        generated_source=generated_code,
        citations=["Textbook citation"],
    )
    return record.id


@DBOS.step()
def dbos_step_verify_collection(config_dict: dict[str, Any]) -> bool:
    """Final verification: run full mlg check on Mathlore repository."""
    cfg = AppConfig.model_validate(config_dict)
    client = MlgClient(cfg.paths.mlg_bin, cfg.paths.mathlore_repo)
    report = client.check()
    return report.successful


# --- Main DBOS Workflow ---

@DBOS.workflow()
def mathlore_forge_workflow(config_dict: dict[str, Any], options_dict: dict[str, Any]) -> dict[str, Any]:
    """The master durable DBOS workflow orchestrating Steps 0 through 12."""

    options = WorkflowOptions.model_validate(options_dict)
    iteration_id = options.iteration_id

    # Step 0: Sync Layout
    console.print("\n[bold cyan]▶ Step 0: Synchronizing Mathlore Repository Layout...[/bold cyan]")
    sync_res = dbos_step_0_sync_layout(config_dict)
    console.print(f"[green]  ✔ Synced {sync_res['sections_count']} sections ({sync_res['directories_count']} directories, {sync_res['files_count']} files).[/green]")

    # Step 1: High Level Plan
    console.print("\n[bold cyan]▶ Step 1: Researching & Formulating High-Level Plan...[/bold cyan]")
    hl_plan_dict = dbos_step_1_high_level_plan(config_dict, options.steering_prompt, iteration_id)

    # Step 2 & 3: User Review High Level Plan (interactive or auto)
    hl_feedback = ""
    if options.interactive:
        console.print("\n[bold cyan]=== Proposed High-Level Plan ===[/bold cyan]")
        console.print(f"[bold]Title:[/bold] {hl_plan_dict.get('title')}")
        console.print(f"[bold]Rationale:[/bold] {hl_plan_dict.get('rationale')}")
        console.print(f"[bold]Concepts:[/bold] {', '.join(hl_plan_dict.get('concepts_to_add', []))}")
        console.print(f"[bold]Sources:[/bold] {', '.join(hl_plan_dict.get('reputable_sources', []))}")

        approved, hl_feedback, switch_auto = _prompt_user_decision("\nApprove high-level plan?")
        if switch_auto:
            options.interactive = False

    # Step 4: Update Planning Flywheel
    if hl_feedback:
        console.print("\n[bold cyan]▶ Step 4: Updating Planning Flywheel with User Feedback...[/bold cyan]")
    dbos_step_4_update_hl_flywheel(
        config_dict, iteration_id, hl_feedback, hl_plan_dict.get("title", "")
    )
    if hl_feedback:
        console.print("[green]  ✔ Flywheel guidelines updated.[/green]")

    # Step 5: Detailed Plan
    console.print("\n[bold cyan]▶ Step 5: Formulating Detailed Specification Blueprint...[/bold cyan]")
    detailed_plan_dict = dbos_step_5_detailed_plan(config_dict, hl_plan_dict, iteration_id)

    # Step 6: User Review Detailed Plan
    detailed_feedback = ""
    if options.interactive:
        console.print("\n[bold cyan]=== Detailed Specification Blueprint ===[/bold cyan]")
        console.print(f"[bold]Summary:[/bold] {detailed_plan_dict.get('summary')}")
        for it in detailed_plan_dict.get("items", []):
            console.print(f"  * [{it.get('kind')}] {it.get('title')} -> {it.get('section_path')}")

        approved, detailed_feedback, switch_auto = _prompt_user_decision("\nApprove detailed specification?")
        if switch_auto:
            options.interactive = False

    # Step 7: Update Detailed Flywheel
    if detailed_feedback:
        console.print("\n[bold cyan]▶ Step 7: Updating Detailed Planning Flywheel...[/bold cyan]")
    dbos_step_7_update_detailed_flywheel(
        config_dict, iteration_id, detailed_feedback, detailed_plan_dict.get("summary", "")
    )
    if detailed_feedback:
        console.print("[green]  ✔ Flywheel guidelines updated.[/green]")

    # Step 8: Persist TODO items
    console.print("\n[bold cyan]▶ Step 8: Persisting TODO Items to Database Queue...[/bold cyan]")
    item_ids = dbos_step_8_persist_todo(config_dict, detailed_plan_dict, iteration_id)
    console.print(f"[green]  ✔ Queued {len(item_ids)} item(s) for serial authoring.[/green]")

    # Steps 9 - 12: Serial Authoring
    authored_count = 0
    all_written_code = []
    gaps_count = 0

    for idx, item_id in enumerate(item_ids):
        # Step 9 & 10: Author item serially
        console.print(f"\n[bold cyan]▶ Step 9-10: Serial Authoring [{idx + 1}/{len(item_ids)}]: {item_id}...[/bold cyan]")
        author_res = dbos_step_9_10_author_item(config_dict, item_id)

        if author_res.get("gap_flagged"):
            gaps_count += 1
            console.print(f"\n[bold yellow]Gap in Mathlingua Detected for item {item_id}:[/bold yellow]")
            console.print(json.dumps(author_res.get("gap_details"), indent=2))
            continue

        if not author_res.get("success"):
            console.print(f"[red]Authoring failed for {item_id}: {author_res.get('error_message')}[/red]")
            continue

        authored_count += 1
        written_code = author_res.get("written_code", "")
        all_written_code.append(written_code)

        # Step 11: Review written item
        item_feedback = ""
        if options.interactive:
            console.print(f"\n[green]Item {item_id} authored successfully![/green]")
            console.print(f"Code Preview:\n```mathlingua\n{written_code[:300]}...\n```")
            approved, item_feedback, switch_auto = _prompt_user_decision("Accept item changes?")
            if switch_auto:
                options.interactive = False

        # Step 12: Update authoring flywheel
        if item_feedback:
            console.print(f"[bold cyan]▶ Step 12: Updating authoring flywheel for {item_id}...[/bold cyan]")
        dbos_step_12_update_authoring_flywheel(config_dict, iteration_id, item_id, item_feedback)

    # Generate golden test case if authoring succeeded
    golden_id = None
    if authored_count > 0:
        console.print("\n[bold cyan]▶ Generating Golden Regression Test Case...[/bold cyan]")
        golden_id = dbos_step_record_golden(
            config_dict,
            iteration_id,
            options.steering_prompt or "Standard expansion",
            hl_plan_dict.get("title", ""),
            "\n\n".join(all_written_code),
        )
        console.print(f"[green]  ✔ Golden case recorded: {golden_id}[/green]")

    # Final collection verification
    console.print("\n[bold cyan]▶ Verifying Complete Mathlore Collection with mlg check...[/bold cyan]")
    collection_ok = dbos_step_verify_collection(config_dict)
    if collection_ok:
        console.print("[green]  ✔ Full repository passed compiler checks cleanly.[/green]")
    else:
        console.print("[red]  ✖ Collection verification found issues.[/red]")

    return {
        "iteration_id": iteration_id,
        "successful": collection_ok,
        "high_level_plan": hl_plan_dict,
        "detailed_items_count": len(item_ids),
        "authored_items_count": authored_count,
        "golden_test_id": golden_id,
        "gaps_count": gaps_count,
        "interactive": options.interactive,
    }


# Backwards compatibility alias
mathlore_cycle_workflow = mathlore_forge_workflow


def _extract_json_block(text: str) -> dict[str, Any]:
    clean = text.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()

    # Find boundaries
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1:
        clean = clean[start : end + 1]

    return json.loads(clean)


class MathloreForgeWorkflow:
    """Wrapper to initialize DBOS and execute forge cycles."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._init_dbos()

    def _init_dbos(self) -> None:
        dbos_cfg: DBOSConfig = {
            "name": "mathlore-forge",
            "system_database_url": self.config.dbos_system_database_url,
        }
        try:
            DBOS(config=dbos_cfg)
            DBOS.launch()
        except Exception:
            pass

    def run_cycle(self, options: WorkflowOptions) -> WorkflowResult:
        """Executes the workflow durably."""
        raw_res = mathlore_forge_workflow(self.config.model_dump(), options.model_dump())
        return WorkflowResult.model_validate(raw_res)

    def shutdown(self) -> None:
        try:
            DBOS.destroy()
        except Exception:
            pass


# Backwards compatibility alias
MathloreCycleWorkflow = MathloreForgeWorkflow
