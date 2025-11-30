"""CLI entry point for Director.y."""

import sys
from pathlib import Path

VERSION = "1.0.0"


def show_help():
    """Display help text."""
    print("""
Director.y - AI-powered filesystem management via natural language

USAGE:
    dy [OPTIONS]

OPTIONS:
    --help, -h      Show this help message
    --version, -v   Show version information

MODES:
    Query Mode  - Ask questions about your files (read-only)
                  Example: "how many .py files are there?"

    Task Mode   - Perform file operations (requires approval)
                  Example: "organize photos by date"

CONTROLS:
    Tab             Switch between Query and Task modes
    Ctrl+C          Cancel current operation
    /quit, /exit    Exit Director.y

NOTES:
    - Must be run from within C:\\Users directory
    - All file operations require explicit approval
    - Scripts are sandboxed to current directory tree
    - Maximum output size: 100KB

For more information, visit: https://github.com/raytonc/Director.y
""")


def show_version():
    """Display version information."""
    print(f"Director.y version {VERSION}")


def validate_sandbox() -> Path:
    """
    Validate that the current working directory is under C:\\Users.

    Returns:
        Path: The validated sandbox path

    Exits:
        Exits with code 1 if CWD is not under C:\\Users
    """
    cwd = Path.cwd().resolve()
    users_root = Path("C:/Users").resolve()

    if not cwd.is_relative_to(users_root):
        print(f"Error: Director.y must be run from within C:\\Users.")
        print(f"Current directory: {cwd}")
        sys.exit(1)

    return cwd


def main():
    """Main entry point."""
    try:
        # Handle command-line arguments
        if len(sys.argv) > 1:
            arg = sys.argv[1].lower()
            if arg in ["--help", "-h"]:
                show_help()
                sys.exit(0)
            elif arg in ["--version", "-v"]:
                show_version()
                sys.exit(0)
            else:
                print(f"Error: Unknown argument '{sys.argv[1]}'")
                print("Run 'dy --help' for usage information")
                sys.exit(1)

        # Validate sandbox first
        sandbox = validate_sandbox()

        # Import and run Textual app
        from .tui.app import DirectoryApp
        app = DirectoryApp(sandbox)
        app.run()

        # Clean exit
        sys.exit(0)

    except KeyboardInterrupt:
        # User pressed Ctrl+C
        print("\nInterrupted by user.")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Fatal error: {str(e)}", file=sys.stderr)
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
