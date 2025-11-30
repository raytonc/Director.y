"""Executor agent for task execution."""

from pathlib import Path

from ..text import load_text
from .base import BaseAgent


class ExecutorAgent(BaseAgent):
    """Agent for generating write scripts to execute tasks."""

    def __init__(self):
        """Initialize the Executor Agent."""
        super().__init__()
        self.system_prompt = load_text("executor_prompt")

    async def call(
        self,
        task: str,
        planning_data: str,
        sandbox: Path
    ) -> dict:
        """
        Generate a write script to execute the task.

        Args:
            task: User's task description
            planning_data: JSON output from planning script
            sandbox: Sandbox path

        Returns:
            Dictionary with 'explanation' and 'script' fields
        """
        user_message = f"User's task: {task}, Sandbox scope: {sandbox}, Planning data: {planning_data}"

        response_text = await self._call_api(self.system_prompt, user_message)
        result = self._parse_json_response(response_text)

        # Validate response has required fields
        if "explanation" not in result:
            raise ValueError("Agent response missing 'explanation' field")
        if "script" not in result:
            raise ValueError("Agent response missing 'script' field")

        return result
