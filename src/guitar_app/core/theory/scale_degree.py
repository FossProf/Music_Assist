"""Diatonic scale degrees and their natural-degree offsets."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from guitar_app.core.errors import InvalidScaleDegreeError
from guitar_app.core.theory.chromatic_interval import ChromaticInterval

#: Natural (major-scale / diatonic) semitone offset for each degree number.
_NATURAL_OFFSETS: dict[int, int] = {
    1: 0,
    2: 2,
    3: 4,
    4: 5,
    5: 7,
    6: 9,
    7: 11,
}

#: Supported accidental alteration bounds, in semitones.
_ALTERATION_MIN = -2
_ALTERATION_MAX = 2


def natural_scale_degree_offset(number: int) -> int:
    """Return the natural major-scale semitone offset for a degree number.

    ``1`` maps to ``0``, ``2`` to ``2``, ..., ``7`` to ``11``. Raises
    :class:`InvalidScaleDegreeError` for numbers outside 1..7.
    """
    if number not in _NATURAL_OFFSETS:
        raise InvalidScaleDegreeError(f"scale degree number must be 1..7, got {number}")
    return _NATURAL_OFFSETS[number]


@dataclass(frozen=True, slots=True)
class ScaleDegree:
    """A diatonic scale degree with an accidental alteration.

    ``number`` is the degree position in the major-scale (diatonic) sequence,
    always 1..7. ``alteration`` is the semitone deviation from the natural
    degree, bounded to -2..+2 (so ``ScaleDegree(4, 1)`` is ``#4`` and
    ``ScaleDegree(5, -1)`` is ``b5``).

    A degree preserves its identity independently of the chromatic pitch it
    resolves to: ``#4`` and ``b5`` are distinct values even though both have
    chromatic offset 6.
    """

    number: int
    alteration: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.number <= 7:
            raise InvalidScaleDegreeError(f"scale degree number must be 1..7, got {self.number}")
        if not _ALTERATION_MIN <= self.alteration <= _ALTERATION_MAX:
            raise InvalidScaleDegreeError(
                f"alteration must be within {_ALTERATION_MIN}..{_ALTERATION_MAX}, "
                f"got {self.alteration}"
            )

    @property
    def label(self) -> str:
        """Compact label: ``"1"``, ``"b3"``, ``"#4"``, ``"bb7"``, ``"##5"``."""
        accidental = "#" * self.alteration if self.alteration >= 0 else "b" * -self.alteration
        return f"{accidental}{self.number}"

    @property
    def chromatic_offset(self) -> ChromaticInterval:
        """Chromatic offset from the tonic: natural offset + alteration, mod 12."""
        return ChromaticInterval((natural_scale_degree_offset(self.number) + self.alteration) % 12)

    def __str__(self) -> str:
        return self.label


@dataclass(frozen=True, slots=True)
class ScaleFormula:
    """An immutable, ordered collection of scale degrees.

    ``degrees`` is the sequence of :class:`ScaleDegree` values in scale order
    (tonic first). It must contain at least one degree and must not repeat an
    identical degree. The formula is read-only after construction and supports
    sequence access (indexing, slicing, iteration, ``len``).
    """

    degrees: tuple[ScaleDegree, ...]

    def __post_init__(self) -> None:
        if not self.degrees:
            raise InvalidScaleDegreeError("scale formula must contain at least one degree")
        if len(set(self.degrees)) != len(self.degrees):
            raise InvalidScaleDegreeError("scale formula must not contain duplicate degrees")

    @property
    def chromatic_offsets(self) -> tuple[ChromaticInterval, ...]:
        """Chromatic offsets of each degree from the tonic, in formula order."""
        return tuple(degree.chromatic_offset for degree in self.degrees)

    def __len__(self) -> int:
        return len(self.degrees)

    def __getitem__(self, index: int | slice) -> ScaleDegree | tuple[ScaleDegree, ...]:
        return self.degrees[index]

    def __iter__(self) -> Iterator[ScaleDegree]:
        return iter(self.degrees)

    def __str__(self) -> str:
        return " ".join(degree.label for degree in self.degrees)
