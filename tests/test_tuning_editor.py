"""Tests for the custom-tuning string editor widget."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.ui.tuning_editor import OCTAVE_MAX, OCTAVE_MIN, CustomTuningEditor


def _standard_pitches() -> tuple[Pitch, ...]:
    return (
        Pitch(PitchClass.E, 2),
        Pitch(PitchClass.A, 2),
        Pitch(PitchClass.D, 3),
        Pitch(PitchClass.G, 3),
        Pitch(PitchClass.B, 3),
        Pitch(PitchClass.E, 4),
    )


class TestEditorStructure:
    def test_rows_run_lowest_string_to_highest(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        assert editor.string_numbers() == (6, 5, 4, 3, 2, 1)

    def test_each_row_has_pitch_class_and_octave_controls(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        assert len(editor.pitch_class_combos) == 6
        assert len(editor.octave_spins) == 6

    def test_pitch_class_selectors_offer_normalized_spellings(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        spellings = [pitch_class.spelling() for pitch_class in PitchClass]
        for combo in editor.pitch_class_combos:
            assert [combo.itemText(i) for i in range(combo.count())] == spellings

    def test_octave_selectors_are_small_octave_numbers(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        for spin in editor.octave_spins:
            assert spin.minimum() == OCTAVE_MIN
            assert spin.maximum() == OCTAVE_MAX


class TestEditorValues:
    def test_set_pitches_reads_back_low_to_high(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        assert editor.read_pitches() == _standard_pitches()

    def test_set_string_pitch_updates_only_that_string(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        assert editor.pitch_for_string(6) == Pitch(PitchClass.D, 2)
        assert editor.pitch_for_string(5) == Pitch(PitchClass.A, 2)
        assert editor.read_pitches() == (
            Pitch(PitchClass.D, 2),
            Pitch(PitchClass.A, 2),
            Pitch(PitchClass.D, 3),
            Pitch(PitchClass.G, 3),
            Pitch(PitchClass.B, 3),
            Pitch(PitchClass.E, 4),
        )

    def test_pitch_class_and_octave_are_independent(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        editor.set_string_pitch(1, Pitch(PitchClass.D, 5))
        assert editor.pitch_for_string(1) == Pitch(PitchClass.D, 5)
        assert editor.pitch_for_string(2) == Pitch(PitchClass.B, 3)

    def test_unknown_string_number_rejected(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        with pytest.raises(ValueError):
            editor.pitch_for_string(7)

    def test_pitch_class_selector_data_round_trips(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        assert PitchClass(editor.pitch_class_combos[0].currentData()) == PitchClass.E

    def test_string_count_rebuilds_rows(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        editor.set_pitches((Pitch(PitchClass.C, 2), Pitch(PitchClass.G, 3)))
        assert editor.string_numbers() == (2, 1)
        assert editor.read_pitches() == (
            Pitch(PitchClass.C, 2),
            Pitch(PitchClass.G, 3),
        )


class TestEditorSignals:
    def test_set_pitches_does_not_emit_edited(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        fired: list[bool] = []
        editor.edited.connect(lambda: fired.append(True))
        editor.set_pitches(_standard_pitches())
        assert fired == []

    def test_set_string_pitch_emits_edited(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        fired: list[bool] = []
        editor.edited.connect(lambda: fired.append(True))
        editor.set_string_pitch(6, Pitch(PitchClass.D, 2))
        assert fired == [True]

    def test_apply_button_emits_apply_requested(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        fired: list[bool] = []
        editor.apply_requested.connect(lambda: fired.append(True))
        editor.apply_button.click()
        assert fired == [True]


class TestEditorRendering:
    def test_headless_rendering_succeeds(self, qapp: QApplication) -> None:
        editor = CustomTuningEditor()
        editor.set_pitches(_standard_pitches())
        editor.show()
        assert not editor.grab().isNull()
