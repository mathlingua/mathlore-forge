"""Mathlingua authoring agent built with the Google Antigravity SDK."""

from __future__ import annotations

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

from mathlore_forge.config import MathloreConfig, load_config
from mathlore_forge.tools.mathlingua_tools import MathlinguaToolkit

DEFAULT_MATHLINGUA_SYSTEM_INSTRUCTIONS = """\
You are an expert Mathlingua authoring agent. Your role is to formulate mathematically rigorous, \
syntactically valid Mathlingua (.mlg) content and update collection files within the repository.

### Key Capabilities & Tools
You have access to specialized authoring tools and the `mlg` compiler tooling:
- `insert_item_after(file_path, after_id, new_item_content)`: Directly inserts a new Mathlingua item after the item with the given ID.
- `read_content_file(file_path)`: Reads the full text of a Mathlingua source file.
- `write_content_file(file_path, content)`: Creates or overwrites a Mathlingua source file.
- `find_item_by_id(item_id, file_path)`: Finds an item by its UUID and displays its lines and content.
- `replace_item_by_id(file_path, item_id, new_item_content)`: Replaces an item with updated content.
- `mlg_check(paths)`: Runs `mlg check` to validate syntax and semantics. Automatically assigns UUIDs to new items and formats them.
- `mlg_structure()`: Inspects the collection layout, page table of contents, and all item IDs.
- `mlg_search(query)`: Searches existing definitions, commands, and notations across the collection.
- `mlg_format()`: Reformats `.mlg` files according to standard print margins.
- `run_mlg(subcommand, args)`: Executes any `mlg` CLI invocation (e.g. check, structure, search, format, version).

### Domain Skills
You are equipped with comprehensive domain skills in your skills directory:
- `mathlore-author-content`: Overall authoring lifecycle, item separation, and routing to specific guidance.
- `mathlingua-structural-language`: Line-oriented document structure, top-level groups (`Declares:`, `Defines:`, `Refines:`, `States:`, `Theorem:`, `Axiom:`, `Conjecture:`, `Title:`, `Text:`, etc.).
- `mathlingua-formulation-language`: Expression syntax, commands (`\\command:with{args}`), infix operators (`\\.operator./`), signatures, types (`is`), tuples, sets, functions.
- `mathlingua-clause-groups`: Logical collections (`allOf`, `anyOf`, `oneOf`), quantifiers (`forAll`, `exists`, `existsUnique`), conditionals (`if`, `then`), proof-like clauses (`have`).
- `mathlingua-support-sections`: Documentation (`Documented:` with `called:`, `written:`, `description:`), specifications (`specifies:`), conditions (`satisfies:`), requirements (`when:`, `Requires:`), capabilities (`Enables:`).
- `mathlore-how-do-i`: Practical recipes for adding structures, properties, operations, theorems, and prose.
- `mathlore-diagnose-content`: Diagnostics playbook for diagnosing and resolving compiler errors.

### Authoring Rules & Best Practices
1. **Omit `Id:` on New Items**:
   - When writing a new top-level item (`Defines:`, `Declares:`, `Refines:`, `Theorem:`, `Text:`, etc.), do NOT include an `Id:` section.
   - Let `mlg check` generate and assign a fresh unique UUID automatically. Never reuse or fabricate a UUID.
2. **Handling Requests to Insert / Update**:
   - When requested to write content (e.g., "write the definition of a group that is ... in file xyz after item with ID abc"):
     a. Locate the target item and inspect nearby definitions using `find_item_by_id` or `read_content_file` to match existing conventions and symbols.
     b. Formulate the precise Mathlingua code according to structural and formulation language rules.
     c. Use `insert_item_after(file_path=xyz, after_id=abc, new_item_content=...)` to insert the new item into the file.
     d. Run `mlg_check([xyz])` to validate syntax and semantics.
     e. If `mlg_check` reports errors, inspect the diagnostics and line numbers, apply fixes with `replace_item_by_id` or `write_content_file`, and re-check until 0 errors are reported.
     f. Run `mlg_format()` to ensure clean formatting.
3. **Citations & Prose**:
   - Provide standard `Documented:` sections with `called:`, `written:`, and `description:`.
   - Where applicable, include citations to standard textbooks or references.
"""


def _resolve_skills_paths(skills_dir: Path | str | list[Path | str] | None) -> list[str]:
    """Resolves skills directory and all subdirectories containing SKILL.md."""
    if skills_dir is None:
        return []

    input_paths: list[Path] = []
    if isinstance(skills_dir, (str, Path)):
        input_paths.append(Path(skills_dir).resolve())
    elif isinstance(skills_dir, (list, tuple)):
        for p in skills_dir:
            input_paths.append(Path(p).resolve())

    resolved_set: set[str] = set()
    for base in input_paths:
        if base.is_dir():
            resolved_set.add(str(base))
            for sub in base.iterdir():
                if sub.is_dir() and (sub / "SKILL.md").is_file():
                    resolved_set.add(str(sub.resolve()))

    return sorted(list(resolved_set))


def _resolve_explicit_content_root(
    content_root: Path | str | None,
    config: MathloreConfig | None,
) -> Path:
    """Resolves the content root strictly without searching the filesystem."""
    if content_root is not None:
        return Path(content_root).resolve()
    if config and config.paths.mathlore_repo:
        return Path(config.paths.mathlore_repo).resolve()
    env_root = os.getenv("MATHLINGUA_CONTENT_ROOT") or os.getenv("MATHLORE_REPO")
    if env_root:
        return Path(env_root).resolve()

    raise ValueError(
        "content_root must be explicitly specified when creating the Mathlingua agent. "
        "The agent does not search the filesystem for the content root. "
        "This ensures isolated temporary test directories (such as in golden tests) "
        "are used strictly without accidental fallback to other locations."
    )


def create_mathlingua_agent(
    content_root: Path | str | None = None,
    skills_dir: Path | str | list[Path | str] | None = None,
    mlg_bin: Path | str | None = None,
    model: str | types.ModelTarget | None = None,
    api_key: str | None = None,
    system_instructions: str | None = None,
    extra_tools: list[Callable[..., Any]] | None = None,
    policies: Sequence[Any] | None = None,
    capabilities: CapabilitiesConfig | None = None,
    workspaces: list[str] | None = None,
    config: MathloreConfig | None = None,
    **kwargs: Any,
) -> Agent:
    """Creates and configures an Antigravity Agent for authoring Mathlingua content.

    Args:
        content_root: Explicit root directory of the Mathlingua collection. Required.
                      The agent never searches the filesystem for a fallback root.
        skills_dir: Directory containing domain skills. Defaults to config or forge `skills/`.
        mlg_bin: Path to the `mlg` compiler binary. Defaults to config or PATH.
        model: Model target to use. Defaults to `gemini-3.8-flash`.
        api_key: Optional Gemini API key. Defaults to `GEMINI_API_KEY` env var.
        system_instructions: Optional custom system instructions. Defaults to Mathlingua author instructions.
        extra_tools: Optional additional tools to equip the agent with.
        policies: Safety policies. Defaults to `[policy.allow_all()]` so authoring tools execute smoothly.
        capabilities: Optional capabilities configuration.
        workspaces: Optional workspace directories.
        config: Optional pre-loaded MathloreConfig.
        **kwargs: Additional parameters passed to LocalAgentConfig.

    Returns:
        A configured Antigravity `Agent` instance.
    """
    resolved_content_root = _resolve_explicit_content_root(content_root, config)

    if config is None:
        config = load_config(
            content_root=resolved_content_root,
            mlg_bin=mlg_bin,
            skills_dir=skills_dir if isinstance(skills_dir, (str, Path)) else None,
            model=model if isinstance(model, str) else None,
        )

    resolved_skills_dir = skills_dir if skills_dir is not None else config.resolve_skills_dir()
    resolved_mlg_bin = str(mlg_bin) if mlg_bin else config.resolve_mlg_bin()
    resolved_model = model or config.models.author
    resolved_api_key = api_key or os.getenv("GEMINI_API_KEY")

    # 1. Initialize toolkit bound strictly to resolved_content_root and mlg_bin
    toolkit = MathlinguaToolkit(content_root=resolved_content_root, mlg_bin=resolved_mlg_bin)
    agent_tools: list[Callable[..., Any]] = toolkit.get_tools()
    if extra_tools:
        agent_tools.extend(extra_tools)

    # 2. Resolve skill paths
    skills_paths = _resolve_skills_paths(resolved_skills_dir)

    # 3. Setup system instructions
    instructions = system_instructions or DEFAULT_MATHLINGUA_SYSTEM_INSTRUCTIONS
    instructions += (
        f"\n\n### Current Configuration\n"
        f"- Content Root: `{resolved_content_root}`\n"
        f"- `mlg` Binary: `{resolved_mlg_bin}`\n"
    )

    # 4. Capabilities & Policies
    if capabilities is None:
        capabilities = CapabilitiesConfig(
            agent_behavior=AgentBehavior.AUTONOMOUS,
            enable_subagents=True,
        )

    if policies is None:
        policies = [policy.allow_all()]

    agent_workspaces = workspaces or [str(resolved_content_root)]

    agent_config = LocalAgentConfig(
        system_instructions=instructions,
        tools=agent_tools,
        skills_paths=skills_paths,
        model=resolved_model,
        api_key=resolved_api_key,
        capabilities=capabilities,
        policies=policies,
        workspaces=agent_workspaces,
        **kwargs,
    )

    return Agent(agent_config)


def create_mathlingua_subagent_config(
    content_root: Path | str | None = None,
    mlg_bin: Path | str | None = None,
    name: str = "mathlingua_author",
    description: str = "Expert agent capable of authoring and updating Mathlingua (.mlg) content and running mlg compiler checks.",
    system_instructions: str | None = None,
    extra_tools: list[Callable[..., Any]] | None = None,
    config: MathloreConfig | None = None,
) -> types.SubagentConfig:
    """Creates a `SubagentConfig` enabling another Antigravity agent to invoke the Mathlingua author.

    Args:
        content_root: Explicit root directory of the Mathlingua collection. Required.
        mlg_bin: Path to the `mlg` compiler binary.
        name: Name of the subagent.
        description: Description of the subagent's role.
        system_instructions: Optional custom system instructions.
        extra_tools: Optional additional tools.
        config: Optional pre-loaded MathloreConfig.

    Returns:
        `types.SubagentConfig` ready to be passed in `subagents=[...]` of a parent agent config.
    """
    resolved_content_root = _resolve_explicit_content_root(content_root, config)

    if config is None:
        config = load_config(content_root=resolved_content_root, mlg_bin=mlg_bin)

    resolved_mlg_bin = str(mlg_bin) if mlg_bin else config.resolve_mlg_bin()

    toolkit = MathlinguaToolkit(content_root=resolved_content_root, mlg_bin=resolved_mlg_bin)
    agent_tools = toolkit.get_tools()
    if extra_tools:
        agent_tools.extend(extra_tools)

    instructions = system_instructions or DEFAULT_MATHLINGUA_SYSTEM_INSTRUCTIONS
    instructions += (
        f"\n\n### Current Configuration\n"
        f"- Content Root: `{resolved_content_root}`\n"
        f"- `mlg` Binary: `{resolved_mlg_bin}`\n"
    )

    return types.SubagentConfig(
        name=name,
        description=description,
        system_instructions=instructions,
        tools=agent_tools,
        capabilities=types.SubagentCapabilities(
            agent_behavior=AgentBehavior.AUTONOMOUS,
        ),
    )


class MathlinguaAgent:
    """High-level wrapper for the Mathlingua authoring agent."""

    def __init__(
        self,
        content_root: Path | str | None = None,
        skills_dir: Path | str | list[Path | str] | None = None,
        mlg_bin: Path | str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        system_instructions: str | None = None,
        extra_tools: list[Callable[..., Any]] | None = None,
        config: MathloreConfig | None = None,
        **kwargs: Any,
    ):
        resolved_content_root = _resolve_explicit_content_root(content_root, config)

        self.config = config or load_config(
            content_root=resolved_content_root,
            mlg_bin=mlg_bin,
            skills_dir=skills_dir if isinstance(skills_dir, (str, Path)) else None,
            model=model,
        )
        self.content_root = resolved_content_root
        self.mlg_bin = str(mlg_bin) if mlg_bin else self.config.resolve_mlg_bin()
        self.toolkit = MathlinguaToolkit(content_root=self.content_root, mlg_bin=self.mlg_bin)
        self.mlg_client = self.toolkit.mlg_client

        self.agent = create_mathlingua_agent(
            content_root=self.content_root,
            skills_dir=skills_dir or self.config.resolve_skills_dir(),
            mlg_bin=self.mlg_bin,
            model=model or self.config.models.author,
            api_key=api_key,
            system_instructions=system_instructions,
            extra_tools=extra_tools,
            config=self.config,
            **kwargs,
        )

    async def __aenter__(self) -> MathlinguaAgent:
        await self.agent.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.agent.__aexit__(exc_type, exc_val, exc_tb)

    async def chat(self, message: str) -> Any:
        """Sends a message to the agent and returns the response."""
        return await self.agent.chat(message)

    async def author(self, prompt: str) -> str:
        """Executes an authoring turn and returns the aggregated text response."""
        response = await self.agent.chat(prompt)
        return await response.text()

    def check(self, paths: list[str] | None = None) -> str:
        """Synchronously checks collection or paths using mlg."""
        return self.toolkit.mlg_check(paths)

    def structure(self) -> str:
        """Synchronously retrieves collection structure."""
        return self.toolkit.mlg_structure()

    def search(self, query: str) -> str:
        """Synchronously searches collection definitions."""
        return self.toolkit.mlg_search(query)

    def format(self) -> str:
        """Synchronously reformats collection source files."""
        return self.toolkit.mlg_format()
