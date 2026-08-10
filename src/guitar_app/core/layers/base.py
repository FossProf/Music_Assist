"""The minimal fretboard-layer contract and immutable layer results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from guitar_app.core.fretboard.fretboard import FretPosition


class FretboardAnnotation(Protocol):
    """Any structured annotation that targets one fretboard location.

    Every layer annotation identifies the location it describes with a
    :class:`FretPosition`. Layers never carry rendering fields (color, shape,
    opacity, font, pixel coordinates).
    """

    @property
    def position(self) -> FretPosition: ...


T = TypeVar("T", bound=FretboardAnnotation)


@dataclass(frozen=True, slots=True)
class LayerResult(Generic[T]):
    """Immutable result of evaluating a layer.

    Carries the layer's stable metadata plus the layer-specific annotations.
    Each annotation identifies its fretboard location via
    :class:`FretPosition`. No rendering information is included.
    """

    layer_id: str
    layer_name: str
    annotations: tuple[T, ...]


class Layer(Protocol[T]):
    """Structural contract for fretboard overlay layers.

    A layer has a stable ``id``, a human-readable ``name``, and evaluates to an
    immutable :class:`LayerResult`. There is no universal evaluation context:
    each concrete layer declares the inputs it actually requires (for example
    ``ScaleLayer.evaluate(fretboard, scale)``). The abstraction is intentionally
    minimal so future interval, chord, triad, or audio layers can implement it
    without inheriting irrelevant state. Layers compute structured annotations
    only; they never render.
    """

    id: str
    name: str

    def evaluate(self, *args: Any, **kwargs: Any) -> LayerResult[T]: ...
