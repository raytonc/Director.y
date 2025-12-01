# Director.y

**A natural-language TUI for safely managing your Windows filesystem
with AI-generated PowerShell scripts.**

Director.y is a terminal-based tool that lets you navigate, inspect, and
manage your Windows filesystem using natural language. Describe a task
or ask a question - Director.y will generate a safe PowerShell script,
validate it, and execute it *only with your approval*.

------------------------------------------------------------------------

## Features

-   **Natural Language Interface**: Manage files without memorizing
    commands.
-   **Modern TUI**: Clean, responsive interface built with Textual.
-   **Two Modes**
    -   *Query Mode*: Read-only questions about your filesystem.
    -   *Task Mode*: File operations that require explicit approval.
-   **Safety-First Execution**: Sandboxing, path validation, script
    classification, and multi-step validation.
-   **Automatic Retry**: AI automatically fixes PowerShell syntax
    errors.
-   **Live Directory Tree**: Auto-refreshing, interactive view of your
    working directory.

------------------------------------------------------------------------

## Quick Start

### Developer Installation

``` bash
git clone https://github.com/raytonc/Director.y.git
cd Director.y

# Install in development mode
pip install -e .
```

### Configuration

1.  Copy the example environment file:

``` bash
copy .env.example .env
```

2.  Edit `.env` and add your Anthropic API key:

``` env
ANTHROPIC_API_KEY=your_actual_api_key_here
```

------------------------------------------------------------------------

## Usage

Director.y enforces a sandbox for safety and **must be run from a folder
inside `C:\Users\<YourName>`**.

``` bash
# Navigate to a folder under your user directory
cd C:\Users\YourName\Downloads

# Run Director.y
dy
```

------------------------------------------------------------------------

## How It Works

### Query Mode (Read-Only)

Ask questions like:

-   "What's taking up the most space?"
-   "How many PDFs are here?"
-   "Which files were modified today?"

**Flow:**
1. AI generates a read-only PowerShell script
2. The script is validated
3. It runs safely in the sandbox
4. Results are summarized in plain English

------------------------------------------------------------------------

### Task Mode (With Approval)

Examples:

-   "Organize files by type"
-   "Move all PDFs to Documents"
-   "Delete empty folders"
-   "Rename photos with dates"

**Flow:**
1. AI analyzes your request
2. A read-only planning script is generated
3. An execution script is produced
4. **You review and approve all changes**
5. The script executes in the sandbox
6. Results are summarized

------------------------------------------------------------------------

## Safety Features

### Multi-Layer Protection

1.  **Sandboxing** -- Never operates outside the directory you run it
    from
2.  **Path Validation** -- All paths must stay within the sandbox
3.  **Script Classification** -- Read-only, write, or unsafe
4.  **Syntax Validation** -- PowerShell syntax checked before execution
5.  **Manual Approval** -- Required for all write operations
6.  **Recycle Bin Safety** -- Deletions are soft (moved to a temp
    location)
7.  **Output Size Limits** -- Default: 100 KB
8.  **Timeouts** -- 60s for read scripts, 300s for write scripts

### Blocked Operations

-   Registry access
-   Process creation/execution
-   Network requests
-   Operations outside the sandbox
-   Dangerous cmdlets (e.g., `Invoke-Expression`)

------------------------------------------------------------------------

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

    User Question → Query Agent → Validation → Execution → Summary → User

**Task Flow**

    User Task → Planner Agent → Planning Script → Execution Plan
             → Executor Agent → Validation → Syntax Check → User Approval
             → Execute → Summary → User

------------------------------------------------------------------------

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

``` bash
dy --help
dy --version
```

------------------------------------------------------------------------

## Configuration Options

``` env
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional
MODEL=claude-sonnet-4-20250514
MAX_OUTPUT_SIZE=100000
READ_TIMEOUT=60
WRITE_TIMEOUT=300
```

------------------------------------------------------------------------

## Development

### Running Tests

``` bash
pytest tests/ -v
```

### Project Structure Highlights

-   **Agents** -- Specialized AI components for planning and execution
-   **Prompt Text** -- Stored in `/text` for maintainability
-   **Execution Layer** -- Validates and runs PowerShell scripts in a
    sandbox
-   **TUI Layer** -- Interactive interface built with Textual
-   **Workflow Engine** -- Manages multi-step AI interactions with retry
    logic

### Adding New Features

1.  Add system prompt to `src/directory/text/`
2.  Create agent in `src/directory/agents/`
3.  Add workflow in `src/directory/workflows.py`
4.  Add tests in `tests/`

------------------------------------------------------------------------

## Requirements

-   **Windows** (PowerShell required)
-   **Python 3.11+**
-   **Anthropic API Key**
-   Must be run from directories under `C:\Users\*`

------------------------------------------------------------------------

**Important:** Director.y executes PowerShell scripts. Always review
proposed changes before approving. Multiple safety layers are in place,
but *you* make the final decision.
