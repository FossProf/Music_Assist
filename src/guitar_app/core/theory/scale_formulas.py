"""Named scale formula presets and the catalog of available formulas.

This module keeps named scale definitions separate from scale mechanics:
:class:`~guitar_app.core.theory.scale_degree.ScaleFormula` and
:class:`~guitar_app.core.theory.scale.Scale` know nothing about names such as
"Major" or "Dorian".
"""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.errors import UnknownScaleFormulaError
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula


def _scale_formula(*pairs: tuple[int, int]) -> ScaleFormula:
    """Build a ScaleFormula from ``(number, alteration)`` degree pairs."""
    return ScaleFormula(tuple(ScaleDegree(number, alteration) for number, alteration in pairs))


_MAJOR_FORMULA = _scale_formula((1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0))
_NATURAL_MINOR_FORMULA = _scale_formula((1, 0), (2, 0), (3, -1), (4, 0), (5, 0), (6, -1), (7, -1))
_MAJOR_PENTATONIC_FORMULA = _scale_formula((1, 0), (2, 0), (3, 0), (5, 0), (6, 0))
_MINOR_PENTATONIC_FORMULA = _scale_formula((1, 0), (3, -1), (4, 0), (5, 0), (7, -1))
_DORIAN_FORMULA = _scale_formula((1, 0), (2, 0), (3, -1), (4, 0), (5, 0), (6, 0), (7, -1))
_PHRYGIAN_FORMULA = _scale_formula((1, 0), (2, -1), (3, -1), (4, 0), (5, 0), (6, -1), (7, -1))
_LYDIAN_FORMULA = _scale_formula((1, 0), (2, 0), (3, 0), (4, 1), (5, 0), (6, 0), (7, 0))
_MIXOLYDIAN_FORMULA = _scale_formula((1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, -1))
_LOCRIAN_FORMULA = _scale_formula((1, 0), (2, -1), (3, -1), (4, 0), (5, -1), (6, -1), (7, -1))


@dataclass(frozen=True, slots=True)
class NamedScaleFormula:
    """A named scale formula in the built-in catalog.

    ``id`` is the stable programmatic identifier (snake_case); ``name`` is the
    human-readable display name. Display names are not part of
    :class:`ScaleFormula` itself, so scale mechanics stay unaware of names.
    """

    id: str
    name: str
    formula: ScaleFormula

    def __str__(self) -> str:
        return f"{self.name} ({self.formula})"


#: The four core formulas.
MAJOR = NamedScaleFormula("major", "Major", _MAJOR_FORMULA)
NATURAL_MINOR = NamedScaleFormula("natural_minor", "Natural Minor", _NATURAL_MINOR_FORMULA)
MAJOR_PENTATONIC = NamedScaleFormula(
    "major_pentatonic", "Major Pentatonic", _MAJOR_PENTATONIC_FORMULA
)
MINOR_PENTATONIC = NamedScaleFormula(
    "minor_pentatonic", "Minor Pentatonic", _MINOR_PENTATONIC_FORMULA
)

#: The seven major-scale modes. Ionian reuses the Major formula and Aeolian
#: reuses Natural Minor, so the same ScaleFormula instance backs both.
IONIAN = NamedScaleFormula("ionian", "Ionian", _MAJOR_FORMULA)
DORIAN = NamedScaleFormula("dorian", "Dorian", _DORIAN_FORMULA)
PHRYGIAN = NamedScaleFormula("phrygian", "Phrygian", _PHRYGIAN_FORMULA)
LYDIAN = NamedScaleFormula("lydian", "Lydian", _LYDIAN_FORMULA)
MIXOLYDIAN = NamedScaleFormula("mixolydian", "Mixolydian", _MIXOLYDIAN_FORMULA)
AEOLIAN = NamedScaleFormula("aeolian", "Aeolian", _NATURAL_MINOR_FORMULA)
LOCRIAN = NamedScaleFormula("locrian", "Locrian", _LOCRIAN_FORMULA)

#: Every named formula, in stable enumeration order.
SCALE_FORMULAS: tuple[NamedScaleFormula, ...] = (
    MAJOR,
    NATURAL_MINOR,
    MAJOR_PENTATONIC,
    MINOR_PENTATONIC,
    IONIAN,
    DORIAN,
    PHRYGIAN,
    LYDIAN,
    MIXOLYDIAN,
    AEOLIAN,
    LOCRIAN,
)


def scale_formula_by_id(scale_id: str) -> NamedScaleFormula:
    """Return the named formula with the given stable ID.

    Raises :class:`UnknownScaleFormulaError` if the ID is not in the catalog.
    """
    for entry in SCALE_FORMULAS:
        if entry.id == scale_id:
            return entry
    raise UnknownScaleFormulaError(f"unknown scale formula id: {scale_id!r}")
