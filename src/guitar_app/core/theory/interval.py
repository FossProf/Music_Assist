"""Intervals measured in semitones and pitch-class interval helpers."""

from __future__ import annotations

from enum import IntEnum

from guitar_app.core.theory.pitch import PitchClass

# Canonical abbreviations for the twelve pitch-class intervals plus the octave.
# Used for compact display; the values are also the label vocabulary the UI
# layer may consume (rendering decisions stay in the UI).
_ABBREVIATIONS: dict[int, str] = {
    0: "R",
    1: "b2",
    2: "2",
    3: "b3",
    4: "3",
    5: "4",
    6: "b5",
    7: "5",
    8: "b6",
    9: "6",
    10: "b7",
    11: "7",
    12: "8",
}


class Interval(IntEnum):
    """A named interval up to one octave, in semitones.

    The enum value is the semitone count. Compound intervals (larger than an
    octave) are not modeled yet; a perfect twelfth can be expressed as an
    octave plus a fifth.
    """

    UNISON = 0
    MINOR_SECOND = 1
    MAJOR_SECOND = 2
    MINOR_THIRD = 3
    MAJOR_THIRD = 4
    PERFECT_FOURTH = 5
    TRITONE = 6
    PERFECT_FIFTH = 7
    MINOR_SIXTH = 8
    MAJOR_SIXTH = 9
    MINOR_SEVENTH = 10
    MAJOR_SEVENTH = 11
    OCTAVE = 12

    @property
    def semitones(self) -> int:
        """The interval size in semitones."""
        return int(self)

    @property
    def abbreviation(self) -> str:
        """Compact label such as ``"P5"`` for a perfect fifth.

        Uses the ``R`` shorthand for the unison/root.
        """
        return _ABBREVIATIONS[int(self)]


def interval_between(source: PitchClass, target: PitchClass) -> Interval:
    """Return the ascending pitch-class interval from ``source`` to ``target``.

    The result is the shortest pitch-class distance, always in 0..11 semitones
    (unison through major seventh). For example, from ``E`` to ``A`` is a
    perfect fourth and from ``A`` to ``E`` is a perfect fifth.
    """
    return Interval((int(target) - int(source)) % 12)
