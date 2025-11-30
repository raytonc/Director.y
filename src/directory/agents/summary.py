"""Summary agent for result summarization."""

from ..text import load_text
from .base import BaseAgent


class SummaryAgent(BaseAgent):
    """Agent for summarizing script outputs in user-friendly format."""

    def __init__(self):
        """Initialize the Summary Agent."""
        super().__init__()
        self.system_prompt = load_text("summary_prompt")

    async def call(
        self,
        mode: str,
        request: str,
        output: str
    ) -> dict:
        """
        Summarize script output for the user.

        Args:
            mode: 'query' or 'task'
            request: Original user request
            output: Script output (JSON)

        Returns:
            Dictionary with 'summary' field
        """
        user_message = f"Mode: {mode}, Original request: {request}, Script output: {output}"

        response_text = await self._call_api(self.system_prompt, user_message)
        result = self._parse_json_response(response_text)

        # Validate response has required field
        if "summary" not in result:
            raise ValueError("Agent response missing 'summary' field")

        return result
