"""Secure random password generation."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordGeneratorOptions:
    length: int = 20
    use_lowercase: bool = True
    use_uppercase: bool = True
    use_digits: bool = True
    use_symbols: bool = True


LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/|"


def generate_password(options: PasswordGeneratorOptions | None = None) -> str:
    opts = options or PasswordGeneratorOptions()
    groups = _selected_groups(opts)
    if not groups:
        raise ValueError("At least one character group must be selected")
    if opts.length < len(groups):
        raise ValueError("Password length must fit all selected character groups")

    password_chars = [secrets.choice(group) for group in groups]
    alphabet = "".join(groups)
    password_chars.extend(secrets.choice(alphabet) for _ in range(opts.length - len(groups)))
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def estimate_entropy_bits(options: PasswordGeneratorOptions | None = None) -> float:
    opts = options or PasswordGeneratorOptions()
    alphabet_size = sum(len(group) for group in _selected_groups(opts))
    if alphabet_size == 0:
        return 0.0
    return opts.length * _log2(alphabet_size)


def _selected_groups(options: PasswordGeneratorOptions) -> list[str]:
    groups = []
    if options.use_lowercase:
        groups.append(LOWERCASE)
    if options.use_uppercase:
        groups.append(UPPERCASE)
    if options.use_digits:
        groups.append(DIGITS)
    if options.use_symbols:
        groups.append(SYMBOLS)
    return groups


def _log2(value: int) -> float:
    return value.bit_length() - 1 + ((value / (1 << (value.bit_length() - 1))) - 1) * 0.7213

