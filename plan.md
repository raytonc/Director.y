# Director.y Implementation Plan

This document outlines the implementation phases for Director.y, a CLI tool that manages files via natural language using PowerShell scripts and LLM agents.

---

## Phase 1: Project Foundation & Configuration

### 1.1 Project Structure
- Set up directory structure as specified in design.md
- Create all module files with basic imports
- Initialize `__init__.py` files

### 1.2 Configuration System
- **File:** `src/directory/config.py`
- Implement `Settings` class using pydantic-settings
- Environment variable handling for `ANTHROPIC_API_KEY`
- Default values for model, timeouts, size limits
- Configuration validation

### 1.3 Data Models
- **File:** `src/directory/models.py`
- Define `ExecutionResult` dataclass (success, stdout, stderr)
- Define `AgentResponse` models for each agent type
- Define `Mode` enum (Query, Task)
- Define `ScriptClassification` enum (read, write, unsafe)

### 1.4 Package Configuration
- **File:** `pyproject.toml`
- Configure project metadata
- Set up `dy` console script entry point
- Define dependencies (anthropic, pydantic-settings, rich/prompt-toolkit)
- Configure build system

---

## Phase 2: Security & Sandbox Layer

### 2.1 Sandbox Validation
- **File:** `src/directory/__main__.py`
- Implement `validate_sandbox()` function
- Check CWD is under `C:\Users`
- Return resolved sandbox Path or exit with error
- Display clear error messages for invalid locations

### 2.2 Path Validation
- **File:** `src/directory/execution.py`
- Implement `extract_paths()` to parse PowerShell script for path references
- Implement `all_paths_in_sandbox()` to validate all paths are within sandbox
- Handle both absolute and relative paths
- Resolve symlinks and validate final paths

### 2.3 Script Classification
- **File:** `src/directory/execution.py`
- Define `READ_SAFE_CMDLETS` set
- Define `WRITE_CMDLETS` set
- Define `DANGEROUS_PATTERNS` list
- Implement `classify_script()` function:
  - Check path validation first
  - Check for dangerous patterns
  - Detect write cmdlets
  - Verify allowlist for read operations
  - Return classification enum

---

## Phase 3: Script Execution Engine

### 3.1 PowerShell Execution
- **File:** `src/directory/execution.py`
- Implement `execute_script()` function
- Use subprocess.run with PowerShell
- Set `-ExecutionPolicy Bypass`
- Capture stdout/stderr
- Handle timeouts (60s read, 300s write)
- Return `ExecutionResult`

### 3.2 Output Validation
- **File:** `src/directory/execution.py`
- Implement `check_output_size()` function
- Enforce 100KB limit
- Return helpful error message with actual size
- Handle edge cases (empty output, encoding issues)

### 3.3 Error Handling
- **File:** `src/directory/execution.py`
- Handle PowerShell syntax errors
- Handle execution timeouts
- Handle permission errors
- Provide user-friendly error messages

---

## Phase 4: Agent System

### 4.1 Base Agent Class
- **File:** `src/directory/agents/base.py`
- Create `BaseAgent` abstract class
- Initialize Anthropic client
- Define common methods (format prompt, parse JSON response)
- Handle API errors and retries
- JSON validation

### 4.2 Query Agent
- **File:** `src/directory/agents/query.py`
- Extend `BaseAgent`
- Implement prompt template for read-only script generation
- Include sandbox path in context
- Enforce read-only rules
- Emphasize efficiency (aggregates, limited output)
- Return JSON with `script` field

### 4.3 Planner Agent
- **File:** `src/directory/agents/planner.py`
- Extend `BaseAgent`
- Implement prompt template for planning script
- Focus on minimal data gathering
- Output only what Executor needs
- Return JSON with `script` field

### 4.4 Executor Agent
- **File:** `src/directory/agents/executor.py`
- Extend `BaseAgent`
- Implement prompt template for write script generation
- Include planning data in context
- Generate both explanation and script
- Enforce safety rules (try/catch, Recycle Bin, structured output)
- Return JSON with `explanation` and `script` fields

### 4.5 Summary Agent
- **File:** `src/directory/agents/summary.py`
- Extend `BaseAgent`
- Implement prompt template for summarization
- Handle both Query and Task modes
- Different formatting for each mode
- Return JSON with `summary` field

---

## Phase 5: User Interface Layer

### 5.1 Display Functions
- **File:** `src/directory/ui.py`
- Implement `display_header()` - show banner with mode and scope
- Implement `display()` - general output
- Implement `display_error()` - error formatting
- Implement `display_mode_switch()` - mode change indicator
- Use rich or simple ANSI colors for formatting

### 5.2 Input Handling
- **File:** `src/directory/ui.py`
- Implement `get_input()` function
- Detect TAB key for mode switching
- Detect Ctrl+C for cancellation
- Return user input and key pressed
- Show prompt with current mode

### 5.3 Approval System
- **File:** `src/directory/ui.py`
- Implement `show_approval_prompt()`
- Display explanation prominently
- Show script in collapsible/scrollable view
- Implement `user_approves()` - [y/n] prompt
- Handle invalid input

### 5.4 Status Indicators
- **File:** `src/directory/ui.py`
- "Analyzing..." message during agent calls
- Progress indication for long operations
- Clear cancellation messages

---

## Phase 6: Workflow Orchestration

### 6.1 Query Workflow
- **File:** `src/directory/main.py`
- Implement `query_flow()` async function
- Call Query Agent with question and sandbox
- Classify returned script
- Reject if not read-only
- Execute script with timeout
- Check output size
- Call Summary Agent
- Display result

### 6.2 Task Workflow
- **File:** `src/directory/main.py`
- Implement `task_flow()` async function
- Call Planner Agent
- Validate and execute planning script
- Check output size
- Call Executor Agent with planning data
- Classify execution script
- Show approval prompt
- Execute on approval
- Check output size
- Call Summary Agent
- Display result

### 6.3 Main Loop
- **File:** `src/directory/main.py`
- Implement `main()` function
- Validate sandbox on startup
- Initialize mode to "query"
- Display header
- Loop:
  - Get user input
  - Handle TAB for mode switch (only when idle)
  - Route to query_flow or task_flow
  - Handle KeyboardInterrupt
  - Track workflow_running state

---

## Phase 7: Entry Point & Integration

### 7.1 CLI Entry Point
- **File:** `src/directory/__main__.py`
- Import main() from main.py
- Add `if __name__ == "__main__":` block
- Handle top-level exceptions
- Exit with appropriate codes

### 7.2 Version Command
- Add `--version` flag support
- Display version from pyproject.toml

### 7.3 Help Text
- Add `--help` flag support
- Brief usage instructions
- Mode explanation
- Example commands

---

## Phase 8: Error Handling & Edge Cases

### 8.1 Graceful Degradation
- Handle Anthropic API failures
- Handle network issues
- Handle PowerShell not available
- Provide actionable error messages

### 8.2 Input Validation
- Handle empty user input
- Handle very long inputs
- Sanitize inputs before passing to agents

### 8.3 Edge Cases
- Empty directories
- Permission denied scenarios
- Locked files
- Very large filesystems
- Unicode/special characters in filenames

---

## Phase 9: Testing & Validation

### 9.1 Unit Tests
- **File:** `tests/test_execution.py`
- Test sandbox validation logic
- Test path extraction and validation
- Test script classification
- Test output size checking

### 9.2 Agent Tests
- **File:** `tests/test_agents.py`
- Test each agent's prompt construction
- Test JSON parsing
- Mock API responses
- Validate output formats

### 9.3 Integration Tests
- Test full query workflow
- Test full task workflow
- Test mode switching
- Test cancellation handling

### 9.4 Manual Testing
- Test in various directories
- Test with real Anthropic API
- Test edge cases found during development
- Verify Windows Explorer integration

---

## Phase 10: Documentation & Polish

### 10.1 Code Documentation
- Add docstrings to all public functions
- Add type hints throughout
- Add inline comments for complex logic

### 10.2 README
- Installation instructions
- Quick start guide
- Examples from design.md
- Configuration guide
- Troubleshooting

### 10.3 Error Messages
- Review all error messages for clarity
- Ensure consistent formatting
- Add helpful suggestions

### 10.4 Performance Optimization
- Review agent prompts for token efficiency
- Optimize script classification performance
- Add caching where appropriate

---

## Implementation Notes

### Dependencies
- `anthropic` - Claude API client
- `pydantic-settings` - Configuration management
- `rich` or `prompt-toolkit` - Terminal UI (choose one)
- Standard library: `subprocess`, `pathlib`, `asyncio`, `json`

### Development Order
Implement phases in order, as later phases depend on earlier ones:
1. Phase 1 must complete before Phase 2
2. Phases 2-3 can be developed in parallel after Phase 1
3. Phase 4 depends on Phases 1-3
4. Phase 5 can be developed alongside Phase 4
5. Phase 6 requires Phases 4-5
6. Phases 7-10 are final integration

### Testing Strategy
- Write tests alongside implementation
- Test each phase before moving to next
- Integration tests in Phase 9
- Manual validation throughout

### Key Design Principles
1. **Security first** - All sandbox/path validation before any execution
2. **Fail safely** - Default to rejecting operations if unsure
3. **User control** - Always require approval for writes
4. **Clear feedback** - Every operation has clear status/result
5. **Simple usage** - Complex logic hidden behind simple interface

---

*End of Implementation Plan*
