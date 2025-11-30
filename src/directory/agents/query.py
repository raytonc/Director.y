"""Query agent for read-only operations."""

from pathlib import Path

from ..text import load_text
from .base import BaseAgent


class QueryAgent(BaseAgent):
    """Agent for generating read-only PowerShell scripts to answer questions."""

    def __init__(self):
        """Initialize the Query Agent."""
        super().__init__()
        self.system_prompt = load_text("query_prompt")

    async def call(self, question: str, sandbox: Path) -> dict:
        """
        Generate a read-only script to answer the user's question.

        Args:
            question: User's question
            sandbox: Sandbox path

        Returns:
            Dictionary with 'script' field
        """
        user_message = f"User\'s question: {question}, Sandbox scope: {sandbox}"
        response_text = await self._call_api(self.system_prompt, user_message)
        result = self._parse_json_response(response_text)

        # Validate response has required field
        if "script" not in result:
            raise ValueError("Agent response missing 'script' field")

        return result
