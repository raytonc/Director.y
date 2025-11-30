"""User interface functions."""

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

from .models import Mode


def display_header(sandbox: Path, mode: Mode):
    """
    Display the application header with scope and mode.

    Args:
        sandbox: Current sandbox path
        mode: Current mode (Query or Task)
    """
    # TODO: Implement with rich formatting
    print(f"\n┌─────────────────────────────────────────────────────────────────┐")
    print(f"│  Director.y                                     [{mode.value} Mode ▼]  │")
    print(f"│  Scope: {sandbox}                                 │")
    print(f"│                                                                 │")
    print(f"│  Tab: switch mode | Ctrl+C: cancel | /quit or /exit: exit      │")
    print(f"│                                                                 │")
    print(f"└─────────────────────────────────────────────────────────────────┘\n")


def display(message: str):
    """Display a general message."""
    print(message)


def display_error(message: str):
    """Display an error message."""
    print(f"Error: {message}")


def display_mode_switch(mode: Mode):
    """Display mode switch notification."""
    print(f"\n[Switched to {mode.value} Mode]\n")


def display_script(script: str):
    """
    Display the script being executed for transparency.

    Args:
        script: The PowerShell script to display
    """
    print("\n┌─ Executing Script ─────────────────────────────────┐")
    for line in script.split("\n"):
        # Truncate very long lines for readability
        display_line = line[:70] + "..." if len(line) > 70 else line
        print(f"│ {display_line}")
    print("└────────────────────────────────────────────────────┘\n")


def get_input() -> tuple[str, str | None]:
    """
    Get user input and detect special keys.

    Returns:
        Tuple of (user_input, key_pressed)
        key_pressed can be None, "TAB", or "CTRL+C"
    """
    # Create key bindings to detect Tab key press
    kb = KeyBindings()
    tab_pressed = {"value": False}

    @kb.add("tab")
    def handle_tab(event):
        """Handle Tab key press - switches mode, doesn't insert tab."""
        tab_pressed["value"] = True
        # Accept the current input (even if empty) and exit the prompt
        event.app.current_buffer.validate_and_handle()

    # Create a session with the key bindings
    session = PromptSession(key_bindings=kb)

    try:
        user_input = session.prompt("> ")

        # Check if Tab was pressed
        if tab_pressed["value"]:
            return user_input, "TAB"
        return user_input, None
    except KeyboardInterrupt:
        return "", "CTRL+C"


def show_approval_prompt(explanation: str, script: str):
    """
    Show the approval prompt with explanation and script.

    Args:
        explanation: What will change
        script: The PowerShell script to execute
    """
    print("\n┌─ Proposed Changes ─────────────────────────────────┐")
    print(f"│ {explanation}")
    print("├─ Script ───────────────────────────────────────────┤")
    # Show first few lines of script
    lines = script.split("\n")[:5]
    for line in lines:
        print(f"│ {line[:50]}")
    if len(script.split("\n")) > 5:
        print(f"│ ... ({len(script.split('\n')) - 5} more lines)")
    print("└────────────────────────────────────────────────────┘")


def user_approves() -> bool:
    """
    Prompt user for approval.

    Returns:
        True if user approves, False otherwise
    """
    while True:
        response = input("Approve? [y/n]: ").lower().strip()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please enter 'y' or 'n'")
