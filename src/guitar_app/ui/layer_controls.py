"""UI-facing definitions of the available fretboard overlay controls.

The layer-control definitions are the single UI model that decides which
existing overlays are visible. They deliberately carry no Qt widgets,
callbacks, services, or layer objects — the MainWindow derives its checkboxes
from them. Like ``ui.render_annotations`` and ``ui.geometry``, this module is
free of PySide6 so the definitions are unit-testable without a display.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LayerControl:
    """UI definition of one toggleable overlay.

    ``id`` matches the corresponding core layer id where practical, ``name``
    is the human-readable label shown to the user, and ``default_enabled`` is
    the initial visibility state.
    """

    id: str
    name: str
    default_enabled: bool


#: Available overlays in deterministic UI order (scale first, then interval).
LAYER_CONTROLS: tuple[LayerControl, ...] = (
    LayerControl("scale", "Scale", True),
    LayerControl("interval", "Intervals", False),
)
