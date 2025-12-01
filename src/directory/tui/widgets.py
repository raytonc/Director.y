"""Custom Textual widgets for Director.y."""

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, Tree

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
            "Tab: Switch Mode | Ctrl+C: Cancel | Ctrl+Q: Quit | Type 'help' for commands",
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


class DirectoryTreeWidget(Container):
    """
    Directory tree sidebar widget.

    Displays a hierarchical view of the current directory structure
    with automatic refresh after workflow operations.
    """

    DEFAULT_CSS = """
    DirectoryTreeWidget {
        height: 100%;
        layout: vertical;
    }

    DirectoryTreeWidget #tree-header {
        height: 1;
        background: $panel;
        content-align: center middle;
        text-style: bold;
        color: $text;
        border-bottom: solid $primary;
    }

    DirectoryTreeWidget Tree {
        width: 100%;
        height: 1fr;
        scrollbar-gutter: stable;
        background: $panel;
        padding: 0 1;
    }
    """

    def __init__(self, sandbox: Path) -> None:
        """
        Initialize the directory tree widget.

        Args:
            sandbox: Directory to display
        """
        super().__init__(id="directory-tree")
        self.sandbox = sandbox
        self._refreshing = False
        self._tree_script = self._build_tree_script()

    def compose(self) -> ComposeResult:
        """Build the widget layout."""
        yield Static("📂 Directory Tree", id="tree-header")
        yield Tree(str(self.sandbox.name), id="dir-tree")

    def on_mount(self) -> None:
        """Handle widget mount - initial tree load."""
        self.refresh_tree(self.sandbox)

    def _build_tree_script(self) -> str:
        """Build the PowerShell script for directory tree."""
        return """
$rootPath = Get-Location
$maxDepth = 2

function Get-DirectoryTree {
    param(
        [string]$Path,
        [int]$CurrentDepth,
        [int]$MaxDepth
    )

    if ($CurrentDepth -gt $MaxDepth) {
        return $null
    }

    try {
        $items = Get-ChildItem -Path $Path -Force -ErrorAction SilentlyContinue |
                 Sort-Object { -not $_.PSIsContainer }, Name

        $result = @()

        foreach ($item in $items) {
            $obj = @{
                name = $item.Name
                path = $item.FullName
                is_dir = $item.PSIsContainer
                children = @()
            }

            if ($item.PSIsContainer -and $CurrentDepth -lt $MaxDepth) {
                $children = Get-DirectoryTree -Path $item.FullName `
                    -CurrentDepth ($CurrentDepth + 1) -MaxDepth $MaxDepth
                if ($children) {
                    $obj.children = $children
                }
            }

            $result += $obj
        }

        return $result
    }
    catch {
        return @()
    }
}

$tree = Get-DirectoryTree -Path $rootPath -CurrentDepth 0 -MaxDepth $maxDepth
$output = @{
    root = $rootPath.Path
    items = $tree
}

$output | ConvertTo-Json -Depth 10 -Compress
"""

    def refresh_tree(self, sandbox: Path) -> None:
        """
        Refresh the directory tree.

        Args:
            sandbox: Directory to scan
        """
        # Skip if already refreshing
        if self._refreshing:
            return

        self._refreshing = True
        try:
            from ..execution import execute_script

            tree = self.query_one("#dir-tree", Tree)

            # Execute PowerShell script to get directory structure
            result = execute_script(self._tree_script, timeout=10, cwd=sandbox)

            if not result.success:
                self._show_error(tree, f"Failed: {result.stderr[:50]}")
                return

            # Parse JSON output
            try:
                tree_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                self._show_error(tree, "Invalid JSON from script")
                return

            # Build tree structure
            self._build_tree(tree, tree_data)
        finally:
            self._refreshing = False

    def _build_tree(self, tree: Tree, data: dict) -> None:
        """
        Build tree structure from parsed data.

        Args:
            tree: Tree widget to populate
            data: Parsed directory data
        """
        # Clear existing tree
        tree.clear()
        tree.root.label = f"📂 {Path(data['root']).name}"

        # Add items to root
        items = data.get("items", [])

        # PowerShell ConvertTo-Json returns a dict instead of list for single items
        if isinstance(items, dict):
            items = [items]

        if not items:
            tree.root.add_leaf("(empty)")
            return

        self._add_nodes(tree.root, items, depth=0)

    def _add_nodes(self, parent_node, items: list, depth: int) -> None:
        """
        Recursively add nodes to tree.

        Args:
            parent_node: Parent tree node
            items: List of item dictionaries
            depth: Current depth level
        """
        for item in items:
            # Skip hidden files starting with . except whitelisted ones
            if item["name"].startswith(".") and item["name"] not in [".git", ".github"]:
                continue

            # Create label with icon
            icon = "📁" if item["is_dir"] else "📄"
            label = f"{icon} {item['name']}"

            # Store path as node data
            node_data = {
                "path": Path(item["path"]),
                "is_dir": item["is_dir"],
                "depth": depth
            }

            # Add directory with children or leaf
            children = item.get("children", [])

            # PowerShell ConvertTo-Json returns a dict instead of list for single items
            if isinstance(children, dict):
                children = [children]

            if item["is_dir"] and children:
                node = parent_node.add(label, data=node_data)
                # Don't auto-expand - start collapsed
                self._add_nodes(node, children, depth + 1)
            else:
                parent_node.add_leaf(label, data=node_data)

    def _show_error(self, tree: Tree, message: str) -> None:
        """
        Show error message in tree.

        Args:
            tree: Tree widget
            message: Error message to display
        """
        tree.clear()
        tree.root.label = "⚠️ Error"
        tree.root.expand()
        tree.root.add_leaf(message)
