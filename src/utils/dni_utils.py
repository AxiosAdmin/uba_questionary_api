"""Utilities for validating and hashing Argentine DNI identifiers."""

import hashlib


class DniUtils:
    """Helper methods for normalizing, validating, and hashing DNI values."""

    @staticmethod
    def normalize(value: str) -> str:
        """Return only the digits from a DNI input."""
        if value is None:
            return ""

        return "".join(character for character in str(value) if character.isdigit())

    @staticmethod
    def normalize_and_validate(value: str) -> str:
        """Normalize a DNI and ensure it is structurally valid."""
        normalized_value = DniUtils.normalize(value)

        if len(normalized_value) not in {7, 8}:
            raise ValueError("DNI must contain 7 or 8 digits.")

        if normalized_value == "0" * len(normalized_value):
            raise ValueError("DNI is invalid.")

        return normalized_value

    @staticmethod
    def hash_normalized(normalized_value: str) -> str:
        """Hash a normalized DNI for database uniqueness checks."""
        return hashlib.sha256(normalized_value.encode("utf-8")).hexdigest()
