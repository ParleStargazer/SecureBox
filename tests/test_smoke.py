from securebox import __version__
from securebox.config import APP_NAME, CRYPTO_VERSION


def test_package_metadata() -> None:
    assert __version__ == "0.1.0"
    assert APP_NAME == "SecureBox"
    assert CRYPTO_VERSION == 1

