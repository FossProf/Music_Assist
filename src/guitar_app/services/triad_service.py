"""Application service for triad-to-fretboard evaluation.

The UI depends on this service instead of coordinating ``Triad`` construction
and triad-layer evaluation itself, keeping layer evaluation behind one
application-facing operation.
"""

from __future__ import annotations

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.triad_voicing import DEFAULT_MAX_FRET_SPAN
from guitar_app.core.layers.triad_layer import TriadLayer, TriadLayerResult
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.triad import Triad, TriadQuality


def evaluate_triad(
    fretboard: Fretboard,
    root: PitchClass,
    quality: TriadQuality,
    *,
    max_fret_span: int = DEFAULT_MAX_FRET_SPAN,
) -> TriadLayerResult:
    """Evaluate the triad with ``root`` and ``quality`` across ``fretboard``.

    Builds the :class:`Triad` and returns the evaluated :class:`TriadLayer`
    result: every chord-tone fretboard position plus the detected
    adjacent-string voicings. ``max_fret_span`` limits the voicings' fret span.
    """
    return TriadLayer().evaluate(
        fretboard,
        Triad(root, quality),
        max_fret_span=max_fret_span,
    )


def available_triad_qualities() -> tuple[TriadQuality, ...]:
    """Return the triad qualities in stable order.

    The tuple follows the enum's natural declaration order: Major, Minor,
    Diminished, Augmented. Callers must not mutate the shared enum members.
    """
    return tuple(TriadQuality)
