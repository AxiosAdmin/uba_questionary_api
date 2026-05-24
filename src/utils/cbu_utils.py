"""Utilities for validating and hashing Argentine CBU identifiers."""

from hashlib import sha256


class CbuUtils:
    """Helper methods for normalizing, validating, and hashing CBU values."""

    _BLOCK_ONE_WEIGHTS = (7, 1, 3, 9, 7, 1, 3)
    _BLOCK_TWO_WEIGHTS = (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3)

    @staticmethod
    def normalize(value: str) -> str:
        """Return only the digits from a CBU input."""
        return "".join(character for character in str(value or "") if character.isdigit())

    @staticmethod
    def _calculate_check_digit(base_digits: str, weights: tuple[int, ...]) -> int:
        weighted_sum = sum(
            int(digit) * weight for digit, weight in zip(base_digits, weights)
        )
        modulo = weighted_sum % 10
        return 0 if modulo == 0 else 10 - modulo

    @staticmethod
    def normalize_and_validate(value: str) -> str:
        """Normalize a CBU and ensure it is structurally valid."""
        normalized_value = CbuUtils.normalize(value)
        if len(normalized_value) != 22 or not normalized_value.isdigit():
            raise ValueError("CBU must contain exactly 22 digits.")

        if normalized_value[:3] == "000":
            raise ValueError("CBU bank code is invalid.")

        expected_first_digit = CbuUtils._calculate_check_digit(
            normalized_value[:7], CbuUtils._BLOCK_ONE_WEIGHTS
        )
        if expected_first_digit != int(normalized_value[7]):
            raise ValueError("CBU first block verification digit is invalid.")

        expected_second_digit = CbuUtils._calculate_check_digit(
            normalized_value[8:21], CbuUtils._BLOCK_TWO_WEIGHTS
        )
        if expected_second_digit != int(normalized_value[21]):
            raise ValueError("CBU second block verification digit is invalid.")

        return normalized_value

    @staticmethod
    def hash_normalized(value: str) -> str:
        """Hash a normalized CBU for database uniqueness checks."""
        return sha256(value.encode("utf-8")).hexdigest()
