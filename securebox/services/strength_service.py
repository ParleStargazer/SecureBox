"""Password strength evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from zxcvbn import zxcvbn


@dataclass(frozen=True)
class PasswordStrength:
    score: int
    label: str
    guesses: int
    warning: str
    suggestions: tuple[str, ...]


STRENGTH_LABELS = {
    0: "very weak",
    1: "weak",
    2: "fair",
    3: "strong",
    4: "very strong",
}


def analyze_password(password: str, user_inputs: list[str] | None = None) -> PasswordStrength:
    result = zxcvbn(password, user_inputs=user_inputs or [])
    score = int(result["score"])
    feedback = result.get("feedback", {})
    return PasswordStrength(
        score=score,
        label=STRENGTH_LABELS.get(score, "unknown"),
        guesses=int(result.get("guesses", 0)),
        warning=feedback.get("warning", ""),
        suggestions=tuple(feedback.get("suggestions", [])),
    )

