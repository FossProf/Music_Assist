"""Tests for the PySide6 vertical slice: selectors, window wiring, and geometry."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.scale_mapping import ScaleFretboardPosition
from guitar_app.core.instrument.tuning import STANDARD
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale_formulas import MINOR_PENTATONIC, SCALE_FORMULAS
from guitar_app.services.scale_service import available_scale_formulas, evaluate_scale
from guitar_app.ui.fretboard_widget import FretboardWidget
from guitar_app.ui.geometry import FRET_MARKERS, FretboardGeometry, fretboard_geometry
from guitar_app.ui.main_window import STANDARD_BOARD, MainWindow


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
    def test_accepts_layer_result_data(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        result = evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        widget.set_fretboard_data(STANDARD_BOARD, result)
        assert widget.fretboard == STANDARD_BOARD
        assert widget.result == result

    def test_accepts_empty_annotations(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        empty: LayerResult[ScaleFretboardPosition] = LayerResult("scale", "Scale", ())
        widget.set_fretboard_data(STANDARD_BOARD, empty)
        assert widget.result is not None
        assert widget.result.annotations == ()

    def test_replaces_previous_data(self, qapp: QApplication) -> None:
        widget = FretboardWidget()
        first = evaluate_scale(STANDARD_BOARD, PitchClass.A, "minor_pentatonic")
        second = evaluate_scale(STANDARD_BOARD, PitchClass.C, "major")
        widget.set_fretboard_data(STANDARD_BOARD, first)
        assert widget.result == first
        widget.set_fretboard_data(STANDARD_BOARD, second)
        assert widget.result == second

    def test_renders_fretboard_shorter_than_twelve_frets(self, qapp: QApplication) -> None:
        short_board = Fretboard(STANDARD, 5)
        widget = FretboardWidget()
        widget.set_fretboard_data(
            short_board, evaluate_scale(short_board, PitchClass.A, "minor_pentatonic")
        )
        assert widget.result is not None
        assert all(annotation.position.fret <= 5 for annotation in widget.result.annotations)
        pixmap = widget.grab()
        assert not pixmap.isNull()


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
        assert window.fretboard_widget.result == evaluate_scale(
            STANDARD_BOARD, PitchClass.A, "minor_pentatonic"
        )

    def test_changing_root_and_scale_re_evaluates(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.root_selector.setCurrentIndex(0)  # C
        window.scale_selector.setCurrentIndex(0)  # Major
        assert window.selection_label.text() == "C Major"
        assert window.fretboard_widget.result == evaluate_scale(
            STANDARD_BOARD, PitchClass.C, "major"
        )

    def test_changing_scale_alone_re_evaluates(self, qapp: QApplication) -> None:
        window = MainWindow()
        dorian_index = next(
            i for i, named in enumerate(available_scale_formulas()) if named.id == "dorian"
        )
        window.scale_selector.setCurrentIndex(dorian_index)
        assert window.selection_label.text() == "A Dorian"
        assert window.fretboard_widget.result == evaluate_scale(
            STANDARD_BOARD, PitchClass.A, "dorian"
        )

    def test_evaluated_annotations_stay_within_bounds(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window.fretboard_widget.result is not None
        for annotation in window.fretboard_widget.result.annotations:
            assert 1 <= annotation.position.string_number <= 6
            assert 0 <= annotation.position.fret <= 12
