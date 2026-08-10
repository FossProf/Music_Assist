"""Tests for ChromaticInterval and chromatic displacement math."""

import pytest

from guitar_app.core.theory.chromatic_interval import (
    ChromaticInterval,
    chromatic_interval_between,
)
from guitar_app.core.theory.pitch import PitchClass


class TestChromaticInterval:
    def test_twelve_members_from_zero_to_eleven(self) -> None:
        assert len(ChromaticInterval) == 12
        assert [int(member) for member in ChromaticInterval] == list(range(12))

    def test_no_octave_member(self) -> None:
        assert not hasattr(ChromaticInterval, "OCTAVE")
        with pytest.raises(ValueError):
            ChromaticInterval(12)

    @pytest.mark.parametrize(
        ("interval", "semitones"),
        [
            (ChromaticInterval.UNISON, 0),
            (ChromaticInterval.MINOR_SECOND, 1),
            (ChromaticInterval.MAJOR_SECOND, 2),
            (ChromaticInterval.MINOR_THIRD, 3),
            (ChromaticInterval.MAJOR_THIRD, 4),
            (ChromaticInterval.PERFECT_FOURTH, 5),
            (ChromaticInterval.TRITONE, 6),
            (ChromaticInterval.PERFECT_FIFTH, 7),
            (ChromaticInterval.MINOR_SIXTH, 8),
            (ChromaticInterval.MAJOR_SIXTH, 9),
            (ChromaticInterval.MINOR_SEVENTH, 10),
            (ChromaticInterval.MAJOR_SEVENTH, 11),
        ],
    )
    def test_semitone_sizes(self, interval: ChromaticInterval, semitones: int) -> None:
        assert interval.semitones == semitones
        assert int(interval) == semitones

    def test_perfect_fifth_is_seven_semitones(self) -> None:
        assert ChromaticInterval.PERFECT_FIFTH.semitones == 7

    def test_major_third_is_four_semitones(self) -> None:
        assert ChromaticInterval.MAJOR_THIRD.semitones == 4

    def test_minor_third_is_three_semitones(self) -> None:
        assert ChromaticInterval.MINOR_THIRD.semitones == 3


class TestAbbreviations:
    def test_fretboard_analysis_labels(self) -> None:
        expected = {
            ChromaticInterval.UNISON: "R",
            ChromaticInterval.MINOR_SECOND: "b2",
            ChromaticInterval.MAJOR_SECOND: "2",
            ChromaticInterval.MINOR_THIRD: "b3",
            ChromaticInterval.MAJOR_THIRD: "3",
            ChromaticInterval.PERFECT_FOURTH: "4",
            ChromaticInterval.TRITONE: "b5",
            ChromaticInterval.PERFECT_FIFTH: "5",
            ChromaticInterval.MINOR_SIXTH: "b6",
            ChromaticInterval.MAJOR_SIXTH: "6",
            ChromaticInterval.MINOR_SEVENTH: "b7",
            ChromaticInterval.MAJOR_SEVENTH: "7",
        }
        for interval, label in expected.items():
            assert interval.abbreviation == label


class TestChromaticIntervalBetween:
    @pytest.mark.parametrize(
        ("source", "target", "expected"),
        [
            (PitchClass.A, PitchClass.A, 0),  # unison
            (PitchClass.A, PitchClass.ASHARP, 1),  # A to Bb
            (PitchClass.A, PitchClass.C, 3),  # A to C
            (PitchClass.A, PitchClass.E, 7),  # A to E
            (PitchClass.C, PitchClass.FSHARP, 6),  # C to F#
            (PitchClass.FSHARP, PitchClass.C, 6),  # F# to C
            (PitchClass.B, PitchClass.C, 1),  # B to C
            (PitchClass.C, PitchClass.B, 11),  # C to B
        ],
    )
    def test_specified_displacements(
        self, source: PitchClass, target: PitchClass, expected: int
    ) -> None:
        result = chromatic_interval_between(source, target)
        assert int(result) == expected
        assert result.semitones == expected

    def test_relative_to_fourth_and_fifth(self) -> None:
        assert chromatic_interval_between(PitchClass.E, PitchClass.A) == (
            ChromaticInterval.PERFECT_FOURTH
        )
        assert chromatic_interval_between(PitchClass.A, PitchClass.E) == (
            ChromaticInterval.PERFECT_FIFTH
        )

    def test_major_scale_relations_from_c(self) -> None:
        assert chromatic_interval_between(PitchClass.C, PitchClass.C) == (ChromaticInterval.UNISON)
        assert chromatic_interval_between(PitchClass.C, PitchClass.D) == (
            ChromaticInterval.MAJOR_SECOND
        )
        assert chromatic_interval_between(PitchClass.C, PitchClass.E) == (
            ChromaticInterval.MAJOR_THIRD
        )
        assert chromatic_interval_between(PitchClass.C, PitchClass.F) == (
            ChromaticInterval.PERFECT_FOURTH
        )
        assert chromatic_interval_between(PitchClass.C, PitchClass.G) == (
            ChromaticInterval.PERFECT_FIFTH
        )
        assert chromatic_interval_between(PitchClass.C, PitchClass.A) == (
            ChromaticInterval.MAJOR_SIXTH
        )
        assert chromatic_interval_between(PitchClass.C, PitchClass.B) == (
            ChromaticInterval.MAJOR_SEVENTH
        )

    def test_ascending_displacements_complement_to_twelve(self) -> None:
        for source in PitchClass:
            for target in PitchClass:
                up = chromatic_interval_between(source, target)
                down = chromatic_interval_between(target, source)
                assert (int(up) + int(down)) % 12 == 0

    def test_result_is_always_modulo_12(self) -> None:
        for source in PitchClass:
            for target in PitchClass:
                assert 0 <= int(chromatic_interval_between(source, target)) <= 11

    def test_six_semitones_do_not_choose_a_spelling(self) -> None:
        # Six semitones may be spelled #4 or b5; the type encodes only distance.
        assert int(ChromaticInterval.TRITONE) == 6
        assert ChromaticInterval.TRITONE.abbreviation == "b5"
        assert chromatic_interval_between(PitchClass.C, PitchClass.FSHARP) == (
            ChromaticInterval.TRITONE
        )
