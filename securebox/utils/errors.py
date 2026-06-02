"""Application exception types."""


class SecureBoxError(Exception):
    """Base class for SecureBox errors."""


class AuthenticationFailedError(SecureBoxError):
    """Raised when authenticated decryption or password verification fails."""


class VaultAlreadyInitializedError(SecureBoxError):
    """Raised when initialization is attempted on an existing vault."""


class VaultNotInitializedError(SecureBoxError):
    """Raised when login is attempted before vault initialization."""


class EntryNotFoundError(SecureBoxError):
    """Raised when a password entry does not exist."""


class UnsupportedCryptoVersionError(SecureBoxError):
    """Raised when encrypted data uses an unsupported crypto version."""
