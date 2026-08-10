"""Tunings: ordered collections of guitar strings, including presets."""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.errors import InvalidTuningError
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.theory.pitch import Pitch, PitchClass


def _standard_strings() -> tuple[GuitarString, ...]:
    """The six strings of standard EADGBE tuning, ordered low to high."""
    return (
        GuitarString(6, Pitch(PitchClass.E, 2)),
        GuitarString(5, Pitch(PitchClass.A, 2)),
        GuitarString(4, Pitch(PitchClass.D, 3)),
        GuitarString(3, Pitch(PitchClass.G, 3)),
        GuitarString(2, Pitch(PitchClass.B, 3)),
        GuitarString(1, Pitch(PitchClass.E, 4)),
    )


@dataclass(frozen=True, slots=True)
class Tuning:
    """An immutable collection of guitar strings for one instrument setup.

    Strings are stored in the order they were given; for the standard preset
    this is low to high (string 6 down to string 1). String numbers must be
    unique and positive.
    """

    name: str
    strings: tuple[GuitarString, ...]

    def __post_init__(self) -> None:
        if not self.strings:
            raise InvalidTuningError("a tuning must define at least one string")
        numbers = [string.number for string in self.strings]
        if len(set(numbers)) != len(numbers):
            raise InvalidTuningError(f"string numbers must be unique, got {numbers}")
        if min(numbers) < 1:
            raise InvalidTuningError(f"string numbers must be >= 1, got {numbers}")

    @property
    def string_count(self) -> int:
        """Number of strings in the tuning."""
        return len(self.strings)

    def string(self, number: int) -> GuitarString:
        """Look up a string by its guitar string number."""
        for string in self.strings:
            if string.number == number:
                return string
        raise InvalidTuningError(f"no string numbered {number} in tuning {self.name!r}")


#: Standard six-string EADGBE tuning.
STANDARD = Tuning("Standard (EADGBE)", _standard_strings())
