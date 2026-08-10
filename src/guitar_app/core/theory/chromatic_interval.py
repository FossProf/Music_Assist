"""Chromatic pitch-class displacement and related helpers.

``ChromaticInterval`` models the modulo-12 semitone distance between pitch
classes, as used for root-relative fretboard analysis. It deliberately does not
model theoretical interval identity (e.g. diminished fifth vs augmented
fourth) or enharmonic spelling; a separate theoretical interval type is future
work.
"""

from __future__ import annotations

from enum import IntEnum

from guitar_app.core.theory.pitch import PitchClass

# Default degree-style labels for the twelve chromatic displacements. These are
# fretboard-analysis labels, not definitive theoretical spellings.
_LABELS: dict[int, str] = {
    0: "R",
    1: "b2",
    2: "2",
    3: "b3",
    4: "3",
    5: "4",
    6: "b5",
    7: "5",
    8: "b6",
    9: "6",
    10: "b7",
    11: "7",
}


class ChromaticInterval(IntEnum):
    """Chromatic pitch-class displacement from a reference pitch class.

    The enum value is the modulo-12 semitone count (0..11). This type describes
    only *distance* between pitch classes; it does NOT encode theoretical
    interval identity or enharmonic spelling. For example, six semitones may be
    spelled ``#4`` or ``b5`` depending on context, but both map to the same
    member here.

    Member names use conventional interval names purely for readability; they
    carry no theoretical meaning beyond the semitone count. There is no octave
    member because pitch-class displacement is modulo 12.
    """

    UNISON = 0
    MINOR_SECOND = 1
    MAJOR_SECOND = 2
    MINOR_THIRD = 3
    MAJOR_THIRD = 4
    PERFECT_FOURTH = 5
    TRITONE = 6
    PERFECT_FIFTH = 7
    MINOR_SIXTH = 8
    MAJOR_SIXTH = 9
    MINOR_SEVENTH = 10
    MAJOR_SEVENTH = 11

    @property
    def semitones(self) -> int:
        """The chromatic displacement in semitones (0..11)."""
        return int(self)

    @property
    def abbreviation(self) -> str:
        """Default fretboard-analysis label, such as ``"5"`` for a fifth.

        These are degree-style labels (``R``, ``b2``, ``2``, ``b3``, ``3``,
        ``4``, ``b5``, ``5``, ``b6``, ``6``, ``b7``, ``7``) used for compact
        fretboard display. They are a default labeling choice, not definitive
        theoretical spellings.
        """
        return _LABELS[int(self)]


def chromatic_interval_between(source: PitchClass, target: PitchClass) -> ChromaticInterval:
    """Return the ascending chromatic displacement from ``source`` to ``target``.

    The result is ``(target - source) mod 12``, always in 0..11 semitones. It
    represents only distance: for example, ``C`` to ``F#`` and ``C`` to ``Gb``
    both yield the same member (six semitones) because no spelling information
    is encoded.
    """
    return ChromaticInterval((int(target) - int(source)) % 12)
