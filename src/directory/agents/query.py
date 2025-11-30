"""Query agent for read-only operations."""

from pathlib import Path

from .base import BaseAgent


class QueryAgent(BaseAgent):
    """Agent for generating read-only PowerShell scripts to answer questions."""

    def __init__(self):
        """Initialize the Query Agent."""
        super().__init__()
        self.system_prompt = """You are a PowerShell script generator that creates READ-ONLY scripts to answer user questions about their filesystem.

CRITICAL RULES:
1. Generate ONLY read-only PowerShell commands (Get-ChildItem, Get-Item, Measure-Object, etc.)
2. NEVER use write operations (Move-Item, Copy-Item, Remove-Item, New-Item, etc.)
3. All output must be in JSON format using ConvertTo-Json
4. Stay within the specified scope/sandbox directory
5. Be EFFICIENT - output only the minimum data needed to answer the question

EFFICIENCY GUIDELINES:
- Prefer aggregates over full listings (use Measure-Object, Group-Object)
- Use Select-Object -First N to limit results (default: 50 items max)
- Output only relevant fields, not all properties
- Use Where-Object to filter before outputting

SAFE CMDLETS YOU CAN USE:
- Get-ChildItem, Get-Item, Test-Path, Resolve-Path
- Select-Object, Where-Object, Sort-Object, Group-Object
- Measure-Object, ForEach-Object
- ConvertTo-Json, Write-Output

OUTPUT FORMAT:
Return ONLY a JSON object with this structure:
{"script": "<PowerShell script here>"}

Do not include any explanation, markdown, or additional text - just the JSON."""

    async def call(self, question: str, sandbox: Path) -> dict:
        """
        Generate a read-only script to answer the user's question.

        Args:
            question: User's question
            sandbox: Sandbox path

        Returns:
            Dictionary with 'script' field
        """
        user_message = f"""User's question: {question}

Sandbox scope: {sandbox}

Generate a PowerShell script that:
1. Answers the user's question using ONLY read operations
2. Outputs results as JSON using ConvertTo-Json
3. Only accesses files/folders within the sandbox path: {sandbox}
4. Is efficient and limits output appropriately

Remember: Return ONLY the JSON with the script field, no explanations."""

        response_text = await self._call_api(self.system_prompt, user_message)
        result = self._parse_json_response(response_text)

        # Validate response has required field
        if "script" not in result:
            raise ValueError("Agent response missing 'script' field")

        return result
