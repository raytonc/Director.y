"""Script execution and validation."""

import re
import subprocess
from pathlib import Path
from typing import Literal

from .models import ExecutionResult, ScriptClassification


# Safe read-only cmdlets
READ_SAFE_CMDLETS = {
    "Get-ChildItem",
    "Get-Item",
    "Test-Path",
    "Resolve-Path",
    "Select-Object",
    "Where-Object",
    "Sort-Object",
    "Group-Object",
    "Measure-Object",
    "ForEach-Object",
    "ConvertTo-Json",
    "Write-Output",
}

# Write operation cmdlets
WRITE_CMDLETS = {
    "Move-Item",
    "Copy-Item",
    "Remove-Item",
    "New-Item",
    "Rename-Item",
}

# Dangerous patterns
DANGEROUS_PATTERNS = [
    "Invoke-",
    "Start-Process",
    "HKLM:",
    "HKCU:",
]

# Output size limit (100KB)
MAX_OUTPUT_SIZE = 100_000


def extract_paths(script: str) -> list[str]:
    """
    Extract file paths from a PowerShell script.

    Args:
        script: PowerShell script content

    Returns:
        List of path strings found in the script
    """
    paths = []

    # Pattern 1: Paths in quotes (single or double)
    # Matches strings like "C:\Users\..." or 'C:\Users\...'
    quoted_paths = re.findall(r'["\']([A-Za-z]:[\\\/][^"\']*)["\']', script)
    paths.extend(quoted_paths)

    # Pattern 2: Common path parameters
    # -Path, -LiteralPath, -Destination, -FilePath, etc.
    path_params = re.findall(
        r'-(?:Path|LiteralPath|Destination|FilePath|Source|Target)\s+["\']?([A-Za-z]:[\\\/][^\s"\']*)["\']?',
        script,
        re.IGNORECASE
    )
    paths.extend(path_params)

    # Pattern 3: Variable assignments with paths
    # $var = "C:\Users\..."
    var_paths = re.findall(r'\$\w+\s*=\s*["\']([A-Za-z]:[\\\/][^"\']*)["\']', script)
    paths.extend(var_paths)

    # Pattern 4: UNC paths (\\server\share)
    unc_paths = re.findall(r'["\']?(\\\\[^\s"\']+)["\']?', script)
    paths.extend(unc_paths)

    # Pattern 5: Relative paths starting with .\ or ../
    relative_paths = re.findall(r'["\']?(\.{1,2}[\\\/][^\s"\']*)["\']?', script)
    paths.extend(relative_paths)

    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in paths:
        if path and path not in seen:
            seen.add(path)
            unique_paths.append(path.strip())

    return unique_paths


def all_paths_in_sandbox(script: str, sandbox: Path) -> bool:
    """
    Validate that all paths in the script are within the sandbox.

    Args:
        script: PowerShell script content
        sandbox: Sandbox root path

    Returns:
        True if all paths are within sandbox, False otherwise
    """
    sandbox_resolved = sandbox.resolve()
    extracted_paths = extract_paths(script)

    # If no paths found, assume it's safe (probably a simple script)
    # The agents should generate scripts with explicit paths
    if not extracted_paths:
        return True

    for path_str in extracted_paths:
        try:
            # Handle relative paths by resolving them relative to sandbox
            if path_str.startswith('.'):
                resolved = (sandbox / path_str).resolve()
            else:
                resolved = Path(path_str).resolve()

            # UNC paths are not allowed
            if path_str.startswith('\\\\'):
                return False

            # Check if path is within sandbox
            if not resolved.is_relative_to(sandbox_resolved):
                return False

        except (ValueError, OSError, RuntimeError):
            # Invalid path - treat as unsafe
            return False

    return True


def classify_script(script: str, sandbox: Path) -> ScriptClassification:
    """
    Classify a PowerShell script as read, write, or unsafe.

    Args:
        script: PowerShell script content
        sandbox: Sandbox root path

    Returns:
        Script classification
    """
    # Normalize script for easier checking
    script_lower = script.lower()

    # Check path validation first
    if not all_paths_in_sandbox(script, sandbox):
        return ScriptClassification.UNSAFE

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in script_lower:
            return ScriptClassification.UNSAFE

    # Additional dangerous patterns
    dangerous_keywords = [
        'iex ',  # Invoke-Expression
        'invoke-expression',
        'downloadstring',
        'downloadfile',
        'web-request',
        'invoke-restmethod',
        'net.',  # .NET objects
        'reflection.assembly',
        'add-type',
        'import-module',
        'set-executionpolicy',
    ]

    for keyword in dangerous_keywords:
        if keyword in script_lower:
            return ScriptClassification.UNSAFE

    # Check for write cmdlets (case-insensitive)
    for cmdlet in WRITE_CMDLETS:
        if cmdlet.lower() in script_lower:
            return ScriptClassification.WRITE

    # Additional write operations
    write_keywords = [
        'set-content',
        'add-content',
        'out-file',
        'set-itemproperty',
        'clear-content',
        'new-object system.io',
    ]

    for keyword in write_keywords:
        if keyword in script_lower:
            return ScriptClassification.WRITE

    # If we get here, classify as read
    return ScriptClassification.READ


def validate_script_syntax(script: str) -> tuple[bool, str | None]:
    """
    Validate PowerShell script syntax without executing it.

    Args:
        script: PowerShell script to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Use PowerShell's parser to check syntax
        # -Command with [scriptblock]::Create() validates without executing
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"[scriptblock]::Create(@'\n{script}\n'@)"
            ],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace"
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Syntax validation failed"
            return False, f"PowerShell syntax error: {error_msg}"

        return True, None

    except subprocess.TimeoutExpired:
        return False, "Syntax validation timed out"
    except Exception as e:
        return False, f"Syntax validation failed: {str(e)}"


def execute_script(
    script: str,
    timeout: int = 60,
    cwd: Path | None = None
) -> ExecutionResult:
    """
    Execute a PowerShell script.

    Args:
        script: PowerShell script to execute
        timeout: Timeout in seconds
        cwd: Working directory for script execution (defaults to current directory)

    Returns:
        Execution result with success status, stdout, and stderr
    """
    # Validate syntax before execution
    is_valid, error = validate_script_syntax(script)
    if not is_valid:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=error or "Script has invalid PowerShell syntax",
        )

    try:
        # Build PowerShell command with better error handling
        # -NoProfile: Don't load user profile (faster startup)
        # -NonInteractive: Don't prompt for user input
        # -ExecutionPolicy Bypass: Allow script execution
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            encoding="utf-8",
            errors="replace"  # Replace encoding errors instead of failing
        )

        # PowerShell writes some errors to stdout, so check both
        # Return code 0 = success
        return ExecutionResult(
            success=result.returncode == 0,
            stdout=result.stdout.strip() if result.stdout else "",
            stderr=result.stderr.strip() if result.stderr else "",
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Script execution timed out after {timeout} seconds. The operation may be too complex or the system may be slow.",
        )
    except FileNotFoundError:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr="PowerShell is not available on this system. Please ensure PowerShell is installed and in PATH.",
        )
    except PermissionError as e:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Permission denied: {str(e)}. Check that you have permission to access the requested resources.",
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Unexpected error during script execution: {str(e)}",
        )


def check_output_size(output: str) -> tuple[bool, str | None]:
    """
    Check if output size is within limits.

    Args:
        output: Script output to check

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(output) > MAX_OUTPUT_SIZE:
        size_kb = len(output) // 1000
        return False, f"Results too large ({size_kb}KB). Try a more specific request."
    return True, None
