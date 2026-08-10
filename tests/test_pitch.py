"""Tests for PitchClass and Pitch."""

import pytest

from guitar_app.core.errors import InvalidPitchError
from guitar_app.core.theory.pitch import Pitch, PitchClass


class TestPitchClass:
    def test_twelve_members(self) -> None:
        assert len(PitchClass) == 12

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("C", PitchClass.C),
            ("C#", PitchClass.CSHARP),
            ("Db", PitchClass.CSHARP),
            ("D", PitchClass.D),
            ("E", PitchClass.E),
            ("F", PitchClass.F),
            ("F#", PitchClass.FSHARP),
            ("Gb", PitchClass.FSHARP),
            ("G", PitchClass.G),
            ("G#", PitchClass.GSHARP),
            ("A", PitchClass.A),
            ("Bb", PitchClass.ASHARP),
            ("B", PitchClass.B),
            ("c#", PitchClass.CSHARP),
            ("f♯", PitchClass.FSHARP),
            ("e♭", PitchClass.DSHARP),
        ],
    )
    def test_from_name(self, name: str, expected: PitchClass) -> None:
        assert PitchClass.from_name(name) == expected

    @pytest.mark.parametrize("name", ["", " ", "H", "C#b", "H#", "##", "1"])
    def test_from_name_rejects_invalid(self, name: str) -> None:
        with pytest.raises(InvalidPitchError):
            PitchClass.from_name(name)

    def test_sharp_spelling(self) -> None:
        assert PitchClass.CSHARP.spelling() == "C#"
        assert PitchClass.ASHARP.spelling() == "A#"
        assert PitchClass.F.spelling() == "F"

    def test_values_are_normalized_semitones(self) -> None:
        assert int(PitchClass.G) == 7
        assert int(PitchClass.B) == 11
        assert PitchClass.from_name("Cb") == PitchClass.B


class TestPitch:
    def test_middle_c_midi_number(self) -> None:
        assert Pitch(PitchClass.C, 4).midi == 60

    def test_standard_guitar_open_pitch_midi_numbers(self) -> None:
        assert Pitch(PitchClass.E, 2).midi == 40
        assert Pitch(PitchClass.A, 2).midi == 45
        assert Pitch(PitchClass.D, 3).midi == 50
        assert Pitch(PitchClass.G, 3).midi == 55
        assert Pitch(PitchClass.B, 3).midi == 59
        assert Pitch(PitchClass.E, 4).midi == 64

    def test_from_midi_roundtrip(self) -> None:
        for midi in range(0, 127, 7):
            assert Pitch.from_midi(midi).midi == midi

    def test_from_midi_middle_c(self) -> None:
        assert Pitch.from_midi(60) == Pitch(PitchClass.C, 4)

    def test_transpose_up_one_octave(self) -> None:
        assert Pitch(PitchClass.E, 2).transpose(12) == Pitch(PitchClass.E, 3)

    def test_transpose_a_to_c_across_octave_boundary(self) -> None:
        assert Pitch(PitchClass.A, 2).transpose(3) == Pitch(PitchClass.C, 3)

    def test_transpose_b_to_c(self) -> None:
        assert Pitch(PitchClass.B, 3).transpose(1) == Pitch(PitchClass.C, 4)

    def test_pitch_classes_repeat_every_12_semitones(self) -> None:
        for octave in range(1, 5):
            start = Pitch(PitchClass.G, octave)
            assert start.transpose(12) == Pitch(PitchClass.G, octave + 1)
            assert start.transpose(12).pitch_class == start.pitch_class

    def test_transpose_down(self) -> None:
        assert Pitch(PitchClass.C, 4).transpose(-12) == Pitch(PitchClass.C, 3)
        assert Pitch(PitchClass.C, 4).transpose(-13) == Pitch(PitchClass.B, 2)

    def test_str(self) -> None:
        assert str(Pitch(PitchClass.E, 2)) == "E2"
        assert str(Pitch(PitchClass.CSHARP, 4)) == "C#4"
