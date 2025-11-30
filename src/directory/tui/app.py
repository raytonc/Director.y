"""Main Textual application for Director.y."""

import asyncio
from pathlib import Path
from threading import Event

from rich.panel import Panel
from rich.syntax import Syntax
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Input, LoadingIndicator, RichLog, Static
from textual.worker import WorkerState, get_current_worker
from textual.binding import Binding

from ..models import Mode
from ..workflows import query_flow, task_flow
# Note: AppHeader removed from main layout; keep widget file for now

# Maximum input length (10KB)
MAX_INPUT_LENGTH = 10_000


class DirectoryApp(App):
    """Director.y - AI-powered filesystem management TUI."""

    CSS_PATH = "directory.tcss"

    BINDINGS = [
        Binding("tab", "switch_mode", "Switch Mode", priority=True),
        Binding("ctrl+c", "cancel", "Cancel"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("y", "approve_yes", "Approve", show=False),
        Binding("n", "approve_no", "Decline", show=False),
        Binding("escape", "focus_input", "Focus Input", show=False),
    ]

    # Disable default Tab focus cycling
    def action_focus_next(self) -> None:
        """Override default Tab behavior - we use Tab for mode switching."""
        pass

    # Reactive state
    mode: reactive[Mode] = reactive(Mode.QUERY)
    workflow_running: reactive[bool] = reactive(False)
    approval_pending: reactive[bool] = reactive(False)

    def __init__(self, sandbox: Path):
        """
        Initialize the application.

        Args:
            sandbox: Validated sandbox path
        """
        super().__init__()
        self.sandbox = sandbox
        self._approval_event: Event | None = None
        self._approval_result: bool = False

    def compose(self) -> ComposeResult:
        """Build the UI layout."""
        # Main output area (mode indicator + scrollable log)
        with Container(id="main-content"):
            # Mode display moved into main content (replaces top bar)
            mode_icon = "🔍" if self.mode == Mode.QUERY else "⚡"
            yield Static(f"{mode_icon} {self.mode.value} Mode", id="mode-display")
            yield RichLog(id="output", highlight=True, markup=True, wrap=True)

        # Status bar with loading indicator
        with Container(id="status-bar"):
            yield Static("Ready", id="status-text")
            yield LoadingIndicator(id="progress")

        # Input area (visible when not in approval mode)
        with Container(id="input-area"):
            yield Input(
                placeholder="Enter your question...",
                id="user-input"
            )

        # Approval bar (visible only during approval)
        with Horizontal(id="approval-panel", classes="hidden"):
            yield Static("Approve changes?", id="approval-prompt")
            yield Button("Approve (Y)", variant="success", id="approve-yes")
            yield Button("Decline (N)", variant="error", id="approve-no")

    def on_mount(self) -> None:
        """Handle app mount event."""
        # Focus the input field
        self.query_one("#user-input", Input).focus()

        # Hide progress indicator initially
        self.query_one("#progress", LoadingIndicator).display = False

        # Log welcome message
        self.log_message("[bold cyan]Welcome to Director.y![/bold cyan]")
        self.log_message(f"Working directory: {self.sandbox}")
        self.log_message("Press Tab to switch between Query and Task modes.")
        self.log_message("[dim]Tip: Click on the output area to scroll, or hold Shift while selecting to copy text.[/dim]\n")

    # Reactive watchers
    def watch_mode(self, new_mode: Mode) -> None:
        """Update UI when mode changes."""
        try:
            # Update mode display in main content
            mode_display = self.query_one("#mode-display", Static)
            mode_icon = "🔍" if new_mode == Mode.QUERY else "⚡"
            mode_display.update(f"{mode_icon} {new_mode.value} Mode")

            # Update input placeholder
            input_widget = self.query_one("#user-input", Input)
            input_widget.placeholder = (
                "Enter your question..." if new_mode == Mode.QUERY
                else "Describe a task..."
            )
        except Exception:
            # Widget not yet mounted, ignore
            pass

    def watch_workflow_running(self, running: bool) -> None:
        """Update UI when workflow state changes."""
        try:
            # Disable input during workflow
            input_widget = self.query_one("#user-input", Input)
            input_widget.disabled = running

            # Show/hide progress indicator
            progress = self.query_one("#progress", LoadingIndicator)
            progress.display = running
        except Exception:
            # Widget not yet mounted, ignore
            pass

    def watch_approval_pending(self, pending: bool) -> None:
        """Update UI when approval state changes."""
        try:
            approval_panel = self.query_one("#approval-panel")
            input_area = self.query_one("#input-area")

            if pending:
                approval_panel.remove_class("hidden")
                input_area.add_class("hidden")
                # Focus on approve button
                self.query_one("#approve-yes", Button).focus()
            else:
                approval_panel.add_class("hidden")
                input_area.remove_class("hidden")
                # Refocus input
                self.query_one("#user-input", Input).focus()
        except Exception:
            # Widget not yet mounted, ignore
            pass

    # Actions
    def action_switch_mode(self) -> None:
        """Handle Tab key - switch between Query and Task modes."""
        if self.workflow_running or self.approval_pending:
            self.log_message(
                "[yellow]Cannot switch modes during operation[/yellow]"
            )
            return

        # Toggle mode
        self.mode = Mode.TASK if self.mode == Mode.QUERY else Mode.QUERY
        # Mode display is visible in the main content; no log output needed here

    def action_cancel(self) -> None:
        """Handle Ctrl+C - cancel current operation."""
        if not self.workflow_running and not self.approval_pending:
            return

        # Cancel approval if pending
        if self.approval_pending:
            self._approval_result = False
            if self._approval_event:
                self._approval_event.set()
            self.log_message("[yellow]Approval cancelled[/yellow]")
            return

        # Cancel all running workers
        for worker in self.workers:
            if worker.state == WorkerState.RUNNING:
                worker.cancel()

        self.workflow_running = False
        self.update_status("Ready")
        self.log_message("[yellow]Operation cancelled[/yellow]")

    def action_approve_yes(self) -> None:
        """Handle Y key - approve changes (only during approval)."""
        if self.approval_pending:
            self._handle_approval(True)

    def action_approve_no(self) -> None:
        """Handle N key - decline changes (only during approval)."""
        if self.approval_pending:
            self._handle_approval(False)

    def action_focus_input(self) -> None:
        """Handle Escape key - return focus to input."""
        try:
            self.query_one("#user-input", Input).focus()
        except Exception:
            pass

    # Event handlers
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_input = event.value.strip()

        # Handle special commands
        if user_input in ["/quit", "/exit"]:
            self.exit()
            return

        if not user_input:
            return

        # Validate length
        if len(user_input) > MAX_INPUT_LENGTH:
            self.log_error(
                f"Input too long ({len(user_input)} characters). "
                f"Maximum is {MAX_INPUT_LENGTH} characters."
            )
            return

        # Clear input
        event.input.value = ""

        # Log the query/task
        self.log_message(f"\n[bold cyan]> {user_input}[/bold cyan]\n")

        # Route to appropriate workflow
        if self.mode == Mode.QUERY:
            self.run_query_workflow(user_input)
        else:
            self.run_task_workflow(user_input)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "approve-yes":
            self._handle_approval(True)
        elif event.button.id == "approve-no":
            self._handle_approval(False)

    # Worker methods
    def run_query_workflow(self, question: str) -> None:
        """Execute query workflow as a background worker."""
        self.run_worker(self._query_workflow_task(question), exclusive=True)

    async def _query_workflow_task(self, question: str) -> None:
        """Query workflow background task."""
        try:
            self.workflow_running = True

            await query_flow(
                question,
                self.sandbox,
                display=self.log_message,
                display_error=self.log_error,
                display_script=self.show_script,
                update_status=self.update_status,
            )

        except Exception as e:
            self.log_error(f"Unexpected error: {str(e)}")
        finally:
            self.workflow_running = False
            self.update_status("Ready")

    def run_task_workflow(self, task: str) -> None:
        """Execute task workflow as a background worker."""
        self.run_worker(self._task_workflow_task(task), exclusive=True)

    async def _task_workflow_task(self, task: str) -> None:
        """Task workflow background task."""
        try:
            self.workflow_running = True

            await task_flow(
                task,
                self.sandbox,
                display=self.log_message,
                display_error=self.log_error,
                display_script=self.show_script,
                request_approval=self.request_approval,
                update_status=self.update_status,
            )

        except Exception as e:
            self.log_error(f"Unexpected error: {str(e)}")
        finally:
            self.workflow_running = False
            self.update_status("Ready")

    # UI update methods (thread-safe)
    def log_message(self, message: str) -> None:
        """
        Log a message to the output area (thread-safe).

        Args:
            message: Message to log (supports Rich markup)
        """
        def _log():
            log = self.query_one("#output", RichLog)
            log.write(message)

        try:
            worker = get_current_worker()
            # If we're inside a worker, schedule the UI update on the main thread.
            if worker is not None:
                self.call_from_thread(_log)
            else:
                _log()
        except Exception:
            # If detection fails for any reason, fall back to scheduling on main thread
            try:
                self.call_from_thread(_log)
            except Exception:
                _log()

    def log_error(self, message: str) -> None:
        """
        Log an error message (thread-safe).

        Args:
            message: Error message
        """
        # Reuse log_message which handles thread-safety
        self.log_message(f"[bold red]Error:[/bold red] {message}")

    def show_script(self, script: str) -> None:
        """
        Display a PowerShell script with syntax highlighting (thread-safe).

        Args:
            script: PowerShell script to display
        """
        def _show():
            log = self.query_one("#output", RichLog)

            # Create syntax-highlighted panel (responsive width)
            syntax = Syntax(
                script,
                "powershell",
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            )

            panel = Panel(
                syntax,
                title="[cyan]Executing Script[/cyan]",
                border_style="cyan",
            )

            log.write(panel)

        try:
            worker = get_current_worker()
            if worker is not None:
                self.call_from_thread(_show)
            else:
                _show()
        except Exception:
            try:
                self.call_from_thread(_show)
            except Exception:
                _show()

    def update_status(self, status: str) -> None:
        """
        Update the status bar (thread-safe).

        Args:
            status: Status message
        """
        def _update():
            self.query_one("#status-text", Static).update(status)

        try:
            worker = get_current_worker()
            if worker is not None:
                self.call_from_thread(_update)
            else:
                _update()
        except Exception:
            try:
                self.call_from_thread(_update)
            except Exception:
                _update()

    # Approval flow
    async def request_approval(self, explanation: str, script: str) -> bool:
        """
        Request user approval for changes (async).

        Args:
            explanation: What will change
            script: The PowerShell script to execute

        Returns:
            True if approved, False otherwise
        """
        # Create event for synchronization
        self._approval_event = Event()
        self._approval_result = False

        # Show approval panel - since we're in an async method on the main event loop,
        # we can call UI methods directly
        self._show_approval_panel(explanation, script)

        # Wait for user response (in executor to not block worker thread)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._approval_event.wait)

        # Hide approval panel
        self._hide_approval_panel()

        return self._approval_result

    def _show_approval_panel(self, explanation: str, script: str) -> None:
        """Show the approval panel with explanation and script."""
        # Log the proposed changes to the output panel
        log = self.query_one("#output", RichLog)

        # Display explanation
        from rich.text import Text
        explanation_text = Text(explanation, style="bold yellow")
        explanation_text.no_wrap = False
        log.write(Panel(
            explanation_text,
            title="[yellow]Proposed Changes[/yellow]",
            border_style="yellow",
        ))

        # Display script with syntax highlighting (responsive width)
        syntax = Syntax(
            script,
            "powershell",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        log.write(Panel(
            syntax,
            title="[yellow]Script to Execute[/yellow]",
            border_style="yellow",
        ))

        log.write("\n[bold yellow]→ Approve these changes? (Y/N)[/bold yellow]\n")

        # Show approval buttons
        self.approval_pending = True

    def _hide_approval_panel(self) -> None:
        """Hide the approval panel."""
        self.approval_pending = False

    def _handle_approval(self, approved: bool) -> None:
        """Handle approval decision."""
        self._approval_result = approved
        if self._approval_event:
            self._approval_event.set()

        if approved:
            self.log_message("[green]Changes approved[/green]")
        else:
            self.log_message("[yellow]Changes declined[/yellow]")

