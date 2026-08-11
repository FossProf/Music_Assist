"""The interval layer: annotates every fretboard position with its
root-relative chromatic interval."""

from __future__ import annotations

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.interval_mapping import (
    IntervalFretboardPosition,
    map_intervals_to_fretboard,
)
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.theory.pitch import PitchClass


class IntervalLayer:
    """Evaluates root-relative chromatic intervals across a fretboard.

    ``IntervalLayer`` is stateless and owns no inputs: the fretboard and root
    are supplied at evaluation time. Its evaluated result preserves the interval
    mapping information — fret position, sounding pitch, and root-relative
    chromatic interval — for every fretboard position, and carries the layer's
    stable metadata.
    """

    id = "interval"
    name = "Intervals"

    def evaluate(
        self,
        fretboard: Fretboard,
        root: PitchClass,
    ) -> LayerResult[IntervalFretboardPosition]:
        """Return every fretboard position annotated with its displacement from ``root``."""
        return LayerResult(
            layer_id=self.id,
            layer_name=self.name,
            annotations=map_intervals_to_fretboard(fretboard, root),
        )
