"""Planner agent for task planning."""

from pathlib import Path

from ..text import load_text
from .base import BaseAgent


class PlannerAgent(BaseAgent):
    """Agent for generating read-only scripts to gather planning information."""

    def __init__(self):
        """Initialize the Planner Agent."""
        super().__init__()
        self.system_prompt = load_text("planner_prompt")

    async def call(self, task: str, sandbox: Path) -> dict:
        """
        Generate a read-only script to gather information for planning.

        Args:
            task: User's task description
            sandbox: Sandbox path

        Returns:
            Dictionary with 'script' field
        """
        user_message = f"User's task: {task}, Sandbox scope: {sandbox}"

        response_text = await self._call_api(self.system_prompt, user_message)
        result = self._parse_json_response(response_text)

        # Validate response has required field
        if "script" not in result:
            raise ValueError("Agent response missing 'script' field")

        return result
