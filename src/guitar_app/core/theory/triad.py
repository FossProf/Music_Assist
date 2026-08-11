"""Triads: a root pitch class plus a quality, with derived chord tones.

This is a pure theory model: it represents what a triad *is* — its root,
quality, chord-tone identities, and resulting pitch classes — with no guitar
voicing, string, fret, or fingering data. Fretboard logic is deliberately
excluded.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula


def _triad_formula(*pairs: tuple[int, int]) -> ScaleFormula:
    """Build a ScaleFormula from ``(number, alteration)`` degree pairs."""
    return ScaleFormula(tuple(ScaleDegree(number, alteration) for number, alteration in pairs))


class TriadQuality(Enum):
    """A triad quality and its chord-tone formula.

    The formula reuses :class:`ScaleFormula` so chord tones keep their
    :class:`ScaleDegree` identities: diminished is ``1 b3 b5`` and augmented is
    ``1 3 #5`` — distinct degree spellings even where pitch classes coincide
    enharmonically. The formula lives in the immutable enum value and is
    exposed through read-only properties, so quality/formula data cannot be
    mutated. No voicing or fingering data is stored.
    """

    MAJOR = ("Major", _triad_formula((1, 0), (3, 0), (5, 0)))
    MINOR = ("Minor", _triad_formula((1, 0), (3, -1), (5, 0)))
    DIMINISHED = ("Diminished", _triad_formula((1, 0), (3, -1), (5, -1)))
    AUGMENTED = ("Augmented", _triad_formula((1, 0), (3, 0), (5, 1)))

    @property
    def display_name(self) -> str:
        """The human-readable quality name, e.g. ``"Major"``."""
        return self.value[0]

    @property
    def formula(self) -> ScaleFormula:
        """The quality's chord-tone formula, e.g. ``1 3 5``."""
        return self.value[1]

    def __str__(self) -> str:
        return self.display_name


@dataclass(frozen=True, slots=True)
class TriadTone:
    """A single chord tone: a scale degree bound to a concrete pitch class.

    ``pitch_class`` is derived from the root and the degree's chromatic offset,
    normalized modulo 12. The degree is preserved, so enharmonic distinctions
    that normalize to the same pitch class remain distinct tones.
    """

    degree: ScaleDegree
    pitch_class: PitchClass

    def __str__(self) -> str:
        return f"{self.pitch_class.spelling()} ({self.degree})"


@dataclass(frozen=True, slots=True)
class Triad:
    """A concrete triad: a root pitch class plus a quality.

    ``tones`` binds each quality-formula degree to the pitch class it resolves
    to: ``(root + degree chromatic offset) mod 12``. The formula's degrees are
    preserved — tones are not reduced to a bare set of pitch classes. No
    voicing, octave, or fretboard data is included.
    """

    root: PitchClass
    quality: TriadQuality

    @property
    def tones(self) -> tuple[TriadTone, ...]:
        """The triad's chord tones, in quality-formula order."""
        return tuple(
            TriadTone(
                degree=degree,
                pitch_class=PitchClass((int(self.root) + int(degree.chromatic_offset)) % 12),
            )
            for degree in self.quality.formula
        )

    @property
    def pitch_classes(self) -> tuple[PitchClass, ...]:
        """The triad's pitch classes, in quality-formula order."""
        return tuple(tone.pitch_class for tone in self.tones)

    @property
    def degrees(self) -> tuple[ScaleDegree, ...]:
        """The triad's degrees, in quality-formula order."""
        return tuple(tone.degree for tone in self.tones)

    def __str__(self) -> str:
        return f"{self.root.spelling()} {' '.join(tone.degree.label for tone in self.tones)}"
