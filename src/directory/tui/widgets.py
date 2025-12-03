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

    def compose(self) -> ComposeResult:
        """Build the widget layout."""
        yield Static("📂 Directory Tree", id="tree-header")
        yield Tree(str(self.sandbox.name), id="dir-tree")

    def on_mount(self) -> None:
        """Handle widget mount - initial tree load."""
        self.refresh_tree(self.sandbox)

    def _build_tree_script(self, target_path: str = None) -> str:
        """
        Build the PowerShell script for directory tree.

        Args:
            target_path: Specific path to load children for (if None, uses current directory)

        Returns:
            PowerShell script as string
        """
        if target_path:
            return f"""
$targetPath = "{target_path}"

try {{
    $items = Get-ChildItem -Path $targetPath -Force -ErrorAction SilentlyContinue |
             Sort-Object {{ -not $_.PSIsContainer }}, Name

    $result = @()

    foreach ($item in $items) {{
        $obj = @{{
            name = $item.Name
            path = $item.FullName
            is_dir = $item.PSIsContainer
        }}

        $result += $obj
    }}

    $output = @{{
        root = $targetPath
        items = $result
    }}

    $output | ConvertTo-Json -Depth 3 -Compress
}}
catch {{
    $output = @{{
        root = $targetPath
        items = @()
    }}
    $output | ConvertTo-Json -Depth 3 -Compress
}}
"""
        else:
            return """
$targetPath = Get-Location

try {
    $items = Get-ChildItem -Path $targetPath -Force -ErrorAction SilentlyContinue |
             Sort-Object { -not $_.PSIsContainer }, Name

    $result = @()

    foreach ($item in $items) {
        $obj = @{
            name = $item.Name
            path = $item.FullName
            is_dir = $item.PSIsContainer
        }

        $result += $obj
    }

    $output = @{
        root = $targetPath.Path
        items = $result
    }

    $output | ConvertTo-Json -Depth 3 -Compress
}
catch {
    $output = @{
        root = $targetPath.Path
        items = @()
    }
    $output | ConvertTo-Json -Depth 3 -Compress
}
"""

    def _get_expanded_paths(self, tree: Tree) -> set[Path]:
        """
        Get all currently expanded directory paths.

        Args:
            tree: Tree widget

        Returns:
            Set of expanded directory paths
        """
        expanded_paths = set()

        def collect_expanded(node):
            """Recursively collect expanded node paths."""
            if node.data and isinstance(node.data, dict):
                if node.is_expanded and node.data.get("is_dir"):
                    expanded_paths.add(node.data["path"])

            for child in node.children:
                collect_expanded(child)

        collect_expanded(tree.root)
        return expanded_paths

    def _restore_expanded_state(self, tree: Tree, expanded_paths: set[Path]) -> None:
        """
        Restore previously expanded nodes.

        Args:
            tree: Tree widget
            expanded_paths: Set of paths that should be expanded
        """
        def restore_node(node):
            """Recursively restore expanded state."""
            if node.data and isinstance(node.data, dict):
                if node.data.get("path") in expanded_paths:
                    node.expand()

            for child in node.children:
                restore_node(child)

        restore_node(tree.root)

    def _reload_expanded_paths(self, tree: Tree, expanded_paths: set[Path]) -> None:
        """
        Reload children for previously expanded paths.

        Args:
            tree: Tree widget
            expanded_paths: Set of paths that were expanded
        """
        def reload_node(node):
            """Recursively reload expanded nodes."""
            if node.data and isinstance(node.data, dict):
                node_path = node.data.get("path")
                if node_path in expanded_paths and node.data.get("is_dir"):
                    # Load children for this node
                    self._load_children(node)
                    node.expand()

            for child in node.children:
                reload_node(child)

        reload_node(tree.root)

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

            # Preserve expanded paths before refresh
            expanded_paths = self._get_expanded_paths(tree)

            # Execute PowerShell script to get root directory structure
            script = self._build_tree_script(str(sandbox))
            result = execute_script(script, timeout=10, cwd=sandbox)

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

            # Restore expanded state by loading children for expanded paths
            self._reload_expanded_paths(tree, expanded_paths)
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
        # But empty dict means no items
        if isinstance(items, dict):
            if items:  # Only convert non-empty dicts to list
                items = [items]
            else:
                items = []

        if not items:
            tree.root.add_leaf("(empty)")
            return

        self._add_nodes(tree.root, items, depth=0)

    def _add_nodes(self, parent_node, items: list, depth: int) -> None:
        """
        Add nodes to tree without pre-loading children.

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
                "depth": depth,
                "children_loaded": False
            }

            # Add directory as expandable node (but don't load children yet)
            # Or add file as leaf
            if item["is_dir"]:
                node = parent_node.add(label, data=node_data, allow_expand=True)
                # Add placeholder to make it expandable
                node.add_leaf("Loading...")
            else:
                parent_node.add_leaf(label, data=node_data)

    def _load_children(self, node) -> None:
        """
        Load children for a directory node.

        Args:
            node: Tree node to load children for
        """
        if not node.data or not node.data.get("is_dir"):
            return

        # Skip if already loaded
        if node.data.get("children_loaded"):
            return

        from ..execution import execute_script

        # Get path for this node
        node_path = node.data["path"]

        # Execute PowerShell script to get children
        script = self._build_tree_script(str(node_path))
        result = execute_script(script, timeout=5, cwd=self.sandbox)

        if not result.success:
            # Remove placeholder and show error
            node.remove_children()
            node.add_leaf("(error loading)")
            return

        # Parse JSON output
        try:
            tree_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            node.remove_children()
            node.add_leaf("(error parsing)")
            return

        # Remove placeholder
        node.remove_children()

        items = tree_data.get("items", [])

        # PowerShell ConvertTo-Json returns a dict instead of list for single items
        if isinstance(items, dict):
            if items:
                items = [items]
            else:
                items = []

        if not items:
            node.add_leaf("(empty)")
        else:
            # Add children nodes
            self._add_nodes(node, items, node.data["depth"] + 1)

        # Mark as loaded
        node.data["children_loaded"] = True

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """
        Handle tree node expansion - lazy load children.

        Args:
            event: Node expanded event
        """
        node = event.node

        # Load children if not already loaded
        if node.data and node.data.get("is_dir"):
            if not node.data.get("children_loaded"):
                self._load_children(node)

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
