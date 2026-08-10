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

    A valid tuning must contain exactly the string numbers ``1..N`` where ``N``
    is the number of strings. The stored tuple order is not required to be
    ascending: guitar display order may intentionally remain low to high (e.g.
    ``6, 5, 4, 3, 2, 1``), but the set of string numbers must equal
    ``set(range(1, N + 1))``.
    """

    name: str
    strings: tuple[GuitarString, ...]

    def __post_init__(self) -> None:
        count = len(self.strings)
        if count == 0:
            raise InvalidTuningError("a tuning must define at least one string")
        numbers = [string.number for string in self.strings]
        if set(numbers) != set(range(1, count + 1)):
            raise InvalidTuningError(
                f"string numbers must be exactly 1..{count}, got {sorted(numbers)}"
            )

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
