"""Simple statistics over a piece of text."""


def word_count(text: str) -> int:
    """Return the number of whitespace-separated words in ``text``."""
    return len(text.split())
