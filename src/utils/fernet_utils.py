from cryptography.fernet import Fernet

from src.configs.configs import settings


class FernetUtils:
    """Utility class for encrypting and decrypting strings using Fernet symmetric encryption."""

    def __init__(self, key: bytes | None = None):
        """
        Initialize FernetUtils with an optional key.

        If no key is provided, a new one will be generated.

        Args:
            key: A 32-byte URL-safe base64-encoded key for Fernet encryption.
        """
        if key is None:
            self.key = settings.FERNET_KEY.encode()
        else:
            self.key = key
        self.fernet = Fernet(self.key)

    def encrypt(self, text: str) -> str:
        """
        Encrypt a string using Fernet symmetric encryption.

        Args:
            text: The plain text string to encrypt.

        Returns:
            The encrypted text as a UTF-8 string.
        """
        encrypted_bytes = self.fernet.encrypt(text.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt a string that was encrypted using Fernet.

        Args:
            encrypted_text: The encrypted text to decrypt.

        Returns:
            The decrypted plain text string.
        """
        decrypted_bytes = self.fernet.decrypt(encrypted_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
