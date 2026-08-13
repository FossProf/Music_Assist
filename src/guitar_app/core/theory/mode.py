"""Modes of the major scale and their parallel/relative relationships.

A :class:`Mode` is a typed identity for one of the seven diatonic modes. It
reuses the existing named scale formula catalog rather than defining formulas
again: each mode is bound to the catalog entry with the same ID, so Ionian
shares the Major formula and Aeolian shares Natural Minor. The module also
exposes the two relationships the future Mode Explorer needs, both derived
from the existing scale model and major-scale degree table:

- **parallel** modes — same tonal root, different formula (A Ionian, A Dorian,
  A Phrygian, ...);
- **relative** modes — same pitch collection, different tonal center (D Dorian,
  A Aeolian, and B Locrian all come from C major).

This is pure theory: no fretboard, instrument, or UI concepts are referenced.
"""

from __future__ import annotations

from enum import Enum

from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale import Scale
from guitar_app.core.theory.scale_degree import (
    ScaleDegree,
    natural_scale_degree_offset,
)
from guitar_app.core.theory.scale_formulas import (
    AEOLIAN,
    DORIAN,
    IONIAN,
    LOCRIAN,
    LYDIAN,
    MIXOLYDIAN,
    PHRYGIAN,
    NamedScaleFormula,
)


class Mode(Enum):
    """A mode of the major scale, bound to its catalog scale formula.

    Each member carries its stable snake_case ``id``, human-readable
    ``display_name``, ``degree`` (the mode's index within the parent major
    scale, 1..7), and the associated
    :class:`~guitar_app.core.theory.scale_formulas.NamedScaleFormula` from the
    existing catalog — the same `ScaleFormula` instance the catalog uses, never
    a duplicate. The formula and its metadata are immutable.
    """

    IONIAN = ("ionian", "Ionian", 1, IONIAN)
    DORIAN = ("dorian", "Dorian", 2, DORIAN)
    PHRYGIAN = ("phrygian", "Phrygian", 3, PHRYGIAN)
    LYDIAN = ("lydian", "Lydian", 4, LYDIAN)
    MIXOLYDIAN = ("mixolydian", "Mixolydian", 5, MIXOLYDIAN)
    AEOLIAN = ("aeolian", "Aeolian", 6, AEOLIAN)
    LOCRIAN = ("locrian", "Locrian", 7, LOCRIAN)

    @property
    def id(self) -> str:
        """The stable programmatic identifier, e.g. ``"dorian"``."""
        return self.value[0]

    @property
    def display_name(self) -> str:
        """The human-readable name, e.g. ``"Dorian"``."""
        return self.value[1]

    @property
    def degree(self) -> int:
        """The mode's degree/index within the parent major scale, 1..7."""
        return self.value[2]

    @property
    def scale_formula(self) -> NamedScaleFormula:
        """The associated catalog scale formula (shared, never duplicated)."""
        return self.value[3]

    @property
    def altered_degrees_from_ionian(self) -> tuple[ScaleDegree, ...]:
        """The degrees the mode alters relative to the Ionian formula.

        Derived from the mode's formula: every degree with a non-zero
        alteration (``b3``, ``b7``, ``#4``, ...). Ionian returns the empty
        tuple. This is the minimal metadata the Mode Explorer needs to
        emphasize what changed without re-encoding theory in UI code.
        """
        return tuple(degree for degree in self.scale_formula.formula if degree.alteration != 0)

    def __str__(self) -> str:
        return self.display_name


def available_modes() -> tuple[Mode, ...]:
    """All seven modes in canonical order: Ionian, Dorian, ..., Locrian."""
    return tuple(Mode)


def parallel_mode(root: PitchClass, mode: Mode) -> Scale:
    """Build the scale for ``root`` using ``mode``'s formula.

    Parallel modes keep the same tonal root and change the formula: A Ionian,
    A Dorian, A Phrygian, ... A Locrian all share the root A.
    """
    return Scale(root, mode.scale_formula.formula)


def relative_mode(parent_major_root: PitchClass, mode: Mode) -> Scale:
    """Build the mode that starts on the parent major scale's degree.

    The modal root is derived from the parent major scale's natural degree
    offsets (``1 -> 0``, ``2 -> 2``, ..., ``7 -> 11``), never a hard-coded
    pitch-name table: for parent C major, D Dorian, E Phrygian, ..., B Locrian.
    """
    modal_root = PitchClass(
        (int(parent_major_root) + natural_scale_degree_offset(mode.degree)) % 12
    )
    return Scale(modal_root, mode.scale_formula.formula)


def parent_major_root_for(modal_root: PitchClass, mode: Mode) -> PitchClass:
    """Return the major-scale root containing ``modal_root`` as its degree.

    The reverse of :func:`relative_mode`: D Dorian, A Aeolian, and G
    Mixolydian all map back to C major. Lets the future Mode Explorer switch
    between parallel and relative views without recomputing the relationship
    in Qt code.
    """
    return PitchClass((int(modal_root) - natural_scale_degree_offset(mode.degree)) % 12)
