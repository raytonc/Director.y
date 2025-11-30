# Director.y

AI-powered filesystem management via natural language. Ask questions or give tasks, and Director.y generates and executes safe PowerShell scripts.

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
```
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

## Modes

Director.y has two modes:

### Query Mode (Read-Only)
Ask questions about your files:
- "What's taking up the most space?"
- "How many PDFs are in this folder?"
- "Show me the largest files"

### Task Mode (With Approval)
Give tasks to modify files:
- "Organize files by type"
- "Move all PDFs to Documents"
- "Delete files older than 30 days"

**Note:** Task mode requires your approval before making any changes.

Press `Tab` to switch between modes (not yet implemented - manually type queries/tasks for now).

## How It Works

1. **Query Mode:**
   - You ask a question
   - AI generates a read-only PowerShell script
   - Script is validated and executed
   - Results are summarized

2. **Task Mode:**
   - You describe a task
   - AI plans the task (read-only script)
   - AI generates execution script
   - You approve the changes
   - Script is executed
   - Results are confirmed

## Safety Features

- **Sandboxed:** Only operates within the folder you run it from
- **Validated:** All scripts are classified (read/write/unsafe)
- **Approved:** Write operations require your explicit approval
- **Limited:** Output size capped at 100KB
- **Timeout:** Scripts have time limits (60s read, 300s write)

## Examples

### Query Mode
```
> What's in this folder?

Analyzing...

This folder contains 47 files totaling 2.3 GB. Most common types:
images (18), documents (12), and archives (8).
```

### Task Mode
```
> Organize files by type

Analyzing...

┌─ Proposed Changes ─────────────────────────────────┐
│ Create 5 folders, move 47 files:                   │
│   Images (18), Documents (12), Archives (8),       │
│   Videos (5), Other (4)                            │
└────────────────────────────────────────────────────┘
Approve? [y/n]: y

Done! Organized 47 files into 5 folders.
```

## Requirements

- Windows (PowerShell required)
- Python 3.11+
- Anthropic API key
- Must run from `C:\Users\*` directories

## License

MIT
