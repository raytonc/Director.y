"""Data models for Director.y."""

from dataclasses import dataclass
from enum import Enum


class Mode(Enum):
    """Application mode."""

    QUERY = "Query"
    TASK = "Task"


class ScriptClassification(Enum):
    """Script safety classification."""

    READ = "read"
    WRITE = "write"
    UNSAFE = "unsafe"


@dataclass
class ExecutionResult:
    """Result of script execution."""

    success: bool
    stdout: str
    stderr: str
