"""Summary agent for result summarization."""

from .base import BaseAgent


class SummaryAgent(BaseAgent):
    """Agent for summarizing script outputs in user-friendly format."""

    def __init__(self):
        """Initialize the Summary Agent."""
        super().__init__()
        self.system_prompt = """You are a script output summarizer that converts JSON results into clear, user-friendly summaries.

Your goal is to provide concise, informative summaries that answer the user's original question or confirm what action was taken.

FORMATTING GUIDELINES:

For QUERY mode (answering questions):
- Lead with the direct answer that best addresses the user's query
- Include key numbers and statistics
- Be concise
- Be conversational and helpful

For TASK mode (confirming actions):
- Confirm what was actually done
- Mention any errors encountered
- Use past tense
- Example: "Moved 47 files into 5 folders (Images, Documents, Archives, Videos, Other)."
- If errors: "Moved 45 of 47 files. 2 files couldn't be moved due to permission errors."

KEY PRINCIPLES:
- Be specific and factual
- Use natural language, not technical jargon
- Highlight important information
- Keep it short - users want quick answers
- If the output is an error, explain it clearly
- If you don't see any script output, that means the output was empty

OUTPUT FORMAT:
Return ONLY a JSON object with this structure:
{"summary": "<user-friendly summary here>"}
"""

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
        user_message = f"""Mode: {mode}
Original request: {request}

Script output (JSON):
{output}

Create a user-friendly summary:
- If query mode: Answer the user's question directly and concisely
- If task mode: Confirm what was done and mention any errors (1-2 sentences)

Return ONLY the JSON with the summary field, no other text."""

        response_text = await self._call_api(self.system_prompt, user_message)
        result = self._parse_json_response(response_text)

        # Validate response has required field
        if "summary" not in result:
            raise ValueError("Agent response missing 'summary' field")

        return result
