"""Pitch classes and pitches (pitch class + octave)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from guitar_app.core.errors import InvalidPitchError

# Natural note letters map to their semitone offset above C.
_NATURALS: dict[str, int] = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

# Accepted accidental spellings. Enharmonically equivalent input is normalized
# to a single internal representation; context-aware spelling comes later.
_ACCIDENTALS: dict[str, int] = {
    "": 0,
    "#": 1,
    "♯": 1,
    "b": -1,
    "♭": -1,
}

# Canonical display spelling for each pitch class (sharp-based).
_SPELLINGS: dict[int, str] = {
    0: "C",
    1: "C#",
    2: "D",
    3: "D#",
    4: "E",
    5: "F",
    6: "F#",
    7: "G",
    8: "G#",
    9: "A",
    10: "A#",
    11: "B",
}


class PitchClass(IntEnum):
    """A pitch class, internally normalized to a 0..11 semitone offset from C.

    Enharmonically equivalent spellings (e.g. ``C#`` and ``Db``) map to the
    same member. The enum value is the pitch-class number; this is the
    normalized representation used for all internal calculations.
    """

    C = 0
    CSHARP = 1
    D = 2
    DSHARP = 3
    E = 4
    F = 5
    FSHARP = 6
    G = 7
    GSHARP = 8
    A = 9
    ASHARP = 10
    B = 11

    @classmethod
    def from_name(cls, name: str) -> PitchClass:
        """Parse a note name such as ``"F#"``, ``"Gb"``, or ``"A"``.

        Accepts ``#``, ``♯``, ``b``, and ``♭`` accidentals and case-variants.
        Raises :class:`InvalidPitchError` for unrecognized input.
        """
        if not isinstance(name, str) or not name.strip():
            raise InvalidPitchError(f"empty pitch class name: {name!r}")
        text = name.strip()
        letter = text[0].upper()
        if letter not in _NATURALS:
            raise InvalidPitchError(f"not a valid note name: {name!r}")
        accidental = text[1:].lower()
        if accidental not in _ACCIDENTALS:
            raise InvalidPitchError(f"not a valid note name: {name!r}")
        semitones = _NATURALS[letter] + _ACCIDENTALS[accidental]
        return cls(semitones % 12)

    def spelling(self) -> str:
        """Return the canonical sharp-based spelling, e.g. ``"C#"``."""
        return _SPELLINGS[int(self)]


@dataclass(frozen=True, slots=True)
class Pitch:
    """A specific pitch: a pitch class plus a scientific-pitch octave number.

    The octave follows scientific pitch notation (middle C is ``Pitch(C, 4)``).
    The ``midi`` property is the MIDI note number, where ``midi =
    12 * (octave + 1) + pitch_class`` and ``Pitch(C, 4).midi == 60``. Under this
    convention the standard guitar's low E is ``Pitch(E, 2)`` (MIDI 40).
    """

    pitch_class: PitchClass
    octave: int

    @classmethod
    def from_midi(cls, midi: int) -> Pitch:
        """Construct a pitch from a MIDI note number."""
        return cls(PitchClass(midi % 12), midi // 12 - 1)

    @property
    def midi(self) -> int:
        """MIDI note number; see the class docstring for the convention."""
        return 12 * (self.octave + 1) + int(self.pitch_class)

    def transpose(self, semitones: int) -> Pitch:
        """Return a new pitch shifted by ``semitones`` (may be negative)."""
        return Pitch.from_midi(self.midi + semitones)

    def __str__(self) -> str:
        return f"{self.pitch_class.spelling()}{self.octave}"
