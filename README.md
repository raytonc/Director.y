# Director.y

**A natural-language TUI for safely managing your Windows filesystem with
AI-generated PowerShell scripts.**

Director.y is a terminal-based tool that lets you navigate, inspect, and manage
your Windows filesystem using natural language. Describe a task or ask a
question - Director.y will generate a safe PowerShell script, validate it, and
execute it _only with your approval_.

---

## Features

-   **Natural Language Interface**: Manage files without memorizing commands.
-   **Modern TUI**: Clean, responsive interface built with Textual.
-   **Safety-First Execution**: Sandboxing, path validation, script
    classification, and automatic syntax validation with retry for all scripts.
-   **Two Modes**
    -   _Query Mode_: Read-only questions about your filesystem.
    -   _Task Mode_: File operations that require explicit approval.
-   **Live Directory Tree**: Auto-refreshing, interactive view of your working
    directory.
-   **Flexible LLM Integration**: Provider and model agnostic

---

## Installation

### From PyPI (Recommended)

```bash
pip install directory-agent
```

After installation, verify the `dy` command is available:

```bash
dy --version
```

**Note:** If the `dy` command isn't recognized, ensure Python's Scripts
directory is in your PATH.

### From Source (For Development)

```bash
git clone https://github.com/raytonc/Director.y.git
cd Director.y

# Install in development mode
pip install -e .
```

---

## Configuration

Run the interactive configuration wizard to set up your API key:

```bash
dy --configure
```

The wizard will guide you through:

1. Selecting your AI provider
2. Entering and validating your API key
3. Choosing a model
4. Configuring timeouts and output limits

Your configuration will be saved to `%APPDATA%\directory\config.toml` (Windows).

---

## Usage

Director.y enforces a sandbox for safety and **must be run from a folder inside
`C:\Users\<YourName>`**.

```bash
# Navigate to a folder under your user directory
cd C:\Users\YourName\Downloads

# Run Director.y
dy
```

---

## How It Works

### Query Mode (Read-Only)

Ask questions like:

-   "What's taking up the most space?"
-   "Which files were modified today?"

**Flow:**

1. AI generates a read-only PowerShell script
2. Syntax validation (with automatic retry if errors are found)
3. Script classification and safety checks
4. Execution in the sandbox
5. Results are summarized in plain English

---

### Task Mode (With Approval)

Examples:

-   "Organize files by type"
-   "Move all PDFs to Documents"
-   "Delete empty folders"
-   "Rename photos with dates"

**Flow:**

1. AI generates a planning script to analyze your request
2. Syntax validation with retry (planning script)
3. Planning script executes (read-only)
4. AI generates an execution script based on the analysis
5. Syntax validation with retry (execution script)
6. Safety classification check
7. **You review and approve all changes**
8. The script executes in the sandbox
9. Results are summarized

---

## Safety Features

### Multi-Layer Protection

1.  **Sandboxing** -- Never operates outside the directory you run it from
2.  **Path Validation** -- All paths must stay within the sandbox
3.  **Script Classification** -- Read-only, write, or unsafe
4.  **Syntax Validation with Retry** -- All scripts validated before execution;
    AI automatically fixes syntax errors
5.  **Manual Approval** -- Required for all write operations
6.  **Recycle Bin Safety** -- Deletions are soft (moved to a temp location)
7.  **Output Size Limits** -- Default: 100 KB
8.  **Timeouts** -- 60s for read scripts, 300s for write scripts

### Blocked Operations

-   Registry access
-   Process creation/execution
-   Network requests
-   Operations outside the sandbox
-   Dangerous cmdlets (e.g., `Invoke-Expression`)

---

## Architecture

### Core Components

    src/directory/
    ├── agents/           # AI agents for different tasks
    │   ├── query.py      # Generates read-only scripts
    │   ├── planner.py    # Plans task execution
    │   ├── executor.py   # Generates write scripts
    │   └── summary.py    # Summarizes results
    ├── text/             # System prompts and text content
    ├── tui/              # Terminal user interface
    ├── execution.py      # Script validation and execution
    ├── workflows.py      # Orchestrates multi-step workflows
    └── config.py         # Configuration management

### Workflow Overview

**Query Flow**

    User Question → Query Agent → Validation → Execution → Summary

**Task Flow**

    User Task → Planner Agent → Validation → Execution → Executor Agent → Validation → User Approval → Execution → Summary

---

## Commands

### In-App Commands

-   `help` or `/help` -- Show help
-   `quit` or `exit` -- Exit Director.y
-   `/quit` or `/exit` -- Alternative exit aliases

### Keyboard Shortcuts

-   `Tab` -- Switch between Query and Task modes
-   `Ctrl+C` -- Cancel current operation
-   `Ctrl+Q` -- Quit Director.y

### CLI Options

```bash
dy --help          # Show help message
dy --version       # Show version information
dy --configure     # Configure API keys and settings
```

---

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure Highlights

-   **Agents** -- Specialized AI agents for planning and execution
-   **Execution Layer** -- Validates and runs PowerShell scripts safely
-   **TUI Layer** -- Interactive interface built with Textual
-   **Workflow Engine** -- Manages multi-step AI interactions with retry logic

### Adding New Features

1.  Add system prompt to `src/directory/text/`
2.  Create agent in `src/directory/agents/`
3.  Add workflow in `src/directory/workflows.py`
4.  Add tests in `tests/`

---

## Requirements

-   **Windows** (PowerShell required)
-   **Python 3.11+**

---

**Important:** Director.y executes PowerShell scripts. Always review proposed
changes before approving. Multiple safety layers are in place, but _you_ make
the final decision.
