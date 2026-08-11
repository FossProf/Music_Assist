"""UI-only render annotations projected from layer results.

Core layer results are structured domain data and stay untouched. This module
is the explicit UI projection boundary: it converts each concrete layer result
into the small presentation model the fretboard widget paints.

Like ``ui.geometry``, this module is deliberately free of PySide6 so the
projection rules are unit-testable without a QApplication or a display. The
render annotation may carry presentation semantics (a role/category) but never
Qt objects, pixel coordinates, fonts, or painter state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import cast

from guitar_app.core.fretboard.fretboard import FretPosition
from guitar_app.core.fretboard.interval_mapping import IntervalFretboardPosition
from guitar_app.core.fretboard.scale_mapping import ScaleFretboardPosition
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.layers.triad_layer import TriadLayerResult
from guitar_app.core.theory.chromatic_interval import ChromaticInterval
from guitar_app.core.theory.scale_degree import ScaleDegree
from guitar_app.core.theory.triad import TriadInversion

#: The tonic scale degree, drawn with a distinct palette.
_TONIC = ScaleDegree(1)


class RenderRole(Enum):
    """Presentation category of a render annotation.

    The widget uses the role to pick a visual treatment; the enum carries no
    geometry, color, or painter information. Root roles are split per layer so
    a scale root and an interval root at the same position stay distinct.
    """

    SCALE_ROOT = "scale_root"
    SCALE_TONE = "scale_tone"
    INTERVAL_ROOT = "interval_root"
    INTERVAL = "interval"
    TRIAD_ROOT = "triad_root"
    TRIAD_TONE = "triad_tone"


@dataclass(frozen=True, slots=True)
class FretboardRenderAnnotation:
    """An immutable, Qt-free presentation of one fretboard location.

    ``label`` is the text to draw; ``role`` selects the visual treatment.
    Pixel coordinates, colors, fonts, and painter objects are never stored
    here — the widget derives them from the fretboard geometry at paint time.
    """

    position: FretPosition
    label: str
    role: RenderRole


@dataclass(frozen=True, slots=True)
class TriadVoicingRenderGroup:
    """An immutable, Qt-free grouping of one voicing's three fret positions.

    Projected from a domain :class:`TriadVoicing`: ``positions`` holds the
    three chord-tone positions in string-set order (ascending string number),
    ``string_set`` names the adjacent strings, and ``inversion`` preserves the
    voicing's classified inversion. It is purely a UI grouping/highlight model
    — no coordinates, colors, or painter state, and never stored on the domain
    voicing.
    """

    positions: tuple[FretPosition, FretPosition, FretPosition]
    string_set: tuple[int, int, int]
    inversion: TriadInversion


def render_scale_result(
    result: LayerResult[ScaleFretboardPosition],
) -> tuple[FretboardRenderAnnotation, ...]:
    """Project a scale layer result into render annotations.

    Labels are ``ScaleDegree.label``. The tonic receives the ``SCALE_ROOT``
    role; every other scale tone receives ``SCALE_TONE``.
    """
    annotations: list[FretboardRenderAnnotation] = []
    for annotation in result.annotations:
        role = RenderRole.SCALE_ROOT if annotation.degree == _TONIC else RenderRole.SCALE_TONE
        annotations.append(
            FretboardRenderAnnotation(annotation.position, annotation.degree.label, role)
        )
    return tuple(annotations)


def render_interval_result(
    result: LayerResult[IntervalFretboardPosition],
) -> tuple[FretboardRenderAnnotation, ...]:
    """Project an interval layer result into render annotations.

    Labels are ``ChromaticInterval.abbreviation``. Positions at the root
    receive the ``INTERVAL_ROOT`` role; every other position receives
    ``INTERVAL``.
    """
    return tuple(
        FretboardRenderAnnotation(
            annotation.position,
            annotation.chromatic_interval.abbreviation,
            RenderRole.INTERVAL_ROOT
            if annotation.chromatic_interval is ChromaticInterval.UNISON
            else RenderRole.INTERVAL,
        )
        for annotation in result.annotations
    )


def render_triad_result(
    result: TriadLayerResult,
) -> tuple[FretboardRenderAnnotation, ...]:
    """Project a triad layer result into point render annotations.

    Each chord-tone position becomes an ordinary point annotation like the
    scale layer: labels are the triad degree labels (``"1"``, ``"3"``,
    ``"b3"``, ``"5"``, ``"b5"``, ``"#5"``). Root positions receive the
    ``TRIAD_ROOT`` role; every other chord tone receives ``TRIAD_TONE``. The
    roles are triad-specific so a scale root at the same position stays
    distinct. Voicings are *not* projected here.
    """
    return tuple(
        FretboardRenderAnnotation(
            annotation.position,
            annotation.degree.label,
            RenderRole.TRIAD_ROOT if annotation.degree == _TONIC else RenderRole.TRIAD_TONE,
        )
        for annotation in result.annotations
    )


def render_triad_voicings(
    result: TriadLayerResult,
) -> tuple[TriadVoicingRenderGroup, ...]:
    """Project a triad layer result's voicings into grouping/highlight data.

    Each detected voicing becomes a :class:`TriadVoicingRenderGroup`: the three
    chord-tone positions in string-set order, the adjacent strings, and the
    classified inversion. Order follows the service result's deterministic
    voicing order, so index 0 is a stable "default active" choice. No rendering
    information is added to the domain :class:`TriadVoicing`.
    """
    return tuple(
        TriadVoicingRenderGroup(
            positions=cast(
                tuple[FretPosition, FretPosition, FretPosition],
                tuple(tone.position for tone in voicing.tones),
            ),
            string_set=voicing.string_set,
            inversion=voicing.inversion,
        )
        for voicing in result.voicings
    )
