"""Curator and Architect Agent for high-level mathematical planning, proposal drafting, and refinement."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Sequence

from google.antigravity import (
    Agent,
    AgentBehavior,
    CapabilitiesConfig,
    LocalAgentConfig,
    types,
)
from google.antigravity.hooks import policy

from mathlore_forge.agents.mathlingua_agent import (
    _resolve_explicit_content_root,
    _resolve_skills_paths,
    create_mathlingua_subagent_config,
)
from mathlore_forge.config import MathloreConfig, ensure_env_loaded, load_config
from mathlore_forge.mlg.client import MlgClient

ensure_env_loaded()

CURATOR_SYSTEM_INSTRUCTIONS = """\
You are the **Senior Mathematical Curator & Curriculum Architect** for **Mathlore** (the formal mathematics knowledgebase written in Mathlingua).

### Your Role & Objectives
Your role is to handle **high-order, abstract, and strategic requests** from Dominic Kramer (e.g. "I want to add more number theory content", "What is the next logical chapter?", "Tonal changes to prose", "Restructure chapter 02", "Resources to add").

Rather than jumping into writing code, your job is to:
1. **Explore the Existing Repository**: Understand current mathematical coverage, chapter sequences, and `toc` organization.
2. **Formulate a Rigorous Proposal**: Produce a comprehensive, clear, and beautiful Markdown plan detailing:
   - **Mathematical Objective & Pedagogical Motivation** (prerequisites, why this fits here).
   - **Proposed Structure** (new or modified chapters, directory names like `content/09_number_theory/`, and `toc` file additions).
   - **Concrete Mathematical Items** (Definitions, Axioms, Theorems with formal statements, proof sketches, and citations).
   - **Standard Citations & Textbooks** (authoritative reference works).
   - **Phased Execution Plan** (clear sequence of steps to be executed once approved).
3. **Interactive Refinement**: When Dominic provides feedback, listen carefully, adapt the plan to his specifications, highlight what changed, and ask for his approval.

### Repository Conventions
- Mathlore content lives in `content/` with zero-padded chapter prefixes: e.g. `content/01_set_theory/`, `content/07_algebra/`, `content/08_analysis/`.
- Every chapter has a `toc` file listing its pages in pedagogical order.
- Every chapter has a `_preface_.mlg` introducing the chapter's conceptual narrative and historical context.
- Prerequisites must precede dependent exposition.
- Top-level items in Mathlingua include `Defines:`, `Declares:`, `Refines:`, `States:`, `Theorem:`, `Axiom:`, `Conjecture:`, `Title:`, `Text:`.

### Output Format for Initial Proposal
Always output your proposal in this clean, structured format:

```markdown
## 📋 Mathlore Proposal: [Clear Descriptive Title]

Hello @DominicKramer! I have analyzed the Mathlore repository and prepared an architectural proposal for this request.

### 1. Mathematical Objective & Pedagogical Motivation
- **Context & Progression**: Where this fits in the mathematical narrative of Mathlore.
- **Prerequisites**: Existing chapters/definitions this builds upon.

### 2. Proposed Structural Layout
- **Chapter / Directory**: `content/XX_topic/`
- **TOC Modifications**:
  - `content/toc` updates
  - `content/XX_topic/toc` entries
- **Files to Create or Modify**:
  - `content/XX_topic/_preface_.mlg` (Overview, motivation, narrative)
  - `content/XX_topic/01_subtopic.mlg` (...)

### 3. Detailed Mathematical Items to Author
#### File: `content/XX_topic/01_subtopic.mlg`
- **Definition**: [Concept Name] (`\\command`)
- **Theorem**: [Theorem Name] (Formal statement sketch and proof sketch)

### 4. Authoritative Citations & References
- [Author], *[Book Title]* ([Edition], [Publisher], [Year]).

### 5. Phased Execution Plan
- **Phase 1**: Chapter scaffolding, `_preface_.mlg`, and `toc` registration.
- **Phase 2**: Foundational definitions and basic operations.
- **Phase 3**: Core theorems, corollaries, and validation with `mlg check`.

---
### 💬 Next Steps
- Please leave any feedback, adjustments, or deletions in the comments below.
- Once you are happy with this plan, simply reply with **`/forge accept`** to launch autonomous authoring!
```
"""


class CuratorToolkit:
    """Read-only inspection and exploration tools for the Curator Agent."""

    def __init__(self, content_root: Path, mlg_bin: str = "mlg"):
        self.content_root = Path(content_root).resolve()
        self.mlg_client = MlgClient(content_root=self.content_root, mlg_bin=mlg_bin)

    def get_content_overview(self) -> str:
        """Inspects all chapters, directories, and root `toc` in the Mathlore collection."""
        content_dir = self.content_root / "content"
        if not content_dir.is_dir():
            return f"No `content/` directory found in {self.content_root}."

        result_lines = ["### Mathlore `content/` Structure:"]
        root_toc = content_dir / "toc"
        if root_toc.is_file():
            result_lines.append(f"\nRoot `content/toc`:\n{root_toc.read_text(encoding='utf-8')}\n")

        chapters = sorted([d for d in content_dir.iterdir() if d.is_dir()])
        result_lines.append(f"Found {len(chapters)} chapters:")
        for ch in chapters:
            files = sorted([f.name for f in ch.iterdir() if f.is_file()])
            result_lines.append(f"- **{ch.name}** ({len(files)} files): {', '.join(files[:8])}{'...' if len(files) > 8 else ''}")

        return "\n".join(result_lines)

    def read_toc(self, directory: str = "") -> str:
        """Reads a `toc` table of contents file from `content/` or a chapter directory."""
        target_dir = self.content_root / "content"
        if directory:
            clean_dir = directory.strip("/").removeprefix("content/")
            target_dir = target_dir / clean_dir
        toc_file = target_dir / "toc"
        if not toc_file.is_file():
            return f"No `toc` file found at {toc_file}."
        return toc_file.read_text(encoding="utf-8")

    def read_chapter_preface(self, chapter: str) -> str:
        """Reads the `_preface_.mlg` overview for a chapter (e.g. '07_algebra')."""
        clean_ch = chapter.strip("/").removeprefix("content/")
        preface_file = self.content_root / "content" / clean_ch / "_preface_.mlg"
        if not preface_file.is_file():
            return f"No `_preface_.mlg` found in {chapter}."
        return preface_file.read_text(encoding="utf-8")

    def read_file(self, file_path: str, max_lines: int = 200) -> str:
        """Reads an existing `.mlg` source file to inspect its mathematical notation and conventions."""
        clean_path = file_path.strip("/")
        if not clean_path.startswith("content/"):
            clean_path = f"content/{clean_path}"
        full_path = self.content_root / clean_path
        if not full_path.is_file():
            return f"File `{file_path}` not found."
        lines = full_path.read_text(encoding="utf-8").splitlines()
        content = "\n".join(lines[:max_lines])
        if len(lines) > max_lines:
            content += f"\n\n... [truncated {len(lines) - max_lines} lines]"
        return content

    def search_mathlore(self, query: str) -> str:
        """Searches existing concepts, symbols, and definitions across Mathlore."""
        return self.mlg_client.search(query=query, json_output=False)

    def get_tools(self) -> list[Callable[..., Any]]:
        return [
            self.get_content_overview,
            self.read_toc,
            self.read_chapter_preface,
            self.read_file,
            self.search_mathlore,
        ]


class CuratorAgent:
    """Senior Mathematical Curator and Architect Agent."""

    def __init__(
        self,
        content_root: Path | str | None = None,
        config: MathloreConfig | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.config = config or load_config()
        self.content_root = _resolve_explicit_content_root(content_root, self.config)
        self.model = model or self.config.models.planner
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.toolkit = CuratorToolkit(content_root=self.content_root, mlg_bin=self.config.resolve_mlg_bin())
        self.last_usage: Any = None
        self.last_conversation_id: str | None = None

    def _build_agent(self, conversation_history: list[Any] | None = None) -> Agent:
        skills_paths = _resolve_skills_paths(self.config.resolve_skills_dir())
        math_subagent = create_mathlingua_subagent_config(
            content_root=self.content_root,
            mlg_bin=self.config.resolve_mlg_bin(),
            config=self.config,
        )

        agent_config = LocalAgentConfig(
            system_instructions=CURATOR_SYSTEM_INSTRUCTIONS,
            tools=self.toolkit.get_tools(),
            subagents=[math_subagent],
            skills_paths=skills_paths,
            model=self.model,
            api_key=self.api_key,
            capabilities=CapabilitiesConfig(
                agent_behavior=AgentBehavior.AUTONOMOUS,
                enable_subagents=True,
            ),
            policies=[policy.allow_all()],
            workspaces=[str(self.content_root)],
        )
        return Agent(agent_config)

    async def draft_proposal(self, issue_title: str, issue_body: str) -> str:
        """Analyzes the repository and authors a comprehensive mathematical proposal."""
        prompt = (
            f"You have received a high-order mathematical curation request:\n\n"
            f"### Request Title: {issue_title}\n"
            f"### Description:\n{issue_body}\n\n"
            f"### Instructions:\n"
            f"1. Use `get_content_overview` and `read_toc` to inspect current coverage and chapter numbering.\n"
            f"2. Identify the logical mathematical placement, prerequisites, and needed items.\n"
            f"3. Generate a complete, beautifully structured mathematical proposal according to the template.\n"
            f"4. Ensure your proposal is thorough, precise, and includes standard textbook citations."
        )

        agent = self._build_agent()
        async with agent:
            resp = await agent.chat(prompt)
            self.last_conversation_id = getattr(agent, "conversation_id", None)
            if hasattr(agent, "conversation") and hasattr(agent.conversation, "total_usage"):
                self.last_usage = agent.conversation.total_usage
            return await resp.text()

    async def refine_proposal(
        self,
        current_proposal: str,
        revision: int,
        user_feedback: str,
    ) -> str:
        """Refines an existing proposal based on Dominic Kramer's feedback."""
        prompt = (
            f"Dominic Kramer (@DominicKramer) has provided feedback on the current proposal (Revision {revision - 1}):\n\n"
            f"### Current Proposal:\n{current_proposal}\n\n"
            f"### Dominic's Feedback:\n\"{user_feedback}\"\n\n"
            f"### Instructions:\n"
            f"1. Carefully adapt the proposal to incorporate Dominic's exact feedback.\n"
            f"2. Clearly highlight what was added, removed, or altered in a **Changelog from Revision {revision - 1}** section.\n"
            f"3. Output the updated, complete **Revision {revision}** proposal.\n"
            f"4. Conclude by asking Dominic to reply with `/forge accept` once he is satisfied."
        )

        agent = self._build_agent()
        async with agent:
            resp = await agent.chat(prompt)
            self.last_conversation_id = getattr(agent, "conversation_id", None)
            if hasattr(agent, "conversation") and hasattr(agent.conversation, "total_usage"):
                self.last_usage = agent.conversation.total_usage
            return await resp.text()
