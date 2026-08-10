"""The fretboard: a tunable grid of strings and frets with pitch lookups.

This module models only musical structure. It returns domain data (pitches,
pitch classes, intervals, locations) and never rendering instructions.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from guitar_app.core.errors import InvalidPositionError
from guitar_app.core.instrument.tuning import Tuning
from guitar_app.core.theory.chromatic_interval import (
    ChromaticInterval,
    chromatic_interval_between,
)
from guitar_app.core.theory.pitch import Pitch, PitchClass


@dataclass(frozen=True, slots=True)
class FretPosition:
    """A pure location on the fretboard: a string number and a fret number."""

    string_number: int
    fret: int


@dataclass(frozen=True, slots=True)
class FretboardPosition:
    """A fretboard location enriched with the pitch sounding there.

    ``interval_from_root`` is the chromatic displacement (0..11 semitones) from
    a chosen root, or ``None`` when no root was supplied. It encodes distance
    only, not theoretical interval spelling.
    """

    string_number: int
    fret: int
    pitch: Pitch
    interval_from_root: ChromaticInterval | None = None

    @property
    def pitch_class(self) -> PitchClass:
        """The pitch class sounding at this position."""
        return self.pitch.pitch_class


@dataclass(frozen=True, slots=True)
class Fretboard:
    """A fretboard: a tuning plus a number of frets.

    ``fret_count`` is the highest playable fret (12 means frets 0 through 12).
    Positions range over every string and frets 0..``fret_count``.
    """

    tuning: Tuning
    fret_count: int

    def __post_init__(self) -> None:
        if self.fret_count < 0:
            raise InvalidPositionError(f"fret count must be >= 0, got {self.fret_count}")

    def _string_number(self, string_number: int) -> None:
        if string_number < 1 or string_number > self.tuning.string_count:
            raise InvalidPositionError(
                f"string number {string_number} out of range for a "
                f"{self.tuning.string_count}-string tuning"
            )

    def _fret(self, fret: int) -> None:
        if fret < 0 or fret > self.fret_count:
            raise InvalidPositionError(
                f"fret {fret} out of range for a {self.fret_count}-fret fretboard"
            )

    def pitch_at(self, string_number: int, fret: int) -> Pitch:
        """Return the pitch sounding at the given string and fret."""
        self._string_number(string_number)
        self._fret(fret)
        return self.tuning.string(string_number).pitch_at(fret)

    def pitch_class_at(self, string_number: int, fret: int) -> PitchClass:
        """Return the pitch class sounding at the given string and fret."""
        return self.pitch_at(string_number, fret).pitch_class

    def position_at(
        self,
        string_number: int,
        fret: int,
        *,
        root: PitchClass | None = None,
    ) -> FretboardPosition:
        """Return the enriched position, optionally with its displacement from ``root``."""
        pitch = self.pitch_at(string_number, fret)
        interval = None if root is None else chromatic_interval_between(root, pitch.pitch_class)
        return FretboardPosition(string_number, fret, pitch, interval)

    def positions(
        self,
        root: PitchClass | None = None,
    ) -> Iterator[FretboardPosition]:
        """Iterate every position in stored string order, lowest fret first.

        When ``root`` is given, each position carries its chromatic displacement
        relative to ``root``.
        """
        for string in self.tuning.strings:
            for fret in range(self.fret_count + 1):
                yield self.position_at(string.number, fret, root=root)

    def pitch_class_locations(self, pitch_class: PitchClass) -> tuple[FretPosition, ...]:
        """Return every position on the fretboard with the given pitch class."""
        locations: list[FretPosition] = []
        for string in self.tuning.strings:
            for fret in range(self.fret_count + 1):
                if string.pitch_class_at(fret) is pitch_class:
                    locations.append(FretPosition(string.number, fret))
        return tuple(locations)

    def pitch_locations(self, pitch: Pitch) -> tuple[FretPosition, ...]:
        """Return every position that sounds exactly ``pitch`` (octave included)."""
        locations: list[FretPosition] = []
        for string in self.tuning.strings:
            for fret in range(self.fret_count + 1):
                if string.pitch_at(fret) == pitch:
                    locations.append(FretPosition(string.number, fret))
        return tuple(locations)
