"""Base harness for Google Antigravity SDK agents with OpenTelemetry hooks."""

import logging
from pathlib import Path
from typing import Any, Callable
from rich.console import Console
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import hooks
from mathlore_forge.telemetry.tracer import get_telemetry_manager

logger = logging.getLogger(__name__)
console = Console()


def create_agent_config(
    system_instructions: str,
    skills_dirs: list[Path] | None = None,
    tools: list[Callable[..., Any]] | None = None,
    model: str | None = None,
    agent_behavior: types.AgentBehavior = types.AgentBehavior.AUTONOMOUS,
    thinking_level: types.ThinkingLevel = types.ThinkingLevel.HIGH,
) -> LocalAgentConfig:
    """Builds a LocalAgentConfig configured with telemetry hooks, thinking, and authoring skills."""
    telemetry = get_telemetry_manager()

    @hooks.pre_turn
    async def pre_turn_hook(data: str) -> types.HookResult:
        telemetry.record_event("agent_turn_start", {"prompt_preview": data[:120]})
        return types.HookResult(allow=True)

    @hooks.post_turn
    async def post_turn_hook(data: str) -> None:
        telemetry.record_event("agent_turn_end", {"response_length": len(data)})

    @hooks.pre_tool_call_decide
    async def pre_tool_hook(data: types.ToolCall) -> types.HookResult:
        telemetry.set_activity(telemetry.current_phase, f"Running tool: {data.name}")
        telemetry.record_event("tool_call_start", {"tool_name": data.name})
        args_str = ", ".join(f"{k}={repr(v)[:80]}" for k, v in data.args.items()) if data.args else ""
        console.print(f"[yellow]  ⚙ Executing tool:[/yellow] [bold cyan]{data.name}[/bold cyan]({args_str})")
        return types.HookResult(allow=True)

    @hooks.post_tool_call
    async def post_tool_hook(data: Any) -> None:
        telemetry.record_event("tool_call_end", {"status": "completed"})
        console.print("[dim green]  ✔ Tool finished.[/dim green]")

    resolved_skills = []
    if skills_dirs:
        resolved_skills = [p.resolve() for p in skills_dirs if p.exists() and p.is_dir()]

    capabilities = types.CapabilitiesConfig(
        agent_behavior=agent_behavior,
    )

    model_options = types.GeminiModelOptions(thinking_level=thinking_level)

    return LocalAgentConfig(
        system_instructions=system_instructions,
        skills_dirs=resolved_skills,
        tools=tools or [],
        model=model,
        model_options=model_options,
        capabilities=capabilities,
        hooks=[pre_turn_hook, post_turn_hook, pre_tool_hook, post_tool_hook],
    )


async def run_agent_turn(
    agent: Agent,
    prompt: str,
    span_name: str = "agent_interaction",
    print_output: bool = False,
    show_thoughts: bool = True,
    status_message: str | None = None,
) -> str:
    """Executes a turn with an agent within an OpenTelemetry span, streaming thoughts and status."""
    telemetry = get_telemetry_manager()
    if status_message:
        console.print(f"[bold cyan]⏳ {status_message}...[/bold cyan]")

    with telemetry.span(span_name, {"prompt": prompt[:200]}):
        async with agent:
            response = await agent.chat(prompt)
            output_tokens = []

            async for chunk in response.chunks:
                if isinstance(chunk, types.Thought):
                    if show_thoughts and chunk.text and chunk.text.strip():
                        for line in chunk.text.strip().splitlines():
                            if line.strip():
                                console.print(f"[dim italic magenta]  💭 {line.strip()}[/dim italic magenta]")
                elif isinstance(chunk, types.ToolCall):
                    args_str = ", ".join(f"{k}={repr(v)[:80]}" for k, v in chunk.args.items()) if chunk.args else ""
                    console.print(f"[yellow]  ⚙ Tool call:[/yellow] [bold cyan]{chunk.name}[/bold cyan]({args_str})")
                elif isinstance(chunk, types.Text):
                    output_tokens.append(chunk.text)
                    if print_output:
                        print(chunk.text, end="", flush=True)

            if print_output and output_tokens:
                print()

            full_text = "".join(output_tokens)

            # Record token usage if available
            try:
                usage = agent.conversation.total_usage
                telemetry.record_event(
                    "token_usage",
                    {
                        "prompt_tokens": usage.prompt_token_count,
                        "candidates_tokens": usage.candidates_token_count,
                        "thoughts_tokens": usage.thoughts_token_count,
                        "total_tokens": usage.total_token_count,
                    },
                )
            except Exception:
                pass

            return full_text
