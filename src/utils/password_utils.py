"""Utilities for validating password strength requirements."""

import re


PASSWORD_REQUIREMENTS_MESSAGE = (
    "Password must be at least 8 characters long and contain at least one "
    "uppercase letter, one lowercase letter, one number, and one special character"
)


def validate_password_requirements(password: str) -> None:
    """Validate whether a plaintext password satisfies the project requirements."""
    has_min_length = len(password) >= 8
    has_uppercase = bool(re.search(r"[A-Z]", password))
    has_lowercase = bool(re.search(r"[a-z]", password))
    has_number = bool(re.search(r"\d", password))
    has_special_character = bool(re.search(r"[^A-Za-z0-9]", password))

    if not all(
        [
            has_min_length,
            has_uppercase,
            has_lowercase,
            has_number,
            has_special_character,
        ]
    ):
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
