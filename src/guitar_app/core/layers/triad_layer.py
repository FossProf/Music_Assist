"""The triad layer: triad-tone positions plus detected adjacent-string voicings."""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.triad_mapping import (
    TriadFretboardPosition,
    map_triad_to_fretboard,
)
from guitar_app.core.fretboard.triad_voicing import (
    DEFAULT_MAX_FRET_SPAN,
    TriadVoicing,
    find_triad_voicings,
)
from guitar_app.core.theory.triad import Triad


@dataclass(frozen=True, slots=True)
class TriadLayerResult:
    """Immutable result of evaluating the triad layer.

    Carries the layer's stable metadata (mirroring :class:`LayerResult`'s
    ``layer_id``/``layer_name`` semantics), every triad-tone fretboard position
    in ``annotations``, and the detected playable adjacent-string voicings in
    ``voicings``. The layer does not choose a preferred voicing. No rendering
    information is included.

    This result intentionally is *not* a :class:`LayerResult`: it carries two
    heterogeneous payloads (positions and voicings) that the generic
    single-annotation-tuple result cannot express without widening its type.
    Consequently :class:`TriadLayer` does not satisfy the :class:`Layer`
    protocol; the generic abstraction is deliberately left unchanged pending
    review (see the architecture docs).
    """

    layer_id: str
    layer_name: str
    annotations: tuple[TriadFretboardPosition, ...]
    voicings: tuple[TriadVoicing, ...]


class TriadLayer:
    """Evaluates a concrete triad across a fretboard.

    ``TriadLayer`` is stateless and owns no inputs: the fretboard, triad, and
    span limit are supplied at evaluation time. Evaluation delegates to
    :func:`map_triad_to_fretboard` and :func:`find_triad_voicings` without
    duplicating either algorithm; it does not choose one preferred voicing.

    ``TriadLayer`` does not conform to the :class:`Layer` protocol: its
    ``evaluate`` returns :class:`TriadLayerResult` (annotations plus voicing
    groups), not a ``LayerResult[T]``. The protocol is intentionally left
    unchanged; the incompatibility is documented and reported for review.
    """

    id = "triad"
    name = "Triads"

    def evaluate(
        self,
        fretboard: Fretboard,
        triad: Triad,
        *,
        max_fret_span: int = DEFAULT_MAX_FRET_SPAN,
    ) -> TriadLayerResult:
        """Return every triad tone plus detected voicings on ``fretboard``."""
        return TriadLayerResult(
            layer_id=self.id,
            layer_name=self.name,
            annotations=map_triad_to_fretboard(fretboard, triad),
            voicings=find_triad_voicings(fretboard, triad, max_fret_span=max_fret_span),
        )
