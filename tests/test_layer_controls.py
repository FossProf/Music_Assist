"""Tests for the UI layer-control definitions."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from guitar_app.ui import layer_controls as controls_module
from guitar_app.ui.layer_controls import LAYER_CONTROLS, LayerControl


class TestLayerControlDefinitions:
    def test_controls_exist_in_deterministic_order(self) -> None:
        assert [control.id for control in LAYER_CONTROLS] == ["scale", "interval"]

    def test_names_match_the_user_facing_labels(self) -> None:
        assert [control.name for control in LAYER_CONTROLS] == ["Scale", "Intervals"]

    def test_ids_match_core_layer_ids(self) -> None:
        assert [control.id for control in LAYER_CONTROLS] == ["scale", "interval"]

    def test_defaults_are_scale_on_and_intervals_off(self) -> None:
        by_id = {control.id: control for control in LAYER_CONTROLS}
        assert by_id["scale"].default_enabled is True
        assert by_id["interval"].default_enabled is False

    def test_controls_are_immutable(self) -> None:
        control = LAYER_CONTROLS[0]
        assert isinstance(control, LayerControl)
        with pytest.raises(FrozenInstanceError):
            control.default_enabled = False  # type: ignore[misc]

    def test_controls_are_duplicate_free(self) -> None:
        assert len(LAYER_CONTROLS) == len({control.id for control in LAYER_CONTROLS})

    def test_module_contains_no_qt_widgets_or_callbacks(self) -> None:
        source = Path(controls_module.__file__).read_text(encoding="utf-8")
        assert "from PySide6" not in source
        assert "QCheckBox" not in source
        assert "guitar_app.services" not in source
