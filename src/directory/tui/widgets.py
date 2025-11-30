"""Custom Textual widgets for Director.y."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from ..models import Mode


class AppHeader(Container):
    """Custom header widget for Director.y."""

    DEFAULT_CSS = """
    AppHeader {
        height: 4;
        dock: top;
        background: $primary;
        padding: 1;
    }

    AppHeader #title {
        width: auto;
        content-align: left middle;
        text-style: bold;
    }

    AppHeader #mode-badge {
        width: auto;
        padding: 0 3;
        margin-left: 2;
        content-align: center middle;
        text-style: bold;
        border: heavy;
    }

    AppHeader #sandbox-path {
        width: 1fr;
        content-align: left middle;
        margin-left: 2;
        color: $text-muted;
    }

    AppHeader #shortcuts {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    AppHeader .query-mode {
        background: $success;
        border: heavy $success-darken-2;
        color: $text;
    }

    AppHeader .task-mode {
        background: $warning;
        border: heavy $warning-darken-2;
        color: $text;
    }
    """

    def __init__(self, sandbox: Path, mode: Mode) -> None:
        """
        Initialize the header.

        Args:
            sandbox: Current sandbox path
            mode: Current mode
        """
        super().__init__()
        self.sandbox = sandbox
        self.mode = mode

    def compose(self) -> ComposeResult:
        """Build the header layout."""
        # Top row: Title, mode badge, sandbox path
        with Container(id="header-top"):
            yield Static("Director.y", id="title")
            mode_icon = "🔍" if self.mode == Mode.QUERY else "⚡"
            yield Static(
                f"{mode_icon} {self.mode.value.upper()} MODE {mode_icon}",
                id="mode-badge",
                classes="query-mode" if self.mode == Mode.QUERY else "task-mode"
            )
            yield Static(f"Scope: {self.sandbox}", id="sandbox-path")

        # Bottom row: Keyboard shortcuts
        yield Static(
            "Tab: Switch Mode | Ctrl+C: Cancel | Ctrl+Q: Quit",
            id="shortcuts"
        )

    def update_mode(self, mode: Mode) -> None:
        """
        Update the mode badge.

        Args:
            mode: New mode
        """
        self.mode = mode
        badge = self.query_one("#mode-badge", Static)
        mode_icon = "🔍" if mode == Mode.QUERY else "⚡"
        badge.update(f"{mode_icon} {mode.value.upper()} MODE {mode_icon}")

        # Update styling
        badge.remove_class("query-mode", "task-mode")
        badge.add_class("query-mode" if mode == Mode.QUERY else "task-mode")
