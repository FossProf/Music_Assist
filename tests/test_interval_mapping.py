"""Tests for interval-to-fretboard mapping."""

import dataclasses
from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.interval_mapping import (
    IntervalFretboardPosition,
    map_intervals_to_fretboard,
)
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.theory.chromatic_interval import ChromaticInterval
from guitar_app.core.theory.pitch import Pitch, PitchClass

BOARD = Fretboard(STANDARD, 12)

#: Expected interval for each pitch class relative to A (the table from the spec).
EXPECTED_FROM_A: dict[PitchClass, ChromaticInterval] = {
    PitchClass.A: ChromaticInterval.UNISON,
    PitchClass.ASHARP: ChromaticInterval.MINOR_SECOND,
    PitchClass.B: ChromaticInterval.MAJOR_SECOND,
    PitchClass.C: ChromaticInterval.MINOR_THIRD,
    PitchClass.CSHARP: ChromaticInterval.MAJOR_THIRD,
    PitchClass.D: ChromaticInterval.PERFECT_FOURTH,
    PitchClass.DSHARP: ChromaticInterval.TRITONE,
    PitchClass.E: ChromaticInterval.PERFECT_FIFTH,
    PitchClass.F: ChromaticInterval.MINOR_SIXTH,
    PitchClass.FSHARP: ChromaticInterval.MAJOR_SIXTH,
    PitchClass.G: ChromaticInterval.MINOR_SEVENTH,
    PitchClass.GSHARP: ChromaticInterval.MAJOR_SEVENTH,
}


def at(
    results: tuple[IntervalFretboardPosition, ...], string_number: int, fret: int
) -> list[IntervalFretboardPosition]:
    return [r for r in results if r.position == FretPosition(string_number, fret)]


class TestEveryPositionMapped:
    def test_every_position_produces_exactly_one_result(self) -> None:
        results = map_intervals_to_fretboard(BOARD, PitchClass.A)
        positions = list(BOARD.positions())
        assert len(results) == len(positions)
        assert {r.position for r in results} == {
            FretPosition(p.string_number, p.fret) for p in positions
        }
        assert len(results) == len({r.position for r in results})

    def test_count_on_standard_12_fret_board(self) -> None:
        assert len(map_intervals_to_fretboard(BOARD, PitchClass.A)) == 6 * 13  # 78


class TestARoot:
    def test_known_positions_map_to_expected_intervals(self) -> None:
        results = map_intervals_to_fretboard(BOARD, PitchClass.A)
        assert at(results, 5, 0)[0].chromatic_interval == ChromaticInterval.UNISON  # A -> R
        assert at(results, 5, 3)[0].chromatic_interval == ChromaticInterval.MINOR_THIRD  # C -> b3
        assert at(results, 6, 0)[0].chromatic_interval == ChromaticInterval.PERFECT_FIFTH  # E -> 5
        assert at(results, 6, 5)[0].chromatic_interval == ChromaticInterval.UNISON  # A -> R

    def test_known_positions_sound_expected_pitches(self) -> None:
        results = map_intervals_to_fretboard(BOARD, PitchClass.A)
        assert at(results, 5, 3)[0].pitch == Pitch(PitchClass.C, 3)
        assert at(results, 6, 0)[0].pitch == Pitch(PitchClass.E, 2)
        assert at(results, 6, 5)[0].pitch == Pitch(PitchClass.A, 2)

    def test_interval_labels_match_the_spec_table(self) -> None:
        results = map_intervals_to_fretboard(BOARD, PitchClass.A)
        for pitch_class, expected in EXPECTED_FROM_A.items():
            matching = [r for r in results if r.pitch_class is pitch_class]
            assert matching, pitch_class
            assert all(r.chromatic_interval == expected for r in matching)
        assert at(results, 5, 3)[0].chromatic_interval.abbreviation == "b3"
        assert at(results, 6, 0)[0].chromatic_interval.abbreviation == "5"


class TestCRoot:
    def test_known_positions_map_to_expected_intervals(self) -> None:
        results = map_intervals_to_fretboard(BOARD, PitchClass.C)
        assert at(results, 6, 0)[0].chromatic_interval == ChromaticInterval.MAJOR_THIRD  # E -> 3
        assert at(results, 6, 1)[0].chromatic_interval == ChromaticInterval.PERFECT_FOURTH  # F -> 4
        assert at(results, 6, 2)[0].chromatic_interval == ChromaticInterval.TRITONE  # F# -> b5
        assert at(results, 2, 0)[0].chromatic_interval == ChromaticInterval.MAJOR_SEVENTH  # B -> 7
        assert at(results, 6, 8)[0].chromatic_interval == ChromaticInterval.UNISON  # C -> R

    def test_open_strings_map_to_expected_intervals(self) -> None:
        results = map_intervals_to_fretboard(BOARD, PitchClass.C)
        assert at(results, 5, 0)[0].chromatic_interval == ChromaticInterval.MAJOR_SIXTH  # A -> 6
        assert at(results, 4, 0)[0].chromatic_interval == ChromaticInterval.MAJOR_SECOND  # D -> 2
        assert at(results, 3, 0)[0].chromatic_interval == ChromaticInterval.PERFECT_FIFTH  # G -> 5


class TestBToCWrap:
    def test_c_wraps_to_flat_two_relative_to_b(self) -> None:
        results = map_intervals_to_fretboard(BOARD, PitchClass.B)
        c_positions = [r for r in results if r.pitch_class is PitchClass.C]
        assert c_positions
        assert all(r.chromatic_interval == ChromaticInterval.MINOR_SECOND for r in c_positions)
        assert all(r.chromatic_interval.abbreviation == "b2" for r in c_positions)
        assert at(results, 5, 2)[0].chromatic_interval == ChromaticInterval.UNISON  # B -> R
        assert at(results, 5, 3)[0].chromatic_interval == ChromaticInterval.MINOR_SECOND  # C -> b2


class TestAlternateTuningsAndFretCounts:
    def test_alternate_tuning_is_respected(self) -> None:
        drop_d = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                *[s for s in STANDARD.strings if s.number != 6],
            ),
        )
        board = Fretboard(drop_d, 12)
        results = map_intervals_to_fretboard(board, PitchClass.C)
        assert at(results, 6, 0)[0].chromatic_interval == ChromaticInterval.MAJOR_SECOND  # D2 -> 2
        assert at(results, 6, 0)[0].pitch == Pitch(PitchClass.D, 2)
        assert at(results, 6, 2)[0].chromatic_interval == ChromaticInterval.MAJOR_THIRD  # E2 -> 3

    def test_arbitrary_fret_count_is_respected(self) -> None:
        board = Fretboard(STANDARD, 5)
        results = map_intervals_to_fretboard(board, PitchClass.A)
        assert len(results) == 6 * 6
        assert all(r.position.fret <= 5 for r in results)
        assert FretPosition(6, 5) in {r.position for r in results}

    def test_zero_fret_board_keeps_only_open_strings(self) -> None:
        board = Fretboard(STANDARD, 0)
        results = map_intervals_to_fretboard(board, PitchClass.A)
        assert len(results) == 6
        assert {r.position.fret for r in results} == {0}


class TestOrdering:
    def test_matches_fretboard_iteration_order(self) -> None:
        results = map_intervals_to_fretboard(BOARD, PitchClass.A)
        expected = [(p.string_number, p.fret) for p in BOARD.positions()]
        assert [(r.position.string_number, r.position.fret) for r in results] == expected
        assert results[0].position == FretPosition(6, 0)
        assert results[-1].position == FretPosition(1, 12)


class TestIntervalFretboardPosition:
    def test_preserves_all_domain_fields(self) -> None:
        result = map_intervals_to_fretboard(BOARD, PitchClass.A)[0]
        assert result.position == FretPosition(6, 0)
        assert result.pitch == Pitch(PitchClass.E, 2)
        assert result.chromatic_interval == ChromaticInterval.PERFECT_FIFTH
        assert result.pitch_class == PitchClass.E

    def test_fields_are_domain_only(self) -> None:
        result = map_intervals_to_fretboard(BOARD, PitchClass.A)[0]
        fields = {field.name for field in dataclasses.fields(result)}
        assert fields == {"position", "pitch", "chromatic_interval"}

    def test_is_frozen(self) -> None:
        result = map_intervals_to_fretboard(BOARD, PitchClass.A)[0]
        with pytest.raises(FrozenInstanceError):
            result.position = FretPosition(5, 0)  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            result.chromatic_interval = ChromaticInterval.UNISON  # type: ignore[misc]
