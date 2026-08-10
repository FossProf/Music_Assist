"""Scale-to-fretboard mapping: every fretboard position belonging to a scale.

This is the integration boundary between the theory domain (``Scale``) and the
fretboard domain. ``Scale`` itself never imports guitar or fretboard modules.
"""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.theory.chromatic_interval import (
    ChromaticInterval,
    chromatic_interval_between,
)
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale import Scale
from guitar_app.core.theory.scale_degree import ScaleDegree


@dataclass(frozen=True, slots=True)
class ScaleFretboardPosition:
    """A fretboard position that belongs to a scale.

    ``degree`` is the preserved :class:`ScaleDegree` and ``chromatic_interval``
    is the root-relative chromatic displacement. No rendering information is
    included; this is structured domain data for visualization.
    """

    position: FretPosition
    pitch: Pitch
    degree: ScaleDegree
    chromatic_interval: ChromaticInterval

    @property
    def pitch_class(self) -> PitchClass:
        """The pitch class sounding at this position."""
        return self.pitch.pitch_class


def map_scale_to_fretboard(
    fretboard: Fretboard,
    scale: Scale,
) -> tuple[ScaleFretboardPosition, ...]:
    """Return every fretboard position belonging to ``scale``.

    For each position in fretboard iteration order (stored string order, lowest
    fret first), every scale tone whose pitch class matches the position's pitch
    class is emitted. When multiple tones resolve to the same pitch class (e.g.
    ``#4`` and ``b5``), one result is emitted per tone, in formula order, so
    degree identities are never collapsed into a single pitch class.
    """
    results: list[ScaleFretboardPosition] = []
    for board_position in fretboard.positions():
        for tone in scale.tones:
            if tone.pitch_class == board_position.pitch_class:
                results.append(
                    ScaleFretboardPosition(
                        position=FretPosition(board_position.string_number, board_position.fret),
                        pitch=board_position.pitch,
                        degree=tone.degree,
                        chromatic_interval=chromatic_interval_between(
                            scale.root, board_position.pitch_class
                        ),
                    )
                )
    return tuple(results)
