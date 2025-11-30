"""Planner agent for task planning."""

from pathlib import Path

from .base import BaseAgent


class PlannerAgent(BaseAgent):
    """Agent for generating read-only scripts to gather planning information."""

    def __init__(self):
        """Initialize the Planner Agent."""
        super().__init__()
        self.system_prompt = """You are a PowerShell script generator that creates READ-ONLY scripts to gather information needed to plan filesystem tasks.

Your job is to generate a script that collects MINIMAL data needed to plan the task - not to execute the task itself.

CRITICAL RULES:
1. Generate ONLY read-only PowerShell commands (Get-ChildItem, Get-Item, Measure-Object, etc.)
2. NEVER use write operations (Move-Item, Copy-Item, Remove-Item, New-Item, etc.)
3. All output must be in JSON format using ConvertTo-Json
4. Stay within the specified scope/sandbox directory
5. Output ONLY what the Executor agent will need - be extremely selective

EFFICIENCY EXAMPLES:
- Task: "Organize files by type" → Output extension counts, not full file listings
- Task: "Move PDFs to Documents" → Output only PDF names and current locations
- Task: "Delete old files" → Output only files matching the criteria (e.g., older than X days)
- Task: "Find duplicates" → Output file names and sizes/hashes, not full metadata

OUTPUT MINIMAL FIELDS:
- Only include Name, FullName, Length, Extension, LastWriteTime as needed
- Use Select-Object to limit fields
- Use Where-Object to filter before outputting
- Limit results appropriately

OUTPUT FORMAT:
Return ONLY a JSON object with this structure:
{"script": "<PowerShell script here>"}

Do not include any explanation, markdown, or additional text - just the JSON."""

    async def call(self, task: str, sandbox: Path) -> dict:
        """
        Generate a read-only script to gather information for planning.

        Args:
            task: User's task description
            sandbox: Sandbox path

        Returns:
            Dictionary with 'script' field
        """
        user_message = f"""User's task: {task}

Sandbox scope: {sandbox}

Generate a PowerShell script that:
1. Gathers MINIMAL information needed to plan this task
2. Uses ONLY read operations
3. Outputs results as JSON using ConvertTo-Json
4. Only accesses files/folders within: {sandbox}
5. Is highly selective - output only what the Executor will need

Think: What is the minimum data needed to execute this task?

Remember: Return ONLY the JSON with the script field, no explanations."""

        response_text = await self._call_api(self.system_prompt, user_message)
        result = self._parse_json_response(response_text)

        # Validate response has required field
        if "script" not in result:
            raise ValueError("Agent response missing 'script' field")

        return result
