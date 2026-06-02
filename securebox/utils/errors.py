"""Application exception types."""


class SecureBoxError(Exception):
    """Base class for SecureBox errors."""


class AuthenticationFailedError(SecureBoxError):
    """Raised when authenticated decryption or password verification fails."""


class UnsupportedCryptoVersionError(SecureBoxError):
    """Raised when encrypted data uses an unsupported crypto version."""

