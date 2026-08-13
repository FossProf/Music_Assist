"""Application service for modal exploration (parallel/relative modes).

The UI depends on this service to resolve the musical modal context for the
future Mode Explorer without coordinating the theory :class:`Mode` model
itself. It exposes the parallel/relative distinction as an application-facing
enum and a small immutable result, and deliberately resolves **no fretboard
data**: the UI will drive the existing musical services from
:attr:`ModeSelection.modal_root` and the mode's stable scale ID.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from guitar_app.core.theory.mode import (
    Mode,
    parallel_mode,
    parent_major_root_for,
    relative_mode,
)
from guitar_app.core.theory.mode import (
    available_modes as theory_available_modes,
)
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale import Scale
from guitar_app.core.theory.scale_degree import ScaleDegree


class ModeView(Enum):
    """How a mode selection interprets its input root.

    ``PARALLEL`` keeps the same tonal root and changes the formula, so the
    input root is the modal root. ``RELATIVE`` keeps the same pitch collection
    and changes the tonal center, so the input root is the parent-major root.
    """

    PARALLEL = "Parallel"
    RELATIVE = "Relative"

    @property
    def display_name(self) -> str:
        """The human-readable label, e.g. ``"Parallel"``."""
        return self.value

    def __str__(self) -> str:
        return self.display_name


@dataclass(frozen=True, slots=True)
class ModeSelection:
    """The resolved modal context for one view of one mode from one input root.

    ``input_root`` is the root the user supplied (the modal root in the
    parallel view, the parent-major root in the relative view). ``modal_root``
    is the tonal center of the resulting scale and ``parent_major_root`` the
    major-scale root the mode is relative to. ``scale`` is the concrete modal
    scale and ``altered_degrees_from_ionian`` the mode's characteristic
    alterations, passed through unchanged from the theory model.
    """

    view: ModeView
    mode: Mode
    input_root: PitchClass
    modal_root: PitchClass
    parent_major_root: PitchClass
    scale: Scale
    altered_degrees_from_ionian: tuple[ScaleDegree, ...]


def available_mode_views() -> tuple[ModeView, ...]:
    """The supported views in stable order: Parallel, Relative."""
    return tuple(ModeView)


def available_modes() -> tuple[Mode, ...]:
    """The seven modes in canonical order, delegating to the theory catalog."""
    return theory_available_modes()


def evaluate_mode(root: PitchClass, mode: Mode, view: ModeView) -> ModeSelection:
    """Resolve the modal context of ``mode`` from ``root`` under ``view``.

    In the parallel view ``root`` is the modal root and the parent-major root
    is derived via ``parent_major_root_for``. In the relative view ``root`` is
    the parent-major root and the modal root is derived via ``relative_mode``.
    """
    if view is ModeView.PARALLEL:
        scale = parallel_mode(root, mode)
        modal_root = root
        parent_major_root = parent_major_root_for(modal_root, mode)
    elif view is ModeView.RELATIVE:
        scale = relative_mode(root, mode)
        modal_root = scale.root
        parent_major_root = root
    else:
        raise ValueError(f"unknown mode view: {view!r}")
    return ModeSelection(
        view=view,
        mode=mode,
        input_root=root,
        modal_root=modal_root,
        parent_major_root=parent_major_root,
        scale=scale,
        altered_degrees_from_ionian=mode.altered_degrees_from_ionian,
    )
