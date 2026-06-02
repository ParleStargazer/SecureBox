import pytest

from securebox.services.password_generator import (
    DIGITS,
    LOWERCASE,
    SYMBOLS,
    UPPERCASE,
    PasswordGeneratorOptions,
    estimate_entropy_bits,
    generate_password,
)
from securebox.services.strength_service import analyze_password


def test_generator_default_password_contains_all_groups() -> None:
    password = generate_password()

    assert len(password) == 20
    assert any(char in LOWERCASE for char in password)
    assert any(char in UPPERCASE for char in password)
    assert any(char in DIGITS for char in password)
    assert any(char in SYMBOLS for char in password)


def test_generator_respects_disabled_character_groups() -> None:
    password = generate_password(
        PasswordGeneratorOptions(
            length=12,
            use_lowercase=True,
            use_uppercase=False,
            use_digits=True,
            use_symbols=False,
        )
    )

    assert set(password).issubset(set(LOWERCASE + DIGITS))
    assert any(char in LOWERCASE for char in password)
    assert any(char in DIGITS for char in password)


def test_generator_produces_different_values() -> None:
    generated = {generate_password() for _ in range(8)}

    assert len(generated) > 1


def test_generator_rejects_invalid_options() -> None:
    with pytest.raises(ValueError):
        generate_password(
            PasswordGeneratorOptions(
                length=8,
                use_lowercase=False,
                use_uppercase=False,
                use_digits=False,
                use_symbols=False,
            )
        )

    with pytest.raises(ValueError):
        generate_password(PasswordGeneratorOptions(length=2))


def test_entropy_estimate_increases_with_length() -> None:
    short = estimate_entropy_bits(PasswordGeneratorOptions(length=8))
    long = estimate_entropy_bits(PasswordGeneratorOptions(length=20))

    assert long > short


def test_strength_service_scores_weak_and_strong_passwords() -> None:
    weak = analyze_password("123456")
    strong = analyze_password("correct-horse-battery-staple-2026!")

    assert weak.score <= 1
    assert strong.score >= 3

