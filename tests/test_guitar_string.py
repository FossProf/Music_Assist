"""Tests for GuitarString physics."""

import pytest

from guitar_app.core.errors import InvalidPositionError, InvalidTuningError
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.theory.pitch import Pitch, PitchClass

LOW_E = GuitarString(6, Pitch(PitchClass.E, 2))


class TestPitchAt:
    def test_open_fret_is_open_pitch(self) -> None:
        assert LOW_E.pitch_at(0) == Pitch(PitchClass.E, 2)

    def test_fret_12_repeats_the_octave(self) -> None:
        assert LOW_E.pitch_at(12) == Pitch(PitchClass.E, 3)

    def test_each_fret_rises_one_semitone(self) -> None:
        for fret in range(0, 12):
            assert LOW_E.pitch_at(fret + 1).midi == LOW_E.pitch_at(fret).midi + 1

    def test_pitch_classes_wrap_after_b(self) -> None:
        assert LOW_E.pitch_class_at(0) == PitchClass.E
        assert LOW_E.pitch_class_at(1) == PitchClass.F
        assert LOW_E.pitch_class_at(12) == PitchClass.E

    def test_negative_fret_rejected(self) -> None:
        with pytest.raises(InvalidPositionError):
            LOW_E.pitch_at(-1)


class TestNumbering:
    def test_string_number_zero_rejected(self) -> None:
        with pytest.raises(InvalidTuningError):
            GuitarString(0, Pitch(PitchClass.E, 2))

    def test_string_number_negative_rejected(self) -> None:
        with pytest.raises(InvalidTuningError):
            GuitarString(-3, Pitch(PitchClass.E, 2))
