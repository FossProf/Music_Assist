"""Application service for scale-to-fretboard evaluation.

The UI depends on this service instead of coordinating the catalog, ``Scale``
construction, and layer evaluation itself.
"""

from __future__ import annotations

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.scale_mapping import ScaleFretboardPosition
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.layers.scale_layer import ScaleLayer
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale import Scale
from guitar_app.core.theory.scale_formulas import (
    SCALE_FORMULAS,
    NamedScaleFormula,
    scale_formula_by_id,
)


def evaluate_scale(
    fretboard: Fretboard,
    root: PitchClass,
    scale_id: str,
) -> LayerResult[ScaleFretboardPosition]:
    """Evaluate the named scale ``scale_id`` from ``root`` across ``fretboard``.

    Resolves the ID through the catalog, builds the :class:`Scale`, and returns
    the evaluated :class:`ScaleLayer` result. Unknown IDs raise
    :class:`UnknownScaleFormulaError`.
    """
    named = scale_formula_by_id(scale_id)
    scale = Scale(root, named.formula)
    return ScaleLayer().evaluate(fretboard, scale)


def available_scale_formulas() -> tuple[NamedScaleFormula, ...]:
    """Return the catalog's named scale formulas in stable order.

    The returned values are the shared :class:`NamedScaleFormula` instances;
    callers must not mutate them.
    """
    return SCALE_FORMULAS
