"""Utilities for sanitizing user-facing identity and credential fields."""

import re


_WHITESPACE_PATTERN = re.compile(r"\s+")


class UserInputSanitizer:
    """Normalize user input fields that must never contain spaces."""

    @staticmethod
    def remove_all_spaces(value: str | None) -> str:
        """Remove all whitespace characters from a value."""
        return _WHITESPACE_PATTERN.sub("", str(value or ""))

