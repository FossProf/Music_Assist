"""Tests for the PySide6 vertical slice: selectors, window wiring, and geometry."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.instrument.tuning import STANDARD
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale_formulas import MINOR_PENTATONIC, SCALE_FORMULAS
from guitar_app.services.interval_service import evaluate_intervals
from guitar_app.services.scale_service import available_scale_formulas, evaluate_scale
from guitar_app.ui.fretboard_widget import FretboardWidget
from guitar_app.ui.geometry import FRET_MARKERS, FretboardGeometry, fretboard_geometry
from guitar_app.ui.main_window import STANDARD_BOARD, MainWindow
from guitar_app.ui.render_annotations import (
    RenderRole,
    render_interval_result,
    render_scale_result,
)


class TestFretboardGeometry:
    def test_deterministic_coordinates(self) -> None:
        geometry: FretboardGeometry = fretboard_geometry(STANDARD_BOARD, 800.0, 400.0)
        assert geometry == fretboard_geometry(STANDARD_BOARD, 800.0, 400.0)

    def test_strings_are_ordered_top_to_bottom(self) -> None:
        geometry = fretboard_geometry(STANDARD_BOARD, 800.0, 400.0)
        assert geometry.y_for_string(6) < geometry.y_for_string(5) < geometry.y_for_string(1)
        assert geometry.y_for_string(6) < geometry.y_for_string(1)

    def test_string_orientation_matches_domain_order(self) -> None:
        geometry = fretboard_geometry(STANDARD_BOARD, 800.0, 400.0)
        ys = [geometry.y_for_string(number) for number in range(6, 0, -1)]
        assert ys == sorted(ys)

    def test_fret_centers_are_monotonic_and_open_area_is_left_of_nut(self) -> None:
        geometry = fretboard_geometry(STANDARD_BOARD, 800.0, 400.0)
        xs = [geometry.x_for_fret(fret) for fret in range(0, 13)]
        assert xs == sorted(xs)
        assert geometry.x_for_fret(0) < geometry.x_for_fret_line(0)
        assert geometry.x_for_fret(1) > geometry.x_for_fret_line(0)

    def test_fret_lines_are_monotonic(self) -> None:
        geometry = fretboard_geometry(STANDARD_BOARD, 800.0, 400.0)
        assert geometry.x_for_fret_line(0) < geometry.x_for_fret_line(1)
        assert geometry.x_for_fret_line(12) == geometry.left + 13 * geometry.cell_width

    def test_respects_fret_count(self) -> None:
        geometry = fretboard_geometry(Fretboard(STANDARD, 24), 800.0, 400.0)
        assert geometry.fret_count == 24
        assert geometry.x_for_fret(24) > geometry.x_for_fret(12)

    def test_fret_markers_are_the_expected_frets(self) -> None:
        assert FRET_MARKERS == (3, 5, 7, 9, 12)

    def test_fret_out_of_range_raises(self) -> None:
        geometry = fretboard_geometry(STANDARD_BOARD, 800.0, 400.0)
        with pytest.raises(ValueError):
            geometry.x_for_fret(13)
        with pytest.raises(ValueError):
            geometry.x_for_fret(-1)

    def test_string_out_of_range_raises(self) -> None:
        geometry = fretboard_geometry(STANDARD_BOARD, 800.0, 400.0)
        with pytest.raises(ValueError):
            geometry.y_for_string(0)
        with pytest.raises(ValueError):
            geometry.y_for_string(7)


class TestFretboardWidget:
    def test_accepts_render_annotations(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        annotations = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        )
        widget.set_annotations(STANDARD_BOARD, annotations)
        assert widget.fretboard == STANDARD_BOARD
        assert widget.annotations == annotations

    def test_accepts_empty_annotations(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        widget.set_annotations(STANDARD_BOARD, ())
        assert widget.fretboard == STANDARD_BOARD
        assert widget.annotations == ()

    def test_replaces_previous_annotations(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        first = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        )
        second = render_scale_result(evaluate_scale(STANDARD_BOARD, PitchClass.C, "major"))
        widget.set_annotations(STANDARD_BOARD, first)
        assert widget.annotations == first
        widget.set_annotations(STANDARD_BOARD, second)
        assert widget.annotations == second

    def test_renders_fretboard_shorter_than_twelve_frets(self, qapp: QApplication) -> None:
        short_board = Fretboard(STANDARD, 5)
        widget = FretboardWidget()
        annotations = render_scale_result(
            evaluate_scale(short_board, PitchClass.A, "minor_pentatonic")
        )
        widget.set_annotations(short_board, annotations)
        assert widget.fretboard == short_board
        assert all(annotation.position.fret <= 5 for annotation in widget.annotations)
        pixmap = widget.grab()
        assert not pixmap.isNull()

    def test_accepts_interval_only_annotations(self, qapp: QApplication) -> None:
        annotations = render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(STANDARD_BOARD, annotations)
        assert widget.annotations == annotations
        pixmap = widget.grab()
        assert not pixmap.isNull()

    def test_renders_combined_annotations(self, qapp: QApplication) -> None:
        combined = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(STANDARD_BOARD, combined)
        assert widget.annotations == combined
        pixmap = widget.grab()
        assert not pixmap.isNull()

    def test_shared_position_keeps_scale_primary_and_interval_secondary(
        self, qapp: QApplication
    ) -> None:
        combined = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(STANDARD_BOARD, combined)
        plans = {plan.position: plan for plan in widget._build_plan()}
        shared = plans[FretPosition(6, 0)]  # open E: scale fifth + interval fifth
        assert shared.primary.role is RenderRole.SCALE_TONE
        assert shared.secondary is not None
        assert shared.secondary.role is RenderRole.INTERVAL
        assert shared.secondary.label == "5"

    def test_shared_root_position_keeps_scale_root_primary_and_interval_root_secondary(
        self, qapp: QApplication
    ) -> None:
        combined = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(STANDARD_BOARD, combined)
        plans = {plan.position: plan for plan in widget._build_plan()}
        shared = plans[FretPosition(6, 5)]  # 6th string fret 5 is an A root
        assert shared.primary.role is RenderRole.SCALE_ROOT
        assert shared.primary.label == "1"
        assert shared.secondary is not None
        assert shared.secondary.role is RenderRole.INTERVAL_ROOT
        assert shared.secondary.label == "R"

    def test_interval_only_root_annotation_remains_visible_and_emphasized(
        self, qapp: QApplication
    ) -> None:
        annotations = render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(STANDARD_BOARD, annotations)
        plans = {plan.position: plan for plan in widget._build_plan()}
        root_plan = plans[FretPosition(6, 5)]  # interval-only A root position
        assert root_plan.primary.role is RenderRole.INTERVAL_ROOT
        assert root_plan.primary.label == "R"
        assert root_plan.secondary is None
        pixmap = widget.grab()
        assert not pixmap.isNull()

    def test_widget_source_has_no_scale_domain_types(self) -> None:
        module = inspect.getmodule(FretboardWidget)
        assert module is not None and module.__file__ is not None
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "ScaleFretboardPosition" not in source
        assert "LayerResult" not in source


class TestMainWindowSelectors:
    def test_scale_selector_populated_from_catalog(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.scale_selector.count() == len(SCALE_FORMULAS)
        assert window.scale_selector.count() == len(available_scale_formulas())
        assert [
            window.scale_selector.itemText(i) for i in range(window.scale_selector.count())
        ] == [named.name for named in SCALE_FORMULAS]

    def test_root_selector_contains_all_pitch_classes(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.root_selector.count() == 12
        assert [window.root_selector.itemText(i) for i in range(window.root_selector.count())] == [
            pitch_class.spelling() for pitch_class in PitchClass
        ]

    def test_default_selection_is_a_minor_pentatonic(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.root_selector.currentText() == "A"
        assert window.scale_selector.currentText() == MINOR_PENTATONIC.name
        assert window.selection_label.text() == "A Minor Pentatonic"
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        )

    def test_changing_root_and_scale_re_evaluates(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.root_selector.setCurrentIndex(0)  # C
        window.scale_selector.setCurrentIndex(0)  # Major
        assert window.selection_label.text() == "C Major"
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.C, "major")
        )

    def test_changing_scale_alone_re_evaluates(self, qapp: QApplication) -> None:
        window = MainWindow()
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        assert window.selection_label.text() == "A Dorian"
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "dorian")
        )

    def test_evaluated_annotations_stay_within_bounds(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.fretboard_widget.annotations
        for annotation in window.fretboard_widget.annotations:
            assert 1 <= annotation.position.string_number <= 6
            assert 0 <= annotation.position.fret <= 12


class TestLayerCheckboxes:
    def test_checkboxes_are_derived_from_controls(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert list(window.layer_checkboxes) == ["scale", "interval"]
        assert window.layer_checkboxes["scale"].text() == "Scale"
        assert window.layer_checkboxes["interval"].text() == "Intervals"

    def test_defaults_are_scale_on_and_intervals_off(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.layer_checkboxes["scale"].isChecked() is True
        assert window.layer_checkboxes["interval"].isChecked() is False
        assert all(
            annotation.role in (RenderRole.SCALE_ROOT, RenderRole.SCALE_TONE)
            for annotation in window.fretboard_widget.annotations
        )

    def test_disabling_scale_removes_scale_annotations(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        assert window.fretboard_widget.annotations == ()

    def test_enabling_intervals_adds_interval_annotations(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        expected = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.A))
        assert window.fretboard_widget.annotations == expected
        assert any(
            annotation.role in (RenderRole.INTERVAL, RenderRole.INTERVAL_ROOT)
            for annotation in window.fretboard_widget.annotations
        )

    def test_both_layers_enabled_preserves_combined_behavior(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        expected = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.A))
        assert window.fretboard_widget.annotations == expected
        pixmap = window.fretboard_widget.grab()
        assert not pixmap.isNull()

    def test_both_layers_disabled_produces_empty_annotation_tuple(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(False)
        assert window.fretboard_widget.annotations == ()
        pixmap = window.fretboard_widget.grab()
        assert not pixmap.isNull()

    def test_changing_root_updates_all_enabled_layers(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        expected = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.C, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.C))
        assert window.fretboard_widget.annotations == expected

    def test_changing_scale_while_scale_disabled_does_not_enable_it(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        assert window.layer_checkboxes["scale"].isChecked() is False
        assert window.fretboard_widget.annotations == ()

    def test_changing_scale_keeps_interval_layer_and_updates_scale(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        expected = render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "dorian")
        ) + render_interval_result(evaluate_intervals(STANDARD_BOARD, PitchClass.A))
        assert window.fretboard_widget.annotations == expected

    def test_re_enabling_scale_uses_the_currently_selected_scale(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        assert window.fretboard_widget.annotations == ()
        window.layer_checkboxes["scale"].setChecked(True)
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(STANDARD_BOARD, PitchClass.A, "dorian")
        )

    def test_headless_rendering_of_all_enabled_states(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert not window.fretboard_widget.grab().isNull()  # scale only
        window.layer_checkboxes["interval"].setChecked(True)
        assert not window.fretboard_widget.grab().isNull()  # both
        window.layer_checkboxes["scale"].setChecked(False)
        assert not window.fretboard_widget.grab().isNull()  # intervals only
        window.layer_checkboxes["interval"].setChecked(False)
        assert not window.fretboard_widget.grab().isNull()  # neither
        assert window.fretboard_widget.annotations == ()
