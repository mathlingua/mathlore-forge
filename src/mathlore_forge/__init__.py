"""Mathlore Forge: Durable, self-improving AI forge system for Mathlore."""

from mathlore_forge.agents.mathlingua_agent import (
    DEFAULT_MATHLINGUA_SYSTEM_INSTRUCTIONS,
    MathlinguaAgent,
    create_mathlingua_agent,
    create_mathlingua_subagent_config,
)
from mathlore_forge.config import MathloreConfig, load_config
from mathlore_forge.mlg.client import CheckReport, Diagnostic, MlgClient
from mathlore_forge.tools.mathlingua_tools import MathlinguaToolkit

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_MATHLINGUA_SYSTEM_INSTRUCTIONS",
    "CheckReport",
    "Diagnostic",
    "MathlinguaAgent",
    "MathlinguaToolkit",
    "MathloreConfig",
    "MlgClient",
    "create_mathlingua_agent",
    "create_mathlingua_subagent_config",
    "load_config",
]
