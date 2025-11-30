"""Tests for execution module."""

import pytest
from pathlib import Path
from directory.execution import (
    extract_paths,
    all_paths_in_sandbox,
    classify_script,
    check_output_size,
    execute_script,
)
from directory.models import ScriptClassification


class TestExtractPaths:
    """Tests for path extraction from PowerShell scripts."""

    def test_extract_quoted_paths(self):
        """Test extraction of quoted paths."""
        script = '''
        $path = "C:\\Users\\test\\file.txt"
        Get-Item 'C:\\Users\\test\\other.txt'
        '''
        paths = extract_paths(script)
        assert "C:\\Users\\test\\file.txt" in paths
        assert "C:\\Users\\test\\other.txt" in paths

    def test_extract_parameter_paths(self):
        """Test extraction of paths in parameters."""
        script = 'Get-ChildItem -Path "C:\\Users\\test" -Recurse'
        paths = extract_paths(script)
        assert "C:\\Users\\test" in paths

    def test_extract_relative_paths(self):
        """Test extraction of relative paths."""
        script = '''
        Get-Item .\\subfolder\\file.txt
        Get-Item ..\\parent\\file.txt
        '''
        paths = extract_paths(script)
        assert any(".\\subfolder\\file.txt" in p for p in paths)
        assert any("..\\parent\\file.txt" in p for p in paths)

    def test_no_duplicate_paths(self):
        """Test that duplicate paths are removed."""
        script = '''
        $path = "C:\\Users\\test\\file.txt"
        Get-Item "C:\\Users\\test\\file.txt"
        '''
        paths = extract_paths(script)
        assert paths.count("C:\\Users\\test\\file.txt") == 1

    def test_empty_script(self):
        """Test extraction from empty script."""
        paths = extract_paths("")
        assert paths == []


class TestSandboxValidation:
    """Tests for sandbox path validation."""

    def test_valid_absolute_path_in_sandbox(self):
        """Test that absolute paths within sandbox are allowed."""
        sandbox = Path("C:/Users/test")
        script = 'Get-ChildItem "C:\\Users\\test\\Downloads"'
        assert all_paths_in_sandbox(script, sandbox) is True

    def test_invalid_absolute_path_outside_sandbox(self):
        """Test that absolute paths outside sandbox are rejected."""
        sandbox = Path("C:/Users/test")
        script = 'Get-ChildItem "C:\\Windows\\System32"'
        assert all_paths_in_sandbox(script, sandbox) is False

    def test_valid_relative_path(self):
        """Test that relative paths are resolved relative to sandbox."""
        sandbox = Path("C:/Users/test")
        script = 'Get-ChildItem ".\\Downloads"'
        assert all_paths_in_sandbox(script, sandbox) is True

    def test_unc_path_rejected(self):
        """Test that UNC paths are rejected."""
        sandbox = Path("C:/Users/test")
        script = 'Get-ChildItem "\\\\server\\share"'
        assert all_paths_in_sandbox(script, sandbox) is False

    def test_no_paths_in_script(self):
        """Test that scripts with no paths are allowed."""
        sandbox = Path("C:/Users/test")
        script = 'Write-Output "Hello World"'
        assert all_paths_in_sandbox(script, sandbox) is True

    def test_parent_directory_escape_attempt(self):
        """Test that attempts to escape via parent directory are caught."""
        sandbox = Path("C:/Users/test/subfolder")
        script = 'Get-ChildItem "..\\..\\..\\Windows"'
        assert all_paths_in_sandbox(script, sandbox) is False


class TestScriptClassification:
    """Tests for script classification."""

    def test_classify_read_only_script(self):
        """Test classification of read-only scripts."""
        sandbox = Path("C:/Users/test")
        script = '''
        Get-ChildItem "C:\\Users\\test" |
        Where-Object {$_.Extension -eq ".txt"} |
        Measure-Object -Property Length -Sum |
        ConvertTo-Json
        '''
        assert classify_script(script, sandbox) == ScriptClassification.READ

    def test_classify_write_script(self):
        """Test classification of write scripts."""
        sandbox = Path("C:/Users/test")
        script = 'Move-Item "C:\\Users\\test\\file.txt" "C:\\Users\\test\\backup\\"'
        assert classify_script(script, sandbox) == ScriptClassification.WRITE

    def test_classify_unsafe_script_dangerous_cmdlet(self):
        """Test that dangerous cmdlets are classified as unsafe."""
        sandbox = Path("C:/Users/test")
        script = 'Invoke-Expression "malicious code"'
        assert classify_script(script, sandbox) == ScriptClassification.UNSAFE

    def test_classify_safe_script_env_variable(self):
        """Test that environment variable access is allowed (for sandboxed operations like $env:TEMP)."""
        sandbox = Path("C:/Users/test")
        script = 'Move-Item "C:/Users/test/file.txt" -Destination "$env:TEMP"'
        # Should be WRITE since Move-Item is a write operation, but not UNSAFE
        assert classify_script(script, sandbox) == ScriptClassification.WRITE

    def test_classify_unsafe_script_registry(self):
        """Test that registry access is unsafe."""
        sandbox = Path("C:/Users/test")
        script = 'Get-Item "HKLM:\\Software"'
        assert classify_script(script, sandbox) == ScriptClassification.UNSAFE

    def test_classify_unsafe_script_path_outside_sandbox(self):
        """Test that paths outside sandbox make script unsafe."""
        sandbox = Path("C:/Users/test")
        script = 'Get-ChildItem "C:\\Windows"'
        assert classify_script(script, sandbox) == ScriptClassification.UNSAFE

    def test_classify_write_script_new_item(self):
        """Test that New-Item is classified as write."""
        sandbox = Path("C:/Users/test")
        script = 'New-Item -Path "C:\\Users\\test\\newfolder" -ItemType Directory'
        assert classify_script(script, sandbox) == ScriptClassification.WRITE

    def test_classify_write_script_remove_item(self):
        """Test that Remove-Item is classified as write."""
        sandbox = Path("C:/Users/test")
        script = 'Remove-Item "C:\\Users\\test\\file.txt"'
        assert classify_script(script, sandbox) == ScriptClassification.WRITE

    def test_classify_unsafe_script_start_process(self):
        """Test that Start-Process is unsafe."""
        sandbox = Path("C:/Users/test")
        script = 'Start-Process "notepad.exe"'
        assert classify_script(script, sandbox) == ScriptClassification.UNSAFE

    def test_classify_unsafe_script_web_request(self):
        """Test that web requests are unsafe."""
        sandbox = Path("C:/Users/test")
        script = 'Invoke-WebRequest "http://example.com"'
        assert classify_script(script, sandbox) == ScriptClassification.UNSAFE

    def test_classify_case_insensitive(self):
        """Test that classification is case-insensitive."""
        sandbox = Path("C:/Users/test")
        script = 'move-item "C:\\Users\\test\\file.txt" "C:\\Users\\test\\backup\\"'
        assert classify_script(script, sandbox) == ScriptClassification.WRITE


class TestOutputSizeCheck:
    """Tests for output size validation."""

    def test_valid_output_size(self):
        """Test that output within limits is valid."""
        output = "x" * 50000  # 50KB
        is_valid, error = check_output_size(output)
        assert is_valid is True
        assert error is None

    def test_output_too_large(self):
        """Test that output exceeding limits is rejected."""
        output = "x" * 150000  # 150KB
        is_valid, error = check_output_size(output)
        assert is_valid is False
        assert error is not None
        assert "too large" in error.lower()

    def test_empty_output(self):
        """Test that empty output is valid."""
        is_valid, error = check_output_size("")
        assert is_valid is True
        assert error is None

    def test_exactly_at_limit(self):
        """Test output exactly at the limit."""
        output = "x" * 100000  # Exactly 100KB
        is_valid, error = check_output_size(output)
        assert is_valid is True
        assert error is None


class TestScriptExecution:
    """Tests for PowerShell script execution."""

    def test_execute_simple_script(self):
        """Test execution of a simple PowerShell script."""
        script = 'Write-Output "Hello, World!"'
        result = execute_script(script)
        assert result.success is True
        assert "Hello, World!" in result.stdout
        assert result.stderr == ""

    def test_execute_json_output(self):
        """Test execution of script with JSON output."""
        script = '@{Name="Test"; Value=123} | ConvertTo-Json'
        result = execute_script(script)
        assert result.success is True
        assert "Test" in result.stdout
        assert "123" in result.stdout

    def test_execute_arithmetic(self):
        """Test execution of arithmetic operations."""
        script = 'Write-Output (2 + 2)'
        result = execute_script(script)
        assert result.success is True
        assert "4" in result.stdout

    def test_execute_script_with_error(self):
        """Test execution of script that produces an error."""
        script = 'Get-Item "C:\\NonExistentFile12345.txt"'
        result = execute_script(script)
        assert result.success is False
        # PowerShell may write errors to stderr or return non-zero exit code

    def test_execute_script_with_timeout(self):
        """Test that timeout is enforced."""
        # Script that sleeps for 5 seconds
        script = 'Start-Sleep -Seconds 5'
        result = execute_script(script, timeout=1)
        assert result.success is False
        assert "timed out" in result.stderr.lower()

    def test_execute_invalid_powershell_syntax(self):
        """Test execution of script with syntax errors."""
        script = 'this is not valid powershell syntax {'
        result = execute_script(script)
        assert result.success is False

    def test_execute_get_childitem(self):
        """Test Get-ChildItem cmdlet (common read operation)."""
        # Get items in temp directory (should exist on Windows)
        script = 'Get-ChildItem $env:TEMP | Select-Object -First 1 | ConvertTo-Json'
        result = execute_script(script)
        # May succeed or fail depending on permissions, but shouldn't crash
        assert isinstance(result.success, bool)

    def test_execute_empty_script(self):
        """Test execution of empty script."""
        result = execute_script("")
        # Empty script should succeed with no output
        assert result.success is True
        assert result.stdout == ""

    def test_execute_with_working_directory(self):
        """Test execution with custom working directory."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            script = '(Get-Location).Path'
            result = execute_script(script, cwd=Path(tmpdir))
            assert result.success is True
            # Output should contain the temp directory path
            assert tmpdir.replace("\\", "").replace("/", "") in result.stdout.replace("\\", "").replace("/", "")

    def test_execute_multiline_script(self):
        """Test execution of multiline script."""
        script = '''
        $x = 10
        $y = 20
        Write-Output ($x + $y)
        '''
        result = execute_script(script)
        assert result.success is True
        assert "30" in result.stdout
