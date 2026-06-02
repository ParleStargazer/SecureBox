"""Command-line entry point for SecureBox."""

from securebox.ui.app import run_app


def main() -> None:
    """Start the local Flet application."""
    run_app()


if __name__ == "__main__":
    main()

