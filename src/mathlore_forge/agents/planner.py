"""Planner agents for high-level curriculum design and detailed Mathlingua specifications."""

from pathlib import Path
from typing import Any
from google.antigravity import Agent
from pydantic import BaseModel, Field

from mathlore_forge.agents.base import create_agent_config
from mathlore_forge.db.schema import PhaseType
from mathlore_forge.db.store import MathloreStore
from mathlore_forge.flywheel.learner import FeedbackLearner
from mathlore_forge.mlg.client import MlgClient


class HighLevelPlan(BaseModel):
    title: str = Field(description="Title of this focused math expansion cycle")
    rationale: str = Field(description="Why this flows directly from existing Mathlore content without gaps")
    target_chapter: str = Field(description="Chapter directory or file path in Mathlore")
    concepts_to_add: list[str] = Field(description="Specific concepts, definitions, or theorems to introduce")
    prerequisites: list[str] = Field(description="Existing Mathlore concepts this builds upon")
    reputable_sources: list[str] = Field(description="Reputable mathematical textbooks or papers to cite")


class DetailedPlanItem(BaseModel):
    id: str = Field(description="Unique identifier for this TODO item, e.g. 'def_transitive_relation'")
    section_path: str = Field(description="Path to target .mlg file under content/, e.g. 'content/02_relations.mlg'")
    title: str = Field(description="Human readable title of the item")
    kind: str = Field(description="Mathlingua top-level group kind: 'Defines', 'States', 'Theorem', 'Axiom', etc.")
    purpose: str = Field(description="Mathematical purpose of this construct")
    what_to_cover: str = Field(description="Detailed formulation requirements and components to cover")
    prerequisite_symbols: list[str] = Field(description="Mathlingua commands/symbols required, e.g. ['\\\\set', '\\\\relation']")
    citations: list[dict[str, Any]] = Field(description="List of reputable citations with author, title, and page/url")


class DetailedPlan(BaseModel):
    summary: str = Field(description="Summary of the detailed plan")
    items: list[DetailedPlanItem] = Field(description="Ordered list of items to author serially")


def new_high_level_planner_agent(
    mlg_client: MlgClient,
    store: MathloreStore,
    learner: FeedbackLearner,
    model: str | None = None,
    skills_dir: Path | str = "./skills",
) -> Agent:
    """Creates an Antigravity agent specializing in high-level curriculum planning for Mathlore."""

    def query_mathlore_structure() -> str:
        """Inspects the current table of contents and structural layout of Mathlore."""
        structure = mlg_client.structure()
        summary = [f"Mathlore Collection: {structure.title}\nDirectories:"]
        for d in structure.directories:
            summary.append(f"  - {d.path}: {d.title or '<untitled>'}")
        summary.append("\nFiles:")
        for f in structure.files:
            cmds = f" | commands: {', '.join(f.all_commands)}" if f.all_commands else ""
            summary.append(f"  - {f.path}: {f.title or '<untitled>'} ({len(f.items)} items{cmds})")
        return "\n".join(summary)

    def search_mathlore(query: str) -> str:
        """Searches existing Mathlore items by command key, heading, or keyword."""
        report = mlg_client.search(query)
        if not report.matches:
            return f"No items found matching '{query}'."
        out = [f"Found {report.total_matches} item(s) for '{query}':"]
        for m in report.matches[:8]:
            out.append(f"  - [{m.kind}] {m.heading or '<no heading>'} (file: {m.file_path}, keys: {m.definition_keys})")
        return "\n".join(out)

    learned_context = learner.get_prompt_context(PhaseType.HIGH_LEVEL_PLAN)

    system_instructions = (
        "You are an expert mathematical curriculum architect and textbook author specializing in Mathlore.\n"
        "Mathlore is a grand archive of mathematical knowledge written in Mathlingua, structured strictly like "
        "a rigorous textbook flowing continuously from logic and set theory without any gaps.\n\n"
        "Your role is to propose a narrow, focused high-level plan for the next batch of definitions and theorems.\n"
        "Each iteration must:\n"
        "1. Flow directly from existing content with ZERO conceptual gaps.\n"
        "2. Be narrow and focused in scope (e.g. 1 to 4 related items per cycle).\n"
        "3. Base every item on reputable mathematical textbooks (e.g. Bourbaki, Enderton, Rudin, Munkres, Halmos).\n"
        "4. Output a JSON object strictly conforming to the HighLevelPlan schema:\n"
        "{\n"
        '  "title": "...",\n'
        '  "rationale": "...",\n'
        '  "target_chapter": "...",\n'
        '  "concepts_to_add": ["..."],\n'
        '  "prerequisites": ["..."],\n'
        '  "reputable_sources": ["..."]\n'
        "}\n\n"
        f"{learned_context}"
    )

    config = create_agent_config(
        system_instructions=system_instructions,
        skills_dirs=[Path(skills_dir)],
        tools=[query_mathlore_structure, search_mathlore],
        model=model,
    )
    return Agent(config)


def new_detailed_planner_agent(
    mlg_client: MlgClient,
    store: MathloreStore,
    learner: FeedbackLearner,
    model: str | None = None,
    skills_dir: Path | str = "./skills",
) -> Agent:
    """Creates an Antigravity agent specializing in creating concrete serial TODO items."""

    def search_mathlore(query: str) -> str:
        """Searches existing Mathlore items by command key, heading, or keyword."""
        report = mlg_client.search(query)
        if not report.matches:
            return f"No items found matching '{query}'."
        out = [f"Found {report.total_matches} item(s) for '{query}':"]
        for m in report.matches[:8]:
            out.append(f"  - [{m.kind}] {m.heading or '<no heading>'} (file: {m.file_path}, keys: {m.definition_keys})")
        return "\n".join(out)

    learned_context = learner.get_prompt_context(PhaseType.DETAILED_PLAN)

    system_instructions = (
        "You are an expert Mathlingua specification architect.\n"
        "Your task is to take an approved high-level plan and produce a detailed, serial blueprint of TODO items.\n"
        "The items will be authored SERIALLY by sub-agents to avoid definition collisions.\n"
        "For each item, specify:\n"
        "- unique ID\n"
        "- target file path under content/\n"
        "- title\n"
        "- Mathlingua kind ('Defines', 'States', 'Theorem', 'Axiom', 'Refines')\n"
        "- exact purpose and mathematical formulation components to cover\n"
        "- prerequisite symbols\n"
        "- reputable textbook/paper citations (Author, Title, Year/URL/ISBN)\n\n"
        "Output a JSON object strictly conforming to the DetailedPlan schema:\n"
        "{\n"
        '  "summary": "...",\n'
        '  "items": [\n'
        "    {\n"
        '      "id": "...",\n'
        '      "section_path": "content/...",\n'
        '      "title": "...",\n'
        '      "kind": "...",\n'
        '      "purpose": "...",\n'
        '      "what_to_cover": "...",\n'
        '      "prerequisite_symbols": ["..."],\n'
        '      "citations": [{"author": "...", "title": "...", "source": "..."}]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"{learned_context}"
    )

    config = create_agent_config(
        system_instructions=system_instructions,
        skills_dirs=[Path(skills_dir)],
        tools=[search_mathlore],
        model=model,
    )
    return Agent(config)
