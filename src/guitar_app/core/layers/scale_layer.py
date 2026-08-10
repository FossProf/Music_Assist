"""The scale layer: projects a scale onto a fretboard."""

from __future__ import annotations

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.scale_mapping import (
    ScaleFretboardPosition,
    map_scale_to_fretboard,
)
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.theory.scale import Scale


class ScaleLayer:
    """Evaluates a scale across a fretboard.

    ``ScaleLayer`` is stateless and owns no inputs: the fretboard and scale are
    supplied at evaluation time. Its evaluated result preserves the scale
    mapping information — fret position, sounding pitch, scale degree, and
    root-relative chromatic interval — and carries the layer's stable metadata.
    """

    id = "scale"
    name = "Scale"

    def evaluate(
        self,
        fretboard: Fretboard,
        scale: Scale,
    ) -> LayerResult[ScaleFretboardPosition]:
        """Return the scale's annotations for every matching fretboard position."""
        return LayerResult(
            layer_id=self.id,
            layer_name=self.name,
            annotations=map_scale_to_fretboard(fretboard, scale),
        )
