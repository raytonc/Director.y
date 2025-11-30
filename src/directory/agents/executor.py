"""Executor agent for task execution."""

from pathlib import Path

from .base import BaseAgent


class ExecutorAgent(BaseAgent):
    """Agent for generating write scripts to execute tasks."""

    def __init__(self):
        """Initialize the Executor Agent."""
        super().__init__()
        self.system_prompt = """You are a PowerShell script generator that creates SAFE write scripts to execute filesystem tasks.

CRITICAL SAFETY RULES:
1. ALWAYS use try/catch blocks for error handling
2. For deletions, use Move-Item to Recycle Bin ($env:TEMP), NOT Remove-Item -Force
3. Validate paths exist before operations (Test-Path)
4. Output structured results as JSON using ConvertTo-Json
5. Never use dangerous cmdlets (Invoke-Expression, Start-Process, etc.)
6. Stay within the specified sandbox directory

SAFE OPERATIONS YOU CAN USE:
- Move-Item (for moving files/folders)
- Copy-Item (for copying)
- New-Item (for creating files/folders)
- Rename-Item (for renaming)
- Remove-Item (ONLY with Recycle Bin safety - move to $env:TEMP first)

OUTPUT STRUCTURE:
Return structured results showing what was done:
- For each operation: success/failure status
- Count of items processed
- Any errors encountered
- Use JSON format: {"moved": 12, "errors": []}

NOT verbose logs like "Moving file X..."

EXAMPLE GOOD SCRIPT:
```powershell
$results = @{moved=0; errors=@()}
try {
    $files = Get-ChildItem -Path "C:\\Users\\..." -Filter "*.pdf"
    foreach ($file in $files) {
        try {
            Move-Item -Path $file.FullName -Destination "..." -ErrorAction Stop
            $results.moved++
        } catch {
            $results.errors += $_.Exception.Message
        }
    }
} catch {
    $results.errors += $_.Exception.Message
}
$results | ConvertTo-Json
```

OUTPUT FORMAT:
Return ONLY a JSON object with this structure:
{
  "explanation": "<specific description of what will change, e.g., 'Move 12 PDFs to Documents'>",
  "script": "<PowerShell script here>"
}

Do not include any markdown, explanations outside the JSON, or additional text - just the JSON."""

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
        user_message = f"""User's task: {task}

Sandbox scope: {sandbox}

Planning data (from previous script):
{planning_data}

Generate a PowerShell script that:
1. Safely executes the user's task based on the planning data
2. Uses try/catch for ALL operations
3. Uses Recycle Bin safety for deletions (move to $env:TEMP first)
4. Outputs structured JSON results (counts, errors)
5. Only operates within the sandbox: {sandbox}

Also provide a specific explanation of what will change (e.g., "Move 12 PDFs to Documents", not "Organize files").

Remember: Return ONLY the JSON with explanation and script fields, no other text."""

        response_text = await self._call_api(self.system_prompt, user_message)
        result = self._parse_json_response(response_text)

        # Validate response has required fields
        if "explanation" not in result:
            raise ValueError("Agent response missing 'explanation' field")
        if "script" not in result:
            raise ValueError("Agent response missing 'script' field")

        return result
