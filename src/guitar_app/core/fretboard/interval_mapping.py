"""Interval-to-fretboard mapping: every position annotated with its
root-relative chromatic displacement.

This is the interval equivalent of ``map_scale_to_fretboard``: instead of
filtering to scale tones, every fretboard position receives a
:class:`ChromaticInterval`. Like the scale mapping, it sits at the integration
boundary between the theory domain and the fretboard domain and returns
structured domain data only.
"""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.theory.chromatic_interval import (
    ChromaticInterval,
    chromatic_interval_between,
)
from guitar_app.core.theory.pitch import Pitch, PitchClass


@dataclass(frozen=True, slots=True)
class IntervalFretboardPosition:
    """A fretboard position annotated with its root-relative chromatic interval.

    ``chromatic_interval`` is the ascending modulo-12 displacement from the
    mapping's root, in 0..11 semitones. It encodes distance only, not
    theoretical interval identity or enharmonic spelling. No rendering
    information is included.
    """

    position: FretPosition
    pitch: Pitch
    chromatic_interval: ChromaticInterval

    @property
    def pitch_class(self) -> PitchClass:
        """The pitch class sounding at this position."""
        return self.pitch.pitch_class


def map_intervals_to_fretboard(
    fretboard: Fretboard,
    root: PitchClass,
) -> tuple[IntervalFretboardPosition, ...]:
    """Return every fretboard position annotated with its displacement from ``root``.

    For each position in fretboard iteration order (stored string order, lowest
    fret first), the interval is ``chromatic_interval_between(root,
    position.pitch_class)`` — always exactly one result per position, with no
    filtering or grouping.
    """
    results: list[IntervalFretboardPosition] = []
    for board_position in fretboard.positions():
        results.append(
            IntervalFretboardPosition(
                position=FretPosition(board_position.string_number, board_position.fret),
                pitch=board_position.pitch,
                chromatic_interval=chromatic_interval_between(root, board_position.pitch_class),
            )
        )
    return tuple(results)
