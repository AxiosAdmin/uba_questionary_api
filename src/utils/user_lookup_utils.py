"""Utilities for deterministic user lookup hashes."""

from hashlib import sha256


class UserLookupUtils:
    """Helper methods for normalizing and hashing lookup fields."""

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize an email for uniqueness and lookup."""
        return str(email or "").strip().casefold()

    @staticmethod
    def normalize_nickname(nickname: str) -> str:
        """Normalize a nickname while preserving current case-sensitive behavior."""
        return str(nickname or "")

    @staticmethod
    def _hash_value(value: str) -> str:
        return sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_email(email: str) -> str:
        """Hash a normalized email."""
        return UserLookupUtils._hash_value(UserLookupUtils.normalize_email(email))

    @staticmethod
    def hash_nickname(nickname: str) -> str:
        """Hash a normalized nickname."""
        return UserLookupUtils._hash_value(
            UserLookupUtils.normalize_nickname(nickname)
        )
