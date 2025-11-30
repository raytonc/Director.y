"""Text content loading utilities."""

from pathlib import Path


def load_text(name: str) -> str:
    """
    Load text content from a file.

    Args:
        name: Name of the text file (without .txt extension)

    Returns:
        Content of the text file

    Raises:
        FileNotFoundError: If text file doesn't exist
    """
    text_dir = Path(__file__).parent
    text_file = text_dir / f"{name}.txt"

    if not text_file.exists():
        raise FileNotFoundError(f"Text file not found: {text_file}")

    return text_file.read_text(encoding="utf-8")
