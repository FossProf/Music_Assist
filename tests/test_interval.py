"""Tests for Interval and pitch-class interval math."""

import pytest

from guitar_app.core.theory.interval import Interval, interval_between
from guitar_app.core.theory.pitch import PitchClass


class TestIntervalSizes:
    @pytest.mark.parametrize(
        ("interval", "semitones"),
        [
            (Interval.UNISON, 0),
            (Interval.MINOR_SECOND, 1),
            (Interval.MAJOR_SECOND, 2),
            (Interval.MINOR_THIRD, 3),
            (Interval.MAJOR_THIRD, 4),
            (Interval.PERFECT_FOURTH, 5),
            (Interval.TRITONE, 6),
            (Interval.PERFECT_FIFTH, 7),
            (Interval.MINOR_SIXTH, 8),
            (Interval.MAJOR_SIXTH, 9),
            (Interval.MINOR_SEVENTH, 10),
            (Interval.MAJOR_SEVENTH, 11),
            (Interval.OCTAVE, 12),
        ],
    )
    def test_semitone_sizes(self, interval: Interval, semitones: int) -> None:
        assert interval.semitones == semitones
        assert int(interval) == semitones

    def test_perfect_fifth_is_seven_semitones(self) -> None:
        assert Interval.PERFECT_FIFTH.semitones == 7

    def test_major_third_is_four_semitones(self) -> None:
        assert Interval.MAJOR_THIRD.semitones == 4

    def test_minor_third_is_three_semitones(self) -> None:
        assert Interval.MINOR_THIRD.semitones == 3


class TestAbbreviations:
    def test_common_abbreviations(self) -> None:
        assert Interval.UNISON.abbreviation == "R"
        assert Interval.MINOR_THIRD.abbreviation == "b3"
        assert Interval.MAJOR_THIRD.abbreviation == "3"
        assert Interval.PERFECT_FIFTH.abbreviation == "5"
        assert Interval.OCTAVE.abbreviation == "8"


class TestIntervalBetween:
    def test_relative_to_fourth_and_fifth(self) -> None:
        assert interval_between(PitchClass.E, PitchClass.A) == Interval.PERFECT_FOURTH
        assert interval_between(PitchClass.A, PitchClass.E) == Interval.PERFECT_FIFTH

    def test_unison(self) -> None:
        assert interval_between(PitchClass.A, PitchClass.A) == Interval.UNISON

    def test_tritone(self) -> None:
        assert interval_between(PitchClass.C, PitchClass.FSHARP) == Interval.TRITONE
        assert interval_between(PitchClass.FSHARP, PitchClass.C) == Interval.TRITONE

    def test_major_scale_relations_from_c(self) -> None:
        assert interval_between(PitchClass.C, PitchClass.C) == Interval.UNISON
        assert interval_between(PitchClass.C, PitchClass.D) == Interval.MAJOR_SECOND
        assert interval_between(PitchClass.C, PitchClass.E) == Interval.MAJOR_THIRD
        assert interval_between(PitchClass.C, PitchClass.F) == Interval.PERFECT_FOURTH
        assert interval_between(PitchClass.C, PitchClass.G) == Interval.PERFECT_FIFTH
        assert interval_between(PitchClass.C, PitchClass.A) == Interval.MAJOR_SIXTH
        assert interval_between(PitchClass.C, PitchClass.B) == Interval.MAJOR_SEVENTH

    def test_ascending_intervals_complement_to_octave(self) -> None:
        for source in PitchClass:
            for target in PitchClass:
                up = interval_between(source, target)
                down = interval_between(target, source)
                assert (int(up) + int(down)) % 12 == 0

    def test_interval_is_always_between_zero_and_eleven(self) -> None:
        for source in PitchClass:
            for target in PitchClass:
                assert 0 <= int(interval_between(source, target)) <= 11
