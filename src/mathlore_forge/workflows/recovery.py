"""Workflow recovery and resumption handlers using DBOS."""

from typing import Any
from dbos import DBOS
from mathlore_forge.config import AppConfig


class WorkflowRecoveryManager:
    """Manages workflow resumption and failure recovery."""

    def __init__(self, config: AppConfig):
        self.config = config

    def resume_workflow(self, workflow_id: str) -> Any:
        """Resumes an interrupted or paused DBOS workflow."""
        return DBOS.retrieve_workflow(workflow_id).get_result()
