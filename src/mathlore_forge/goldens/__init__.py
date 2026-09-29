"""Mathlingua Agent Golden Testing Framework."""

from mathlore_forge.goldens.author import scaffold_new_test_case
from mathlore_forge.goldens.evaluator import AssertionResult, EvaluationReport, Evaluator
from mathlore_forge.goldens.loader import discover_test_cases, load_test_case_from_path
from mathlore_forge.goldens.models import (
    CompilerExpectation,
    Expectations,
    FileExpectation,
    GoldenTestCase,
    ScaffoldConfig,
    SubagentExpectation,
    ToolCallExpectation,
    TrajectoryExpectations,
)
from mathlore_forge.goldens.runner import (
    AgentAdapter,
    CustomCallableAdapter,
    MathloreForgeAgentAdapter,
    MockAgentAdapter,
    SimulatedAgentAdapter,
    TestRunner,
)
from mathlore_forge.goldens.sandbox import FileDiffSummary, Sandbox
from mathlore_forge.goldens.session import Session, SessionManager, SessionMeta
from mathlore_forge.goldens.trajectory import (
    SubagentCallRecord,
    ToolCallRecord,
    Trajectory,
    TurnRecord,
)

__version__ = "0.1.0"

__all__ = [
    "AgentAdapter",
    "AssertionResult",
    "CompilerExpectation",
    "CustomCallableAdapter",
    "EvaluationReport",
    "Evaluator",
    "Expectations",
    "FileDiffSummary",
    "FileExpectation",
    "GoldenTestCase",
    "MathloreForgeAgentAdapter",
    "MockAgentAdapter",
    "SimulatedAgentAdapter",
    "Sandbox",
    "ScaffoldConfig",
    "Session",
    "SessionManager",
    "SessionMeta",
    "SubagentCallRecord",
    "SubagentExpectation",
    "TestRunner",
    "ToolCallExpectation",
    "ToolCallRecord",
    "Trajectory",
    "TrajectoryExpectations",
    "TurnRecord",
    "discover_test_cases",
    "load_test_case_from_path",
    "scaffold_new_test_case",
]
