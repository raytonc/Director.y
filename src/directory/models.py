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


@dataclass
class QueryResponse:
    """Response from Query Agent."""

    script: str


@dataclass
class PlannerResponse:
    """Response from Planner Agent."""

    script: str


@dataclass
class ExecutorResponse:
    """Response from Executor Agent."""

    explanation: str
    script: str


@dataclass
class SummaryResponse:
    """Response from Summary Agent."""

    summary: str
