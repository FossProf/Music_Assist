"""Scales: a root pitch class plus a scale formula, with derived tones."""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.errors import InvalidScaleDegreeError
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula


@dataclass(frozen=True, slots=True)
class ScaleTone:
    """A single tone of a scale: a scale degree bound to a concrete pitch class.

    ``pitch_class`` is derived from the root and the degree's chromatic offset,
    normalized modulo 12. The degree is preserved, so enharmonic distinctions
    that normalize to the same pitch class (e.g. ``#4`` and ``b5``) remain
    distinct tones.
    """

    degree: ScaleDegree
    pitch_class: PitchClass

    def __str__(self) -> str:
        return f"{self.pitch_class.spelling()} ({self.degree})"


@dataclass(frozen=True, slots=True)
class Scale:
    """A concrete scale: a root pitch class plus a scale formula.

    ``tones`` binds each formula degree to the pitch class it resolves to:
    ``(root pitch-class value + degree chromatic offset) mod 12``. The formula's
    degrees are preserved — tones are not reduced to a bare set of pitch
    classes.
    """

    root: PitchClass
    formula: ScaleFormula

    @property
    def tones(self) -> tuple[ScaleTone, ...]:
        """The scale's tones, in formula order."""
        return tuple(
            ScaleTone(
                degree=degree,
                pitch_class=PitchClass((int(self.root) + int(degree.chromatic_offset)) % 12),
            )
            for degree in self.formula
        )

    @property
    def pitch_classes(self) -> tuple[PitchClass, ...]:
        """The scale's pitch classes, in formula order (duplicates possible)."""
        return tuple(tone.pitch_class for tone in self.tones)

    @property
    def scale_degrees(self) -> tuple[ScaleDegree, ...]:
        """The scale's degrees, in formula order."""
        return tuple(self.formula)

    def tone_for(self, degree: ScaleDegree) -> ScaleTone:
        """Return the tone bound to ``degree``.

        Raises :class:`InvalidScaleDegreeError` if the degree is not part of
        the scale's formula.
        """
        for tone in self.tones:
            if tone.degree == degree:
                return tone
        raise InvalidScaleDegreeError(f"degree {degree} is not in scale {self}")

    def __str__(self) -> str:
        return f"{self.root.spelling()} {' '.join(tone.degree.label for tone in self.tones)}"
