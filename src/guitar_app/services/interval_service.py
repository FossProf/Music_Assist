"""Application service for interval-to-fretboard evaluation.

The UI depends on this service instead of evaluating the interval layer
directly, keeping layer evaluation behind one application-facing operation.
"""

from __future__ import annotations

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.interval_mapping import IntervalFretboardPosition
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.layers.interval_layer import IntervalLayer
from guitar_app.core.theory.pitch import PitchClass


def evaluate_intervals(
    fretboard: Fretboard,
    root: PitchClass,
) -> LayerResult[IntervalFretboardPosition]:
    """Evaluate the interval layer from ``root`` across ``fretboard``.

    Returns every fretboard position annotated with its root-relative chromatic
    interval, wrapped in the interval layer's result metadata.
    """
    return IntervalLayer().evaluate(fretboard, root)
