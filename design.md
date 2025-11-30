# Director.y — Design Document

---

## 1. Overview

**Director.y** (`dy`) is a CLI tool that manages files via natural language. Run it in any folder under `C:\Users`, and it operates only within that folder.

```
C:\Users\john\Downloads> dy
```

**Key Principles:**
- Sandboxed to current working directory (must be under `C:\Users`)
- User selects mode: Query (ask questions) or Task (make changes)
- Read operations auto-execute; write operations require approval
- 4 specialized agents, each with focused responsibility

---

## 2. Usage

### Basic Usage

```bash
# In any folder under C:\Users
C:\Users\john\Downloads> dy

┌─────────────────────────────────────────────────────────────────┐
│  Director.y                                     [Query Mode ▼]  │
│  Scope: C:\Users\john\Downloads                                 │
│                                                                 │
│  Tab: switch mode | Ctrl+C: cancel                              │
│                                                                 │
│  > _                                                            │
└─────────────────────────────────────────────────────────────────┘
```

### File Explorer Integration

Type `dy` in Explorer's address bar to launch Director.y in that folder:

```
┌──────────────────────────────────────────────────────────────┐
│ ← → ↑  │  dy                                            │ → │
├──────────────────────────────────────────────────────────────┤
│  📁 Documents                                                │
│  📁 Downloads                                                │
│  ...                                                         │
└──────────────────────────────────────────────────────────────┘
         ↓ Enter
┌─────────────────────────────────────────────────────────────────┐
│  Director.y                                     [Query Mode ▼]  │
│  Scope: C:\Users\john                                           │
│  ...                                                            │
└─────────────────────────────────────────────────────────────────┘
```

This works automatically when `dy` is on PATH.

### Invalid Location

```bash
C:\Windows> dy

Error: Director.y must be run from within C:\Users.
Current directory: C:\Windows
```

---

## 3. Architecture

```
                    ┌─────────────┐
                    │    User     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Validate CWD │ ← Must be under C:\Users
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Mode Select │ ← Tab (when idle)
                    │ Query │ Task│
                    └──┬───────┬──┘
                       │       │
         ┌─────────────┘       └─────────────┐
         ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────┐
│    Query Flow       │           │     Task Flow       │
│    (2 LLM calls)    │           │    (3 LLM calls)    │
│                     │           │                     │
│  Query Agent        │           │  Planner Agent      │
│       ↓             │           │       ↓             │
│  [auto-execute]     │           │  [auto-execute]     │
│       ↓             │           │       ↓             │
│  [size check]       │           │  [size check]       │
│       ↓             │           │       ↓             │
│  Summary Agent      │           │  Executor Agent     │
│                     │           │       ↓             │
│                     │           │  [user approval]    │
│                     │           │       ↓             │
│                     │           │  [execute]          │
│                     │           │       ↓             │
│                     │           │  [size check]       │
│                     │           │       ↓             │
│                     │           │  Summary Agent      │
└─────────────────────┘           └─────────────────────┘

     0 approvals                       1 approval
```

---

## 4. Sandbox Model

### Rules

1. **Sandbox = Current Working Directory (CWD)**
2. **CWD must be under `C:\Users`**
3. **All operations restricted to sandbox**

### Validation

```python
def validate_sandbox() -> Path:
    cwd = Path.cwd().resolve()
    users_root = Path("C:/Users").resolve()
    
    if not cwd.is_relative_to(users_root):
        print(f"Error: Director.y must be run from within C:\\Users.")
        print(f"Current directory: {cwd}")
        sys.exit(1)
    
    return cwd
```

### Examples

| CWD | Sandbox | Valid? |
|-----|---------|--------|
| `C:\Users\john\Downloads` | `C:\Users\john\Downloads` | ✅ |
| `C:\Users\john` | `C:\Users\john` | ✅ |
| `C:\Users` | `C:\Users` | ✅ |
| `C:\Windows` | — | ❌ |
| `D:\Files` | — | ❌ |

### Displayed Scope

The UI always shows the current scope:

```
┌─────────────────────────────────────────────────────────────────┐
│  Director.y                                     [Query Mode ▼]  │
│  Scope: C:\Users\john\Downloads                                 │
│  ...                                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Agents

### Overview

| Agent | Input | Output |
|-------|-------|--------|
| Query Agent | User question | Read script |
| Planner Agent | User task | Read script |
| Executor Agent | Task + filesystem data | Write script + explanation |
| Summary Agent | Request + script output | Human-friendly summary |

### Query Agent

```
Generate a PowerShell script to answer the user's question.
Scope: {sandbox_path}

Output JSON: {"script": "<PowerShell>"}

Rules:
- Read operations only (Get-ChildItem, Measure-Object, etc.)
- Output via ConvertTo-Json
- Stay within scope

Efficiency:
- Output ONLY fields needed to answer the question
- Prefer aggregates over listings
- Default: Select-Object -First 50
```

### Planner Agent

```
Generate a PowerShell script to gather info for planning a task.
Scope: {sandbox_path}

Output JSON: {"script": "<PowerShell>"}

Rules:
- Read operations only
- Output via ConvertTo-Json
- Stay within scope

Efficiency — output minimum needed to plan:
- "Organize by type" → extension counts, not file list
- "Move PDFs" → PDF names only
- Only include fields the Executor will need
```

### Executor Agent

```
Generate a PowerShell script to execute the task safely.
Scope: {sandbox_path}

Output JSON: {"explanation": "<what will change>", "script": "<PowerShell>"}

Explanation: be specific (e.g., "Move 12 PDFs to Documents")

Script rules:
- Output results via ConvertTo-Json
- Use try/catch for errors
- Use Recycle Bin for deletes
- Output: {"moved": 12, "errors": []} not verbose logs
```

### Summary Agent

```
Summarize script output for the user.
Mode: {mode} | Request: {original_request}

Output JSON: {"summary": "<response>"}

Query: Lead with answer, include key numbers, 2-3 sentences.
Task: Confirm what was done, note errors, 1-2 sentences.
```

---

## 6. Script Execution

### Classification

```python
READ_SAFE_CMDLETS = {
    "Get-ChildItem", "Get-Item", "Test-Path", "Resolve-Path",
    "Select-Object", "Where-Object", "Sort-Object", "Group-Object",
    "Measure-Object", "ForEach-Object", "ConvertTo-Json", "Write-Output",
}

def classify_script(script: str, sandbox: Path) -> Literal["read", "write", "unsafe"]:
    if not all_paths_in_sandbox(script, sandbox):
        return "unsafe"
    
    dangerous = ["Invoke-", "Start-Process", "$env:", "HKLM:", "HKCU:"]
    if any(p in script for p in dangerous):
        return "unsafe"
    
    write_cmdlets = {"Move-Item", "Copy-Item", "Remove-Item", "New-Item", "Rename-Item"}
    if any(cmd in script for cmd in write_cmdlets):
        return "write"
    
    if uses_only_allowlisted(script, READ_SAFE_CMDLETS):
        return "read"
    
    return "write"
```

### Path Validation

```python
def all_paths_in_sandbox(script: str, sandbox: Path) -> bool:
    sandbox_resolved = sandbox.resolve()
    for path_str in extract_paths(script):
        resolved = Path(path_str).resolve()
        if not resolved.is_relative_to(sandbox_resolved):
            return False
    return True
```

### Execution

```python
def execute_script(script: str, timeout: int = 60) -> ExecutionResult:
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return ExecutionResult(
        success=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
    )
```

### Output Size Limit

```python
MAX_OUTPUT_SIZE = 100_000  # 100KB

def check_output_size(output: str) -> tuple[bool, str | None]:
    if len(output) > MAX_OUTPUT_SIZE:
        return False, f"Results too large ({len(output)//1000}KB). Try a more specific request."
    return True, None
```

---

## 7. Workflows

### Query Flow

```python
async def query_flow(question: str, sandbox: Path):
    response = await query_agent.call(question, sandbox)
    script = response["script"]
    
    if classify_script(script, sandbox) != "read":
        return display_error("Cannot access that location.")
    
    print("Analyzing...")
    result = execute_script(script)
    
    if not result.success:
        return display_error(result.stderr)
    
    ok, error = check_output_size(result.stdout)
    if not ok:
        return display_error(error)
    
    summary = await summary_agent.call("query", question, result.stdout)
    display(summary["summary"])
```

### Task Flow

```python
async def task_flow(task: str, sandbox: Path):
    # Plan
    plan = await planner_agent.call(task, sandbox)
    if classify_script(plan["script"], sandbox) != "read":
        return display_error("Cannot access that location.")
    
    print("Analyzing...")
    read_result = execute_script(plan["script"])
    
    if not read_result.success:
        return display_error(read_result.stderr)
    
    ok, error = check_output_size(read_result.stdout)
    if not ok:
        return display_error(error)
    
    # Execute
    exec_response = await executor_agent.call(task, read_result.stdout, sandbox)
    
    if classify_script(exec_response["script"], sandbox) == "unsafe":
        return display_error("Cannot perform that operation.")
    
    show_approval_prompt(exec_response["explanation"], exec_response["script"])
    if not user_approves():
        return display("Cancelled.")
    
    write_result = execute_script(exec_response["script"], timeout=300)
    
    if not write_result.success:
        return display_error(write_result.stderr)
    
    ok, error = check_output_size(write_result.stdout)
    if not ok:
        return display_error(error)
    
    summary = await summary_agent.call("task", task, write_result.stdout)
    display(summary["summary"])
```

### Main Loop

```python
def main():
    sandbox = validate_sandbox()  # Exit if not under C:\Users
    
    mode = "query"
    workflow_running = False
    
    display_header(sandbox)
    
    while True:
        user_input, key = get_input()
        
        if key == "TAB" and not workflow_running:
            mode = "task" if mode == "query" else "query"
            display_mode_switch(mode)
            continue
        
        try:
            workflow_running = True
            if mode == "query":
                await query_flow(user_input, sandbox)
            else:
                await task_flow(user_input, sandbox)
        except KeyboardInterrupt:
            display("Cancelled.")
        finally:
            workflow_running = False
```

---

## 8. Configuration

```python
class Settings(BaseSettings):
    anthropic_api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_output_size: int = 100_000
    read_timeout: int = 60
    write_timeout: int = 300
    
    # Sandbox is determined at runtime from CWD
```

---

## 9. Installation

### Via pip

```bash
pip install directory
```

### Verify PATH

After installation, verify `dy` is accessible:

```bash
dy --version
Director.y v1.0.0
```

### Explorer Integration

Once installed and on PATH, typing `dy` in File Explorer's address bar automatically:
1. Opens a terminal
2. Sets CWD to that folder
3. Launches Director.y with that folder as scope

No additional configuration needed.

---

## 10. Project Structure

```
directory/
├── pyproject.toml
├── README.md
├── src/directory/
│   ├── __init__.py
│   ├── __main__.py      # Entry point, sandbox validation
│   ├── config.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── query.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   └── summary.py
│   ├── execution.py     # Script classification, validation, execution
│   ├── models.py
│   ├── ui.py
│   └── main.py          # Main loop, workflows
└── tests/
    ├── test_agents.py
    └── test_execution.py
```

### pyproject.toml

```toml
[project]
name = "directory"
version = "1.0.0"
description = "AI-powered filesystem management"

[project.scripts]
dy = "directory.__main__:main"
```

---

## 11. Security

| Layer | Enforcement |
|-------|-------------|
| CWD validation | Must be under `C:\Users` |
| Cmdlet allowlist | Only safe cmdlets auto-execute |
| Path validation | Python resolves all paths |
| Mode separation | Query can't produce write scripts |
| User approval | Required for write operations |
| Output limit | 100KB max |

**Blocked:** Paths outside sandbox, `$env:`, registry, network, external processes.

**Allowed:** Symlinks within sandbox (trusted user setup).

---

## 12. Future Extensibility

| Extension | Changes |
|-----------|---------|
| Other LLMs | Add provider interface |
| macOS/Linux | Bash scripts, validate CWD under `~` or `/home` |

---

## Appendix: Examples

### Query

```
C:\Users\john\Downloads> dy

[Query Mode]
Scope: C:\Users\john\Downloads

> What's taking up the most space?

Analyzing...

This folder has 8.2 GB across 156 files. Largest: project-backup.zip 
(2.1 GB) and tutorial-videos/ (1.8 GB) — nearly half the total.
```

### Task

```
C:\Users\john\Downloads> dy

[Task Mode]
Scope: C:\Users\john\Downloads

> Organize by file type

Analyzing...

┌─ Proposed Changes ─────────────────────────────────┐
│ Create 5 folders, move 47 files:                   │
│   Images (18), Documents (12), Archives (8),       │
│   Videos (5), Other (4)                            │
├─ Script ───────────────────────────────────────────┤
│ $basePath = "C:\Users\john\Downloads" ...          │
└────────────────────────────────────────────────────┘
Approve? [y/n]: y

Done! Organized 47 files into 5 folders.
```

### Scope Display

```
C:\Users\john> dy

[Query Mode]
Scope: C:\Users\john

> What's in Downloads?

Analyzing...

Your Downloads folder has 47 files totaling 2.3 GB.
```

### Invalid Location

```
C:\Windows\System32> dy

Error: Director.y must be run from within C:\Users.
Current directory: C:\Windows\System32
```

### Too Large

```
[Query Mode]
Scope: C:\Users\john

> List every file recursively

Analyzing...

Results too large (2,450KB). Try a more specific request.
```

---

*End of Document*
