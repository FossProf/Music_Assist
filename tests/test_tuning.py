"""Tests for Tuning and the standard tuning preset."""

import pytest

from guitar_app.core.errors import InvalidTuningError
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.theory.pitch import Pitch, PitchClass


class TestStandardTuning:
    def test_has_six_strings(self) -> None:
        assert STANDARD.string_count == 6

    def test_open_pitches_match_eadgbe(self) -> None:
        expected = {
            6: Pitch(PitchClass.E, 2),
            5: Pitch(PitchClass.A, 2),
            4: Pitch(PitchClass.D, 3),
            3: Pitch(PitchClass.G, 3),
            2: Pitch(PitchClass.B, 3),
            1: Pitch(PitchClass.E, 4),
        }
        for number, pitch in expected.items():
            assert STANDARD.string(number).open_pitch == pitch

    def test_string_lookup(self) -> None:
        assert STANDARD.string(1).number == 1
        assert STANDARD.string(6).number == 6

    def test_unknown_string_number_rejected(self) -> None:
        with pytest.raises(InvalidTuningError):
            STANDARD.string(7)
        with pytest.raises(InvalidTuningError):
            STANDARD.string(0)

    def test_strings_ordered_low_to_high(self) -> None:
        numbers = [s.number for s in STANDARD.strings]
        assert numbers == [6, 5, 4, 3, 2, 1]


class TestTuningValidation:
    def test_empty_tuning_rejected(self) -> None:
        with pytest.raises(InvalidTuningError):
            Tuning("empty", ())

    def test_duplicate_string_numbers_rejected(self) -> None:
        strings = (
            GuitarString(1, Pitch(PitchClass.E, 4)),
            GuitarString(1, Pitch(PitchClass.E, 4)),
        )
        with pytest.raises(InvalidTuningError):
            Tuning("duplicate", strings)

    def test_custom_tuning(self) -> None:
        tuning = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                GuitarString(5, Pitch(PitchClass.A, 2)),
                GuitarString(1, Pitch(PitchClass.E, 4)),
            ),
        )
        assert tuning.string_count == 3
        assert tuning.string(6).open_pitch == Pitch(PitchClass.D, 2)
        assert tuning.string(1).open_pitch == Pitch(PitchClass.E, 4)
