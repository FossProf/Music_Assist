"""Triad-to-fretboard mapping: every fretboard position belonging to a triad.

This is the integration boundary between the theory domain (``Triad``) and the
fretboard domain, paralleling ``map_scale_to_fretboard``. It maps individual
triad tones only, producing the raw material for future voicing analysis; it
does NOT identify playable three-note voicings.
"""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.theory.chromatic_interval import (
    ChromaticInterval,
    chromatic_interval_between,
)
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale_degree import ScaleDegree
from guitar_app.core.theory.triad import Triad


@dataclass(frozen=True, slots=True)
class TriadFretboardPosition:
    """A fretboard position that belongs to a triad.

    ``degree`` is the preserved chord-tone :class:`ScaleDegree` (``1``, ``b3``,
    ``3``, ``b5``, ``5``, ``#5``) and ``chromatic_interval`` is the root-relative
    chromatic displacement. No rendering or fingering data is included; this is
    the raw material for voicing analysis, not a claim that any three-note
    combination is a playable voicing.
    """

    position: FretPosition
    pitch: Pitch
    degree: ScaleDegree
    chromatic_interval: ChromaticInterval

    @property
    def pitch_class(self) -> PitchClass:
        """The pitch class sounding at this position."""
        return self.pitch.pitch_class


def map_triad_to_fretboard(
    fretboard: Fretboard,
    triad: Triad,
) -> tuple[TriadFretboardPosition, ...]:
    """Return every fretboard position belonging to ``triad``.

    For each position in fretboard iteration order (stored string order, lowest
    fret first), every triad tone whose pitch class matches the position's pitch
    class is emitted, one result per tone, in triad formula order, so chord-tone
    degree identities are never collapsed into a single pitch class. ``Triad``
    itself stays guitar-agnostic.

    This maps individual triad tones only: it does not group positions into
    three-note voicings, apply string-set or span constraints, or claim any
    combination is playable.
    """
    tones = triad.tones
    results: list[TriadFretboardPosition] = []
    for board_position in fretboard.positions():
        for tone in tones:
            if tone.pitch_class == board_position.pitch_class:
                results.append(
                    TriadFretboardPosition(
                        position=FretPosition(board_position.string_number, board_position.fret),
                        pitch=board_position.pitch,
                        degree=tone.degree,
                        chromatic_interval=chromatic_interval_between(
                            triad.root, board_position.pitch_class
                        ),
                    )
                )
    return tuple(results)
