"""Tests for the PySide6 vertical slice: selectors, window wiring, and geometry."""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.instrument.tuning import STANDARD
from guitar_app.core.instrument.tuning_presets import (
    DADGAD_TUNING,
    DROP_D_TUNING,
    available_tunings,
)
from guitar_app.core.layers.triad_layer import TriadLayerResult
from guitar_app.core.theory.mode import Mode
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale_formulas import MINOR_PENTATONIC, SCALE_FORMULAS
from guitar_app.core.theory.triad import TriadQuality
from guitar_app.services.instrument_state import DEFAULT_INSTRUMENT_STATE
from guitar_app.services.interval_service import evaluate_intervals
from guitar_app.services.mode_service import (
    ModeView,
    available_mode_views,
    available_modes,
)
from guitar_app.services.scale_service import available_scale_formulas, evaluate_scale
from guitar_app.services.triad_service import (
    available_triad_qualities,
    evaluate_triad,
)
from guitar_app.ui import main_window as main_window_module
from guitar_app.ui.fretboard_widget import FretboardWidget
from guitar_app.ui.geometry import (
    FretboardGeometry,
    double_marker_frets,
    fret_markers,
    fretboard_geometry,
)
from guitar_app.ui.main_window import MainWindow
from guitar_app.ui.render_annotations import (
    RenderRole,
    TriadVoicingRenderGroup,
    render_interval_result,
    render_scale_result,
    render_triad_result,
    render_triad_voicings,
)

WINDOW_TEST_BOARD = DEFAULT_INSTRUMENT_STATE.fretboard

A_DORIAN_READOUT = "A Dorian · Parent Major: G · Altered from Ionian: b3, b7"
D_DORIAN_READOUT = "D Dorian · Parent Major: C · Altered from Ionian: b3, b7"


def _tuning_index(tuning_id: str) -> int:
    return next(i for i, named in enumerate(available_tunings()) if named.id == tuning_id)


def _mode_index(mode_id: str) -> int:
    return next(i for i, mode in enumerate(available_modes()) if mode.id == mode_id)


def _view_index(view: ModeView) -> int:
    return next(i for i, candidate in enumerate(available_mode_views()) if candidate is view)


class TestFretboardGeometry:
    def test_deterministic_coordinates(self) -> None:
        geometry: FretboardGeometry = fretboard_geometry(WINDOW_TEST_BOARD, 800.0, 400.0)
        assert geometry == fretboard_geometry(WINDOW_TEST_BOARD, 800.0, 400.0)

    def test_strings_are_ordered_top_to_bottom(self) -> None:
        geometry = fretboard_geometry(WINDOW_TEST_BOARD, 800.0, 400.0)
        assert geometry.y_for_string(6) < geometry.y_for_string(5) < geometry.y_for_string(1)
        assert geometry.y_for_string(6) < geometry.y_for_string(1)

    def test_string_orientation_matches_domain_order(self) -> None:
        geometry = fretboard_geometry(WINDOW_TEST_BOARD, 800.0, 400.0)
        ys = [geometry.y_for_string(number) for number in range(6, 0, -1)]
        assert ys == sorted(ys)

    def test_fret_centers_are_monotonic_and_open_area_is_left_of_nut(self) -> None:
        geometry = fretboard_geometry(WINDOW_TEST_BOARD, 800.0, 400.0)
        xs = [geometry.x_for_fret(fret) for fret in range(0, 13)]
        assert xs == sorted(xs)
        assert geometry.x_for_fret(0) < geometry.x_for_fret_line(0)
        assert geometry.x_for_fret(1) > geometry.x_for_fret_line(0)

    def test_fret_lines_are_monotonic(self) -> None:
        geometry = fretboard_geometry(WINDOW_TEST_BOARD, 800.0, 400.0)
        assert geometry.x_for_fret_line(0) < geometry.x_for_fret_line(1)
        assert geometry.x_for_fret_line(12) == geometry.left + 13 * geometry.cell_width

    def test_respects_fret_count(self) -> None:
        geometry = fretboard_geometry(Fretboard(STANDARD, 24), 800.0, 400.0)
        assert geometry.fret_count == 24
        assert geometry.x_for_fret(24) > geometry.x_for_fret(12)

    def test_fret_markers_are_fret_count_aware(self) -> None:
        assert fret_markers(12) == (3, 5, 7, 9)
        assert double_marker_frets(12) == (12,)
        assert fret_markers(22) == (3, 5, 7, 9, 15, 17, 19, 21)
        assert double_marker_frets(22) == (12,)
        assert fret_markers(24) == (3, 5, 7, 9, 15, 17, 19, 21)
        assert double_marker_frets(24) == (12, 24)
        assert fret_markers(27) == (3, 5, 7, 9, 15, 17, 19, 21, 27)
        assert fret_markers(5) == (3, 5)
        assert double_marker_frets(5) == ()

    def test_fret_out_of_range_raises(self) -> None:
        geometry = fretboard_geometry(WINDOW_TEST_BOARD, 800.0, 400.0)
        with pytest.raises(ValueError):
            geometry.x_for_fret(23)
        with pytest.raises(ValueError):
            geometry.x_for_fret(-1)
        short_geometry = fretboard_geometry(Fretboard(STANDARD, 12), 800.0, 400.0)
        with pytest.raises(ValueError):
            short_geometry.x_for_fret(13)

    def test_string_out_of_range_raises(self) -> None:
        geometry = fretboard_geometry(WINDOW_TEST_BOARD, 800.0, 400.0)
        with pytest.raises(ValueError):
            geometry.y_for_string(0)
        with pytest.raises(ValueError):
            geometry.y_for_string(7)


class TestFretboardWidget:
    def test_accepts_render_annotations(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        annotations = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        )
        widget.set_annotations(WINDOW_TEST_BOARD, annotations)
        assert widget.fretboard == WINDOW_TEST_BOARD
        assert widget.annotations == annotations

    def test_accepts_empty_annotations(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, ())
        assert widget.fretboard == WINDOW_TEST_BOARD
        assert widget.annotations == ()

    def test_replaces_previous_annotations(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        first = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        )
        second = render_scale_result(evaluate_scale(WINDOW_TEST_BOARD, PitchClass.C, "major"))
        widget.set_annotations(WINDOW_TEST_BOARD, first)
        assert widget.annotations == first
        widget.set_annotations(WINDOW_TEST_BOARD, second)
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
        annotations = render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, annotations)
        assert widget.annotations == annotations
        pixmap = widget.grab()
        assert not pixmap.isNull()

    def test_renders_combined_annotations(self, qapp: QApplication) -> None:
        combined = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, combined)
        assert widget.annotations == combined
        pixmap = widget.grab()
        assert not pixmap.isNull()

    def test_shared_position_keeps_scale_primary_and_interval_secondary(
        self, qapp: QApplication
    ) -> None:
        combined = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, combined)
        plans = {plan.position: plan for plan in widget._build_plan()}
        shared = plans[FretPosition(6, 0)]  # open E: scale fifth + interval fifth
        assert shared.primary.role is RenderRole.SCALE_TONE
        assert shared.badges
        assert shared.badges[0].role is RenderRole.INTERVAL
        assert shared.badges[0].label == "5"

    def test_shared_root_position_keeps_scale_root_primary_and_interval_root_secondary(
        self, qapp: QApplication
    ) -> None:
        combined = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, combined)
        plans = {plan.position: plan for plan in widget._build_plan()}
        shared = plans[FretPosition(6, 5)]  # 6th string fret 5 is an A root
        assert shared.primary.role is RenderRole.SCALE_ROOT
        assert shared.primary.label == "1"
        assert shared.badges
        assert shared.badges[0].role is RenderRole.INTERVAL_ROOT
        assert shared.badges[0].label == "R"

    def test_interval_only_root_annotation_remains_visible_and_emphasized(
        self, qapp: QApplication
    ) -> None:
        annotations = render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.A))
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, annotations)
        plans = {plan.position: plan for plan in widget._build_plan()}
        root_plan = plans[FretPosition(6, 5)]  # interval-only A root position
        assert root_plan.primary.role is RenderRole.INTERVAL_ROOT
        assert root_plan.primary.label == "R"
        assert root_plan.badges == ()
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
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        )

    def test_changing_root_and_scale_re_evaluates(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.root_selector.setCurrentIndex(0)  # C
        window.scale_selector.setCurrentIndex(0)  # Major
        assert window.selection_label.text() == "C Major"
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.C, "major")
        )

    def test_changing_scale_alone_re_evaluates(self, qapp: QApplication) -> None:
        window = MainWindow()
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        assert window.selection_label.text() == "A Dorian"
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "dorian")
        )

    def test_evaluated_annotations_stay_within_bounds(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.fretboard_widget.annotations
        for annotation in window.fretboard_widget.annotations:
            assert 1 <= annotation.position.string_number <= 6
            assert 0 <= annotation.position.fret <= window._instrument_state.fret_count


class TestLayerCheckboxes:
    def test_checkboxes_are_derived_from_controls(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert list(window.layer_checkboxes) == ["scale", "interval", "triad"]
        assert window.layer_checkboxes["scale"].text() == "Scale"
        assert window.layer_checkboxes["interval"].text() == "Intervals"
        assert window.layer_checkboxes["triad"].text() == "Triads"

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
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.A))
        assert window.fretboard_widget.annotations == expected
        assert any(
            annotation.role in (RenderRole.INTERVAL, RenderRole.INTERVAL_ROOT)
            for annotation in window.fretboard_widget.annotations
        )

    def test_both_layers_enabled_preserves_combined_behavior(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        expected = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.A))
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

    def test_disabling_intervals_keeps_scale_annotations(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        assert any(
            annotation.role in (RenderRole.INTERVAL, RenderRole.INTERVAL_ROOT)
            for annotation in window.fretboard_widget.annotations
        )
        window.layer_checkboxes["interval"].setChecked(False)
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        )

    def test_changing_root_updates_all_enabled_layers(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        expected = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.C, "minor_pentatonic")
        ) + render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.C))
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
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "dorian")
        ) + render_interval_result(evaluate_intervals(WINDOW_TEST_BOARD, PitchClass.A))
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
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "dorian")
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


class TestSelectionLabel:
    def test_label_scale_only(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.selection_label.text() == "A Minor Pentatonic"

    def test_label_intervals_only(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(True)
        assert window.selection_label.text() == "A Intervals"

    def test_label_triads_only(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.selection_label.text() == "A Major Triads"

    def test_label_none(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        assert window.selection_label.text() == "A — No layers"

    def test_label_scale_and_intervals(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        assert window.selection_label.text() == "A Minor Pentatonic · Intervals"

    def test_label_scale_and_triads(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.selection_label.text() == "A Minor Pentatonic · Major Triads"

    def test_label_intervals_and_triads(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.selection_label.text() == "A Intervals · Major Triads"

    def test_label_all_three(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.selection_label.text() == "A Minor Pentatonic · Intervals · Major Triads"

    def test_label_preserves_deterministic_layer_order(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.selection_label.text() == ("A Minor Pentatonic · Intervals · Major Triads")
        window.triad_quality_selector.setCurrentIndex(3)  # Augmented
        assert window.selection_label.text() == (
            "A Minor Pentatonic · Intervals · Augmented Triads"
        )

    def test_changing_root_updates_only_the_prefix(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        assert window.selection_label.text() == "C Minor Pentatonic · Intervals · Major Triads"
        window.layer_checkboxes["triad"].setChecked(False)
        assert window.selection_label.text() == "C Minor Pentatonic · Intervals"
        window.layer_checkboxes["scale"].setChecked(False)
        assert window.selection_label.text() == "C Intervals"
        window.layer_checkboxes["interval"].setChecked(False)
        assert window.selection_label.text() == "C — No layers"

    def test_changing_scale_changes_only_the_scale_portion(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        assert window.selection_label.text() == "A Dorian · Intervals · Major Triads"

    def test_changing_triad_quality_changes_only_the_triad_portion(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        window.triad_quality_selector.setCurrentIndex(2)  # Diminished
        assert window.selection_label.text() == "A Minor Pentatonic · Intervals · Diminished Triads"

    def test_hidden_layer_selections_do_not_appear(self, qapp: QApplication) -> None:
        window = MainWindow()
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.selection_label.text() == "A Intervals · Major Triads"
        window.triad_quality_selector.setCurrentIndex(1)  # Minor (triads hidden)
        window.layer_checkboxes["triad"].setChecked(False)
        assert window.selection_label.text() == "A Intervals"

    def test_re_enabling_scale_restores_currently_selected_scale_label(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        assert window.selection_label.text() == "A — No layers"
        window.layer_checkboxes["scale"].setChecked(True)
        assert window.selection_label.text() == "A Dorian"

    def test_re_enabling_triads_restores_currently_selected_quality(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.triad_quality_selector.setCurrentIndex(1)  # Minor
        assert window.selection_label.text() == "A Minor Pentatonic · Minor Triads"
        window.layer_checkboxes["triad"].setChecked(False)
        assert window.selection_label.text() == "A Minor Pentatonic"
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.selection_label.text() == "A Minor Pentatonic · Minor Triads"

    def test_changing_scale_while_intervals_only_keeps_interval_label(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(True)
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        assert window.selection_label.text() == "A Intervals"


class TestModeSelector:
    def test_defaults_to_identity_ionian_parallel(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.mode_selector.currentData() is Mode.IONIAN
        assert window.mode_selector.currentText() == "Ionian"
        assert window.view_selector.currentData() is ModeView.PARALLEL
        assert window.view_selector.isEnabled() is False
        assert window.scale_selector.currentText() == MINOR_PENTATONIC.name
        assert window.selection_label.text() == "A Minor Pentatonic"
        assert window.mode_label.text() == ""

    def test_mode_readout_parallel_dorian(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        assert window.mode_label.text() == A_DORIAN_READOUT

    def test_mode_readout_relative_dorian(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.mode_label.text() == D_DORIAN_READOUT

    def test_mode_readout_relative_lydian(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.mode_selector.setCurrentIndex(_mode_index("lydian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.mode_label.text() == "D Lydian · Parent Major: A · Altered from Ionian: #4"

    def test_mode_readout_cleared_when_leaving_modal_context(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        assert window.mode_label.text() != ""
        window.mode_selector.setCurrentIndex(_mode_index("ionian"))
        assert window.mode_label.text() == ""

    def test_selecting_dorian_mirrors_formula_into_scale_selector(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        assert window.view_selector.isEnabled() is True
        assert window.scale_selector.currentText() == "Dorian"
        assert window.selection_label.text() == "A Dorian"
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.A, "dorian")
        )

    def test_parallel_view_keeps_input_root(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.PARALLEL))
        assert window.selection_label.text() == "C Dorian"
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.C, "dorian")
        )

    def test_relative_dorian_uses_derived_modal_root(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.selection_label.text() == "D Dorian of C Major"
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.D, "dorian")
        )

    def test_relative_lydian_from_a_is_d_lydian(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.mode_selector.setCurrentIndex(_mode_index("lydian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.selection_label.text() == "D Lydian of A Major"
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.D, "lydian")
        )

    def test_relative_aeolian_maps_to_relative_minor(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("aeolian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.selection_label.text() == "A Aeolian of C Major"
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.A, "aeolian")
        )

    def test_returning_to_ionian_restores_prior_scale(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        assert window.scale_selector.currentText() == "Dorian"
        window.mode_selector.setCurrentIndex(_mode_index("ionian"))
        assert window.scale_selector.currentText() == MINOR_PENTATONIC.name
        assert window.view_selector.currentData() is ModeView.PARALLEL
        assert window.view_selector.isEnabled() is False
        assert window.selection_label.text() == "A Minor Pentatonic"

    def test_changing_scale_while_mode_active_leaves_modal_context(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        mixolydian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "mixolydian"
        )
        window.scale_selector.setCurrentIndex(mixolydian_index)
        assert window.mode_selector.currentData() is Mode.IONIAN
        assert window.view_selector.currentData() is ModeView.PARALLEL
        assert window.view_selector.isEnabled() is False
        assert window.scale_selector.currentText() == "Mixolydian"
        assert window.selection_label.text() == "A Mixolydian"

    def test_intervals_follow_modal_root(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.selection_label.text() == "D Intervals"
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_interval_result(
            evaluate_intervals(board, PitchClass.D)
        )

    def test_triads_follow_modal_root(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["triad"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_triad_result(
            evaluate_triad(board, PitchClass.D, TriadQuality.MAJOR)
        )

    def test_mode_change_preserves_selections_and_layers(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        window.triad_quality_selector.setCurrentIndex(1)  # Minor
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.root_selector.currentText() == "C"
        assert window.triad_quality_selector.currentText() == "Minor"
        assert window.layer_checkboxes["scale"].isChecked() is True
        assert window.layer_checkboxes["interval"].isChecked() is True
        assert window.layer_checkboxes["triad"].isChecked() is True
        board = window._instrument_state.fretboard
        expected = render_scale_result(evaluate_scale(board, PitchClass.D, "dorian"))
        expected += render_interval_result(evaluate_intervals(board, PitchClass.D))
        expected += render_triad_result(evaluate_triad(board, PitchClass.D, TriadQuality.MINOR))
        assert window.fretboard_widget.annotations == expected
        assert window.selection_label.text() == (
            "D Dorian of C Major · Intervals · Minor Triads"
        )

    def test_mode_change_resets_active_voicing_to_first(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.voicing_label.text().startswith("Voicing 1 /")
        assert window._active_voicing_index == 0

    def test_mode_survives_tuning_change(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window.mode_selector.currentData() is Mode.DORIAN
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.A, "dorian")
        )
        assert window.selection_label.text() == "A Dorian"

    def test_relative_dorian_on_standard_tuning(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        assert window.tuning_selector.currentText() == "Standard"
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.D, "dorian")
        )
        assert window.selection_label.text() == "D Dorian of C Major"
        assert window.mode_label.text() == D_DORIAN_READOUT

    def test_relative_dorian_on_drop_d_tuning(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.D, "dorian")
        )
        assert window.selection_label.text() == "D Dorian of C Major"
        assert window.mode_label.text() == D_DORIAN_READOUT

    def test_relative_dorian_on_dadgad_tuning(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_selector.setCurrentIndex(_tuning_index("dadgad"))
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.D, "dorian")
        )
        assert window.selection_label.text() == "D Dorian of C Major"
        assert window.mode_label.text() == D_DORIAN_READOUT

    def test_relative_dorian_on_custom_tuning(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        assert window.tuning_selector.currentText() == "Custom"
        window.root_selector.setCurrentIndex(0)  # C
        window.mode_selector.setCurrentIndex(_mode_index("dorian"))
        window.view_selector.setCurrentIndex(_view_index(ModeView.RELATIVE))
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.D, "dorian")
        )
        assert window.selection_label.text() == "D Dorian of C Major"
        assert window.mode_label.text() == D_DORIAN_READOUT


class TestTriadQualitySelector:
    def test_quality_selector_contains_all_qualities(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.triad_quality_selector.count() == 4
        assert [window.triad_quality_selector.itemText(i) for i in range(4)] == [
            "Major",
            "Minor",
            "Diminished",
            "Augmented",
        ]
        assert window.triad_quality_selector.count() == len(available_triad_qualities())

    def test_default_quality_is_major(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.triad_quality_selector.currentIndex() == 0
        assert window.triad_quality_selector.currentText() == "Major"


class TestTriadProjection:
    def test_c_major_roles_and_labels(self) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        annotations = render_triad_result(result)
        by_position = {annotation.position: annotation for annotation in annotations}
        assert by_position[FretPosition(5, 3)].role is RenderRole.TRIAD_ROOT  # C3 root
        assert by_position[FretPosition(5, 3)].label == "1"
        assert by_position[FretPosition(6, 0)].role is RenderRole.TRIAD_TONE  # open E
        assert by_position[FretPosition(6, 0)].label == "3"
        assert by_position[FretPosition(6, 3)].role is RenderRole.TRIAD_TONE  # G2
        assert by_position[FretPosition(6, 3)].label == "5"

    def test_a_minor_flat_third_label(self) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.A, TriadQuality.MINOR)
        by_position = {
            annotation.position: annotation for annotation in render_triad_result(result)
        }
        assert by_position[FretPosition(5, 0)].role is RenderRole.TRIAD_ROOT  # open A2
        assert by_position[FretPosition(5, 0)].label == "1"
        assert by_position[FretPosition(5, 3)].role is RenderRole.TRIAD_TONE  # C3
        assert by_position[FretPosition(5, 3)].label == "b3"

    def test_c_augmented_sharp_fifth_label(self) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.AUGMENTED)
        labels = {annotation.label for annotation in render_triad_result(result)}
        assert labels == {"1", "3", "#5"}

    def test_projection_preserves_every_mapped_position(self) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        projected = render_triad_result(result)
        assert len(projected) == len(result.annotations)
        assert all(isinstance(annotation.role, RenderRole) for annotation in projected)

    def test_projection_is_qt_free(self) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        annotations = render_triad_result(result)
        assert all(
            not hasattr(annotation, "color") and not hasattr(annotation, "rect")
            for annotation in annotations
        )


class TestTriadVoicingGroupProjection:
    def test_preserves_three_positions_and_inversion(self) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        groups = render_triad_voicings(result)
        assert groups
        assert len(groups) == len(result.voicings)
        group = groups[0]
        assert isinstance(group, TriadVoicingRenderGroup)
        assert group.positions == tuple(tone.position for tone in result.voicings[0].tones)
        assert group.string_set == result.voicings[0].string_set
        assert group.inversion is result.voicings[0].inversion

    def test_group_is_ui_only_and_immutable(self) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        group = render_triad_voicings(result)[0]
        assert {field.name for field in dataclasses.fields(group)} == {
            "positions",
            "string_set",
            "inversion",
        }
        with pytest.raises(dataclasses.FrozenInstanceError):
            group.positions = ()  # type: ignore[assignment, misc]

    def test_domain_voicings_are_not_modified_by_projection(self) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        voicing = result.voicings[0]
        render_triad_voicings(result)
        assert voicing.string_set == result.voicings[0].string_set
        assert voicing.inversion is result.voicings[0].inversion
        assert tuple(tone.position for tone in voicing.tones) == tuple(
            tone.position for tone in result.voicings[0].tones
        )


class TestTriadLayerCheckbox:
    def test_triads_control_exists_and_defaults_off(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.layer_checkboxes["triad"].isChecked() is False

    def test_enabling_triads_adds_triad_point_annotations(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        expected = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_triad_result(evaluate_triad(WINDOW_TEST_BOARD, PitchClass.A, TriadQuality.MAJOR))
        assert window.fretboard_widget.annotations == expected
        assert any(
            annotation.role in (RenderRole.TRIAD_ROOT, RenderRole.TRIAD_TONE)
            for annotation in window.fretboard_widget.annotations
        )

    def test_disabling_triads_removes_them(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(False)
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        )
        assert window.fretboard_widget.voicing_group is None

    def test_changing_quality_updates_enabled_triads(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.triad_quality_selector.setCurrentIndex(1)  # Minor
        expected = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.A, "minor_pentatonic")
        ) + render_triad_result(evaluate_triad(WINDOW_TEST_BOARD, PitchClass.A, TriadQuality.MINOR))
        assert window.fretboard_widget.annotations == expected
        assert any(annotation.label == "b3" for annotation in window.fretboard_widget.annotations)

    def test_changing_quality_while_disabled_does_not_enable_triads(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.triad_quality_selector.setCurrentIndex(2)  # Diminished
        assert window.layer_checkboxes["triad"].isChecked() is False
        assert all(
            annotation.role not in (RenderRole.TRIAD_ROOT, RenderRole.TRIAD_TONE)
            for annotation in window.fretboard_widget.annotations
        )
        assert window.fretboard_widget.voicing_group is None

    def test_root_change_updates_triad_result(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        expected = render_scale_result(
            evaluate_scale(WINDOW_TEST_BOARD, PitchClass.C, "minor_pentatonic")
        ) + render_triad_result(evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR))
        assert window.fretboard_widget.annotations == expected

    def test_shared_position_retains_scale_interval_and_triad(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        plans = {plan.position: plan for plan in window.fretboard_widget._build_plan()}
        shared = plans[FretPosition(6, 0)]  # open E: scale fifth + interval fifth + triad fifth
        assert shared.primary.role is RenderRole.SCALE_TONE
        assert len(shared.badges) == 2
        assert {badge.role for badge in shared.badges} == {
            RenderRole.INTERVAL,
            RenderRole.TRIAD_TONE,
        }

    def test_headless_rendering_with_all_three_layers(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        assert not window.fretboard_widget.grab().isNull()
        assert window.fretboard_widget.voicing_group is not None

    def test_headless_rendering_each_triad_state(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        assert not window.fretboard_widget.grab().isNull()
        window.triad_quality_selector.setCurrentIndex(1)  # Minor
        assert not window.fretboard_widget.grab().isNull()
        window.triad_quality_selector.setCurrentIndex(2)  # Diminished
        assert not window.fretboard_widget.grab().isNull()
        window.triad_quality_selector.setCurrentIndex(3)  # Augmented
        assert not window.fretboard_widget.grab().isNull()


class TestVoicingNavigation:
    def test_default_active_group_is_first_voicing(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        expected_first = render_triad_voicings(
            evaluate_triad(WINDOW_TEST_BOARD, PitchClass.A, TriadQuality.MAJOR)
        )[0]
        assert window.fretboard_widget.voicing_group == expected_first
        assert window.voicing_label.text().startswith("Voicing 1 /")

    def test_next_and_previous_step_through_voicings(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 3 /")
        window.previous_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")

    def test_cycling_wraps_deterministically(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        count = len(window._triad_groups)
        assert count >= 1
        for _ in range(count - 1):
            window.next_voicing_button.click()
        assert window.voicing_label.text().startswith(f"Voicing {count} /")
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 1 /")  # wrapped forward
        window.previous_voicing_button.click()
        assert window.voicing_label.text().startswith(f"Voicing {count} /")  # wrapped backward

    def test_voicing_label_describes_inversion_and_strings(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        count = len(window._triad_groups)
        group = window._triad_groups[0]
        assert window.voicing_label.text() == (
            f"Voicing 1 / {count} — {group.inversion.display_name} — "
            f"strings {'-'.join(str(string) for string in group.string_set)}"
        )

    def test_root_change_resets_active_voicing_to_first(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.root_selector.setCurrentIndex(0)  # C
        assert window.voicing_label.text().startswith("Voicing 1 /")

    def test_quality_change_resets_active_voicing_to_first(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.triad_quality_selector.setCurrentIndex(1)  # Minor
        assert window.voicing_label.text().startswith("Voicing 1 /")

    def test_toggling_unrelated_layers_preserves_active_voicing(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.layer_checkboxes["interval"].setChecked(True)
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.layer_checkboxes["scale"].setChecked(False)
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.layer_checkboxes["scale"].setChecked(True)
        assert window.voicing_label.text().startswith("Voicing 2 /")

    def test_toggling_triads_off_and_on_preserves_active_voicing(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.layer_checkboxes["triad"].setChecked(False)
        assert window.voicing_label.text() == ""
        assert window.fretboard_widget.voicing_group is None
        assert window.next_voicing_button.isEnabled() is False
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.voicing_label.text().startswith("Voicing 2 /")
        assert window._active_voicing_index == 1

    def test_no_voicing_state(self, qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
        empty = TriadLayerResult("triad", "Triads", (), ())
        monkeypatch.setattr(main_window_module, "evaluate_triad", lambda *args, **kwargs: empty)
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.voicing_label.text() == "No triad voicings"
        assert window.fretboard_widget.voicing_group is None
        assert window.previous_voicing_button.isEnabled() is False
        assert window.next_voicing_button.isEnabled() is False

    def test_no_voicing_state_keeps_point_annotations(
        self, qapp: QApplication, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.A, TriadQuality.MAJOR)
        empty_voicings = TriadLayerResult("triad", "Triads", real.annotations, ())
        monkeypatch.setattr(
            main_window_module, "evaluate_triad", lambda *args, **kwargs: empty_voicings
        )
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        assert window.voicing_label.text() == "No triad voicings"
        assert any(
            annotation.role in (RenderRole.TRIAD_ROOT, RenderRole.TRIAD_TONE)
            for annotation in window.fretboard_widget.annotations
        )
        assert not window.fretboard_widget.grab().isNull()


class TestVoicingGroupWidget:
    def test_widget_accepts_voicing_group(self, qapp: QApplication) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        groups = render_triad_voicings(result)
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, render_triad_result(result))
        widget.set_voicing_group(groups[0])
        assert widget.voicing_group == groups[0]
        pixmap = widget.grab()
        assert not pixmap.isNull()

    def test_widget_draws_group_without_altering_domain_objects(self, qapp: QApplication) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        voicing = result.voicings[0]
        positions_before = tuple(tone.position for tone in voicing.tones)
        groups = render_triad_voicings(result)
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, render_triad_result(result))
        widget.set_voicing_group(groups[0])
        pixmap = widget.grab()
        assert not pixmap.isNull()
        assert tuple(tone.position for tone in voicing.tones) == positions_before
        assert voicing.inversion is result.voicings[0].inversion
        assert groups[0].positions == positions_before

    def test_widget_clears_voicing_group(self, qapp: QApplication) -> None:
        result = evaluate_triad(WINDOW_TEST_BOARD, PitchClass.C, TriadQuality.MAJOR)
        groups = render_triad_voicings(result)
        widget = FretboardWidget()
        widget.set_annotations(WINDOW_TEST_BOARD, render_triad_result(result))
        widget.set_voicing_group(groups[0])
        widget.set_voicing_group(None)
        assert widget.voicing_group is None
        assert not widget.grab().isNull()


class TestTuningSelector:
    def test_tuning_selector_populated_from_catalog(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.tuning_selector.count() == len(available_tunings()) + 1
        assert [
            window.tuning_selector.itemText(i) for i in range(window.tuning_selector.count())
        ] == [named.name for named in available_tunings()] + ["Custom"]
        assert window.tuning_selector.itemData(window.tuning_selector.count() - 1) is None

    def test_default_tuning_is_standard(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.tuning_selector.currentText() == "Standard"
        assert window._instrument_state.tuning_id == "standard"
        assert window._instrument_state.fretboard == DEFAULT_INSTRUMENT_STATE.fretboard
        assert window.fretboard_widget.fretboard == DEFAULT_INSTRUMENT_STATE.fretboard
        assert window.tuning_label.text() == "Tuning: Standard"

    def test_switching_to_drop_d_updates_state_and_annotations(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(True)
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window._instrument_state.tuning_id == "drop_d"
        assert window.tuning_label.text() == "Tuning: Drop D"
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.fretboard == board
        assert window.fretboard_widget.annotations == render_interval_result(
            evaluate_intervals(board, PitchClass.A)
        )

    def test_tuning_change_preserves_fret_count(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window._instrument_state.fret_count == DEFAULT_INSTRUMENT_STATE.fret_count
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window._instrument_state.fret_count == DEFAULT_INSTRUMENT_STATE.fret_count
        assert window._instrument_state.fretboard == Fretboard(
            DROP_D_TUNING.tuning, DEFAULT_INSTRUMENT_STATE.fret_count
        )

    def test_tuning_change_preserves_selections_and_layers(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        window.triad_quality_selector.setCurrentIndex(1)  # Minor
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window.root_selector.currentText() == "C"
        assert window.scale_selector.currentText() == MINOR_PENTATONIC.name
        assert window.triad_quality_selector.currentText() == "Minor"
        assert window.layer_checkboxes["scale"].isChecked() is True
        assert window.layer_checkboxes["interval"].isChecked() is True
        assert window.layer_checkboxes["triad"].isChecked() is True
        board = window._instrument_state.fretboard
        expected = render_scale_result(evaluate_scale(board, PitchClass.C, "minor_pentatonic"))
        expected += render_interval_result(evaluate_intervals(board, PitchClass.C))
        expected += render_triad_result(evaluate_triad(board, PitchClass.C, TriadQuality.MINOR))
        assert window.fretboard_widget.annotations == expected
        assert window.selection_label.text() == "C Minor Pentatonic · Intervals · Minor Triads"

    def test_tuning_change_re_evaluates_scale_with_concrete_frets(self, qapp: QApplication) -> None:
        window = MainWindow()
        by_fret = {
            annotation.position: annotation for annotation in window.fretboard_widget.annotations
        }
        assert by_fret[FretPosition(6, 0)].label == "5"  # open E: fifth of A minor pentatonic
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        by_fret = {
            annotation.position: annotation for annotation in window.fretboard_widget.annotations
        }
        assert by_fret[FretPosition(6, 0)].label == "4"  # open D: fourth of A minor pentatonic

    def test_tuning_change_re_evaluates_interval_labels(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(True)
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        by_fret = {
            annotation.position: annotation for annotation in window.fretboard_widget.annotations
        }
        assert by_fret[FretPosition(6, 0)].role is RenderRole.INTERVAL
        assert by_fret[FretPosition(6, 0)].label == "4"  # A to open D: perfect fourth
        assert by_fret[FretPosition(5, 0)].role is RenderRole.INTERVAL_ROOT
        assert by_fret[FretPosition(5, 0)].label == "R"  # open A: the root

    def test_tuning_change_re_evaluates_triad_positions(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["triad"].setChecked(True)
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        by_fret = {
            annotation.position: annotation for annotation in window.fretboard_widget.annotations
        }
        assert by_fret[FretPosition(5, 0)].role is RenderRole.TRIAD_ROOT  # open A2
        assert by_fret[FretPosition(5, 0)].label == "1"
        assert by_fret[FretPosition(4, 2)].role is RenderRole.TRIAD_TONE  # D3 + 2 = E3
        assert by_fret[FretPosition(4, 2)].label == "5"
        assert by_fret[FretPosition(6, 2)].role is RenderRole.TRIAD_TONE  # D2 + 2 = E2
        assert by_fret[FretPosition(6, 2)].label == "5"

    def test_tuning_change_resets_active_voicing_to_first(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window.voicing_label.text().startswith("Voicing 1 /")
        assert window._active_voicing_index == 0

    def test_switching_back_to_standard_restores_its_voicings(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        standard_groups = window._triad_groups
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window.voicing_label.text().startswith("Voicing 1 /")
        window.tuning_selector.setCurrentIndex(_tuning_index("standard"))
        assert window.voicing_label.text().startswith("Voicing 1 /")
        assert window._triad_groups == standard_groups

    def test_tuning_label_uses_preset_display_name(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.tuning_label.text() == "Tuning: Standard"
        window.tuning_selector.setCurrentIndex(_tuning_index("dadgad"))
        assert window.tuning_label.text() == "Tuning: DADGAD"
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window.tuning_label.text() == "Tuning: Drop D"

    def test_headless_rendering_after_tuning_change(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert not window.fretboard_widget.grab().isNull()
        window.tuning_selector.setCurrentIndex(_tuning_index("dadgad"))
        assert not window.fretboard_widget.grab().isNull()

    def test_main_window_has_no_fixed_standard_board(self) -> None:
        module = inspect.getmodule(MainWindow)
        assert module is not None and module.__file__ is not None
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "STANDARD_BOARD" not in source


class TestCustomTuningEditor:
    STANDARD_PITCHES = (
        Pitch(PitchClass.E, 2),
        Pitch(PitchClass.A, 2),
        Pitch(PitchClass.D, 3),
        Pitch(PitchClass.G, 3),
        Pitch(PitchClass.B, 3),
        Pitch(PitchClass.E, 4),
    )

    def test_editor_initially_reflects_standard(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.tuning_editor.read_pitches() == self.STANDARD_PITCHES

    def test_editor_is_hidden_by_default_and_toggleable(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window._tuning_editor_open is False
        assert window.tuning_editor_button.text() == "Edit Tuning…"
        window.tuning_editor_button.click()
        assert window._tuning_editor_open is True
        assert window.tuning_editor.isHidden() is False
        assert window.tuning_editor_button.text() == "Hide Tuning Editor"
        window.tuning_editor_button.click()
        assert window._tuning_editor_open is False
        assert window.tuning_editor_button.text() == "Edit Tuning…"

    def test_selecting_drop_d_repopulates_editor(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window.tuning_editor.read_pitches() == tuple(
            string.open_pitch for string in DROP_D_TUNING.tuning.strings
        )

    def test_selecting_dadgad_repopulates_editor(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_selector.setCurrentIndex(_tuning_index("dadgad"))
        assert window.tuning_editor.read_pitches() == tuple(
            string.open_pitch for string in DADGAD_TUNING.tuning.strings
        )

    def test_editing_one_string_does_not_affect_active_state_until_apply(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        state_before = window._instrument_state
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        assert window._instrument_state is state_before
        assert window._instrument_state.tuning_id == "standard"
        assert window.fretboard_widget.fretboard is not None
        assert window.fretboard_widget.fretboard.tuning is state_before.tuning
        assert window.tuning_selector.currentText() == "Standard"

    def test_editing_string_shows_pending_status_message(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        assert "Apply Tuning" in window.statusBar().currentMessage()

    def test_apply_standard_edit_makes_drop_d_equivalent_custom(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        state = window._instrument_state
        assert state.tuning_id is None
        assert state.display_name == "Custom"
        assert window.tuning_selector.currentText() == "Custom"
        assert window.tuning_label.text() == "Tuning: Custom"
        assert tuple(string.open_pitch for string in state.tuning.strings) == tuple(
            string.open_pitch for string in DROP_D_TUNING.tuning.strings
        )
        assert state.fret_count == DEFAULT_INSTRUMENT_STATE.fret_count
        assert state.fretboard.pitch_at(6, 0) == Pitch(PitchClass.D, 2)

    def test_custom_state_is_not_identified_as_preset_drop_d(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        assert window._instrument_state.tuning_id is None
        assert window._instrument_state.display_name == "Custom"
        assert window._instrument_state.tuning is not DROP_D_TUNING.tuning
        assert window.tuning_selector.currentText() == "Custom"

    def test_scale_recomputes_from_custom_tuning(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.fretboard == board
        assert window.fretboard_widget.annotations == render_scale_result(
            evaluate_scale(board, PitchClass.A, "minor_pentatonic")
        )
        by_fret = {
            annotation.position: annotation for annotation in window.fretboard_widget.annotations
        }
        assert by_fret[FretPosition(6, 0)].label == "4"

    def test_intervals_recompute_from_custom_tuning(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["interval"].setChecked(True)
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_interval_result(
            evaluate_intervals(board, PitchClass.A)
        )
        by_fret = {
            annotation.position: annotation for annotation in window.fretboard_widget.annotations
        }
        assert by_fret[FretPosition(6, 0)].label == "4"

    def test_triads_recompute_from_custom_tuning(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["scale"].setChecked(False)
        window.layer_checkboxes["triad"].setChecked(True)
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        board = window._instrument_state.fretboard
        assert window.fretboard_widget.annotations == render_triad_result(
            evaluate_triad(board, PitchClass.A, TriadQuality.MAJOR)
        )
        by_fret = {
            annotation.position: annotation for annotation in window.fretboard_widget.annotations
        }
        assert by_fret[FretPosition(6, 2)].label == "5"

    def test_voicings_reset_to_first_on_apply(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["triad"].setChecked(True)
        window.next_voicing_button.click()
        assert window.voicing_label.text().startswith("Voicing 2 /")
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        assert window.voicing_label.text().startswith("Voicing 1 /")
        assert window._active_voicing_index == 0

    def test_apply_preserves_selections_and_layer_toggles(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        window.root_selector.setCurrentIndex(0)  # C
        window.triad_quality_selector.setCurrentIndex(1)  # Minor
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        assert window.root_selector.currentText() == "C"
        assert window.scale_selector.currentText() == MINOR_PENTATONIC.name
        assert window.triad_quality_selector.currentText() == "Minor"
        assert window.layer_checkboxes["scale"].isChecked() is True
        assert window.layer_checkboxes["interval"].isChecked() is True
        assert window.layer_checkboxes["triad"].isChecked() is True
        board = window._instrument_state.fretboard
        expected = render_scale_result(evaluate_scale(board, PitchClass.C, "minor_pentatonic"))
        expected += render_interval_result(evaluate_intervals(board, PitchClass.C))
        expected += render_triad_result(evaluate_triad(board, PitchClass.C, TriadQuality.MINOR))
        assert window.fretboard_widget.annotations == expected
        assert window.selection_label.text() == ("C Minor Pentatonic · Intervals · Minor Triads")

    def test_returning_to_preset_restores_identity_and_display_name(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        assert window._instrument_state.tuning_id is None
        window.tuning_selector.setCurrentIndex(_tuning_index("drop_d"))
        assert window._instrument_state.tuning_id == "drop_d"
        assert window._instrument_state.display_name == "Drop D"
        assert window.tuning_label.text() == "Tuning: Drop D"
        assert window.tuning_selector.currentText() == "Drop D"
        assert window.tuning_editor.read_pitches() == tuple(
            string.open_pitch for string in DROP_D_TUNING.tuning.strings
        )

    def test_selecting_custom_item_without_custom_tuning_snaps_back(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.tuning_selector.setCurrentIndex(window._custom_tuning_index)
        assert window.tuning_selector.currentText() == "Standard"
        assert window._instrument_state.tuning_id == "standard"

    def test_headless_rendering_after_custom_apply(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.layer_checkboxes["interval"].setChecked(True)
        window.layer_checkboxes["triad"].setChecked(True)
        window.tuning_editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        window.tuning_editor.apply_button.click()
        assert not window.fretboard_widget.grab().isNull()
        window.tuning_selector.setCurrentIndex(_tuning_index("dadgad"))
        assert not window.fretboard_widget.grab().isNull()
