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

    def test_custom_tuning(self) -> None:
        tuning = Tuning(
            "Drop D (3-string example)",
            (
                GuitarString(3, Pitch(PitchClass.D, 2)),
                GuitarString(2, Pitch(PitchClass.A, 2)),
                GuitarString(1, Pitch(PitchClass.E, 4)),
            ),
        )
        assert tuning.string_count == 3
        assert tuning.string(3).open_pitch == Pitch(PitchClass.D, 2)
        assert tuning.string(1).open_pitch == Pitch(PitchClass.E, 4)


class TestStringNumbering:
    def test_standard_tuning_numbering_is_exactly_1_to_6(self) -> None:
        assert {s.number for s in STANDARD.strings} == set(range(1, 7))

    def test_single_string_tuning_numbered_1_is_valid(self) -> None:
        tuning = Tuning("single", (GuitarString(1, Pitch(PitchClass.E, 4)),))
        assert tuning.string_count == 1

    def test_seven_string_tuning_numbered_1_to_7_is_valid(self) -> None:
        strings = tuple(GuitarString(n, Pitch(PitchClass.C, 2)) for n in range(1, 8))
        tuning = Tuning("7-string", strings)
        assert tuning.string_count == 7
        assert {s.number for s in tuning.strings} == set(range(1, 8))

    def test_low_to_high_stored_order_remains_valid(self) -> None:
        tuning = Tuning(
            "Low to high order",
            (
                GuitarString(3, Pitch(PitchClass.G, 2)),
                GuitarString(2, Pitch(PitchClass.D, 3)),
                GuitarString(1, Pitch(PitchClass.G, 3)),
            ),
        )
        assert [s.number for s in tuning.strings] == [3, 2, 1]

    @pytest.mark.parametrize(
        ("numbers", "label"),
        [
            ((1, 1), "duplicate numbers"),
            ((1, 3), "missing number"),
            ((2, 3), "numbering starting at 2"),
            ((0, 1, 2), "numbering containing 0"),
            ((1, 2, 4), "non-contiguous numbering"),
        ],
    )
    def test_malformed_numbering_rejected(self, numbers: tuple[int, ...], label: str) -> None:
        with pytest.raises(InvalidTuningError):
            strings = tuple(GuitarString(n, Pitch(PitchClass.E, 2)) for n in numbers)
            Tuning(label, strings)
