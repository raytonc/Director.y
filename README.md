# Director.y

**AI-powered filesystem management through natural language.**

Director.y is a command-line tool that lets you manage files using plain English. Ask questions about your files or give tasks to organize them - Director.y generates and executes safe PowerShell scripts with your approval.

## Features

- **Natural Language Interface** - No need to remember complex commands
- **Two Modes** - Query mode for questions, Task mode for file operations
- **Safety First** - Sandboxed operations, explicit approvals, and multi-layer validation
- **Powered by Claude** - Uses Claude Sonnet 4 for intelligent file operations
- **Automatic Retry** - Syntax errors are automatically fixed by AI
- **Modern TUI** - Clean terminal interface built with Textual

## Quick Start

### Installation

```bash
# Clone or navigate to the project directory
cd Director.y

# Install in development mode
pip install -e .
```

### Configuration

1. Copy the example environment file:
```bash
copy .env.example .env
```

2. Edit `.env` and add your Anthropic API key:
```env
ANTHROPIC_API_KEY=your_actual_api_key_here
```

### Usage

Director.y must be run from within `C:\Users`. Navigate to any folder under your user directory:

```bash
# Navigate to a folder
cd C:\Users\YourName\Downloads

# Run Director.y
dy
```

## How It Works

### Query Mode (Read-Only)

Ask questions about your files:
- "What's taking up the most space?"
- "How many PDFs are in this folder?"
- "Show me the largest files"
- "Which files were modified today?"

**Process:**
1. AI generates a read-only PowerShell script
2. Script is validated for safety
3. Script executes and gathers information
4. Results are summarized in plain English

### Task Mode (With Approval)

Give tasks to modify files:
- "Organize files by type"
- "Move all PDFs to Documents"
- "Delete empty folders"
- "Rename photos with dates"

**Process:**
1. AI analyzes what needs to be done (read-only script)
2. AI generates an execution script
3. **You review and approve the changes**
4. Script executes with your permission
5. Results are confirmed

## Safety Features

### Multi-Layer Protection

1. **Sandboxing** - Only operates within the folder you run it from
2. **Path Validation** - All file paths must be within the sandbox directory
3. **Script Classification** - Scripts are classified as read/write/unsafe
4. **Syntax Validation** - PowerShell syntax is validated before execution
5. **Approval Required** - Write operations require explicit user approval
6. **Recycle Bin Safety** - Deletions move files to temp (not permanent delete)
7. **Size Limits** - Output capped at 100KB to prevent excessive operations
8. **Timeouts** - Scripts have time limits (60s read, 300s write)

### Blocked Operations

- Registry access
- Process execution
- Network requests
- Operations outside sandbox
- Dangerous cmdlets (Invoke-Expression, etc.)

## Architecture

### Core Components

```
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
```

### Workflow Architecture

**Query Flow:**
```
User Question → Query Agent → Validation → Execution → Summary → User
```

**Task Flow:**
```
User Task → Planner Agent → Planning Script → Execution Plan
         → Executor Agent → Validation → Syntax Check → User Approval
         → Execute → Summary → User
```

## Commands

### In-App Commands

Type these in the Director.y input:

- `help` or `/help` - Show help information
- `quit` or `exit` - Exit Director.y
- `/quit` or `/exit` - Exit Director.y (alternative)

### Keyboard Shortcuts

- `Tab` - Switch between Query and Task modes
- `Ctrl+C` - Cancel current operation
- `Ctrl+Q` - Quit Director.y

### CLI Options

```bash
dy --help       # Show help message
dy --version    # Show version information
```

## Configuration Options

Edit `.env` to customize:

```env
# Required: Your Anthropic API key
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Override default model (default: claude-sonnet-4-20250514)
MODEL=claude-sonnet-4-20250514

# Optional: Override output size limit in bytes (default: 100000)
MAX_OUTPUT_SIZE=100000

# Optional: Override read timeout in seconds (default: 60)
READ_TIMEOUT=60

# Optional: Override write timeout in seconds (default: 300)
WRITE_TIMEOUT=300
```

## Examples

### Query Mode Examples

**Q: "What's in this folder?"**
```
This folder contains 47 files totaling 2.3 GB. Most common types:
images (18), documents (12), and archives (8).
```

**Q: "Find all PDFs larger than 10MB"**
```
Found 3 PDFs larger than 10MB:
- Report_Final.pdf (15.2 MB)
- Presentation.pdf (12.8 MB)
- Documentation.pdf (11.1 MB)
```

### Task Mode Examples

**Task: "Organize files by type"**
```
┌─ Proposed Changes ─────────────────────────────┐
│ Create 5 folders, move 47 files:               │
│   Images (18), Documents (12), Archives (8),   │
│   Videos (5), Other (4)                        │
└────────────────────────────────────────────────┘
Approve? [y/n]: y

Done! Organized 47 files into 5 folders.
```

**Task: "Delete empty folders"**
```
┌─ Proposed Changes ─────────────────────────────┐
│ Remove 12 empty folders                        │
└────────────────────────────────────────────────┘
Approve? [y/n]: y

Removed 12 empty folders.
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

- **Agents** - Specialized AI agents for different tasks
- **Text System** - Prompts stored as text files for maintainability
- **Execution Layer** - Sandboxed PowerShell execution with validation
- **TUI Layer** - Modern terminal interface with Textual
- **Workflow Engine** - Orchestrates multi-step AI workflows with retry logic

### Adding New Features

1. Add system prompt to `src/directory/text/`
2. Create agent in `src/directory/agents/`
3. Add workflow in `src/directory/workflows.py`
4. Add tests in `tests/`

## Requirements

- **Windows** - PowerShell required
- **Python 3.11+** - Modern Python features
- **Anthropic API Key** - For Claude AI
- **Must run from** `C:\Users\*` directories

## License

MIT License - See [LICENSE](LICENSE) for details

## Contributing

Issues and pull requests welcome at [github.com/raytonc/Director.y](https://github.com/raytonc/Director.y)

## Acknowledgments

- Built with [Anthropic Claude](https://www.anthropic.com/claude)
- Terminal UI powered by [Textual](https://github.com/Textualize/textual)
- Configuration via [Pydantic Settings](https://github.com/pydantic/pydantic-settings)

---

**⚠️ Important:** Director.y executes PowerShell scripts. Always review proposed changes before approving. While multiple safety layers are in place, you are responsible for approving operations.
