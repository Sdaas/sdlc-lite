import pytest

from roman_numeral.greet import greet


def test_greet_returns_greeting() -> None:
    assert greet("Ada") == "Hello, Ada!"


def test_greet_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        greet("")


def test_greet_rejects_whitespace_only_name() -> None:
    with pytest.raises(ValueError):
        greet("   ")
