"""The guitar string as a physical model."""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.errors import InvalidPositionError, InvalidTuningError
from guitar_app.core.theory.pitch import Pitch, PitchClass


@dataclass(frozen=True, slots=True)
class GuitarString:
    """A single string defined by its open-string pitch.

    ``number`` follows the conventional guitar numbering: 1 is the highest
    (thinnest) string and 6 is the lowest. The number is an identifier for a
    tuning, not an ordering; a tuning may order its strings however it likes.

    The physical model is ``pitch at fret = open pitch + fret semitones``.
    """

    number: int
    open_pitch: Pitch

    def __post_init__(self) -> None:
        if self.number < 1:
            raise InvalidTuningError(f"string number must be >= 1, got {self.number}")

    def pitch_at(self, fret: int) -> Pitch:
        """Return the pitch of this string at ``fret`` (0 = open string)."""
        if fret < 0:
            raise InvalidPositionError(f"fret must be >= 0, got {fret}")
        return self.open_pitch.transpose(fret)

    def pitch_class_at(self, fret: int) -> PitchClass:
        """Return the pitch class of this string at ``fret``."""
        return self.pitch_at(fret).pitch_class
