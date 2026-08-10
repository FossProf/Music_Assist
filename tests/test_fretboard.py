"""Tests for Fretboard pitch lookup, location search, and interval mapping."""

import pytest

from guitar_app.core.errors import InvalidPositionError
from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.theory.interval import Interval
from guitar_app.core.theory.pitch import Pitch, PitchClass

BOARD = Fretboard(STANDARD, 12)


class TestPitchLookup:
    def test_low_e_string_fret_12_is_e3(self) -> None:
        assert BOARD.pitch_at(6, 12) == Pitch(PitchClass.E, 3)

    def test_a_string_fret_3_is_c3(self) -> None:
        assert BOARD.pitch_at(5, 3) == Pitch(PitchClass.C, 3)

    def test_b_string_fret_1_is_c4(self) -> None:
        assert BOARD.pitch_at(2, 1) == Pitch(PitchClass.C, 4)

    def test_open_positions_match_the_tuning(self) -> None:
        for string in STANDARD.strings:
            assert BOARD.pitch_at(string.number, 0) == string.open_pitch

    def test_pitch_class_at(self) -> None:
        assert BOARD.pitch_class_at(6, 12) == PitchClass.E
        assert BOARD.pitch_class_at(5, 3) == PitchClass.C

    def test_pitch_rises_every_fret_on_every_string(self) -> None:
        for string in STANDARD.strings:
            for fret in range(BOARD.fret_count):
                assert BOARD.pitch_at(string.number, fret + 1).midi == (
                    BOARD.pitch_at(string.number, fret).midi + 1
                )


class TestLocationSearch:
    def test_c_pitch_class_locations_on_standard_12_fret(self) -> None:
        locations = BOARD.pitch_class_locations(PitchClass.C)
        assert len(locations) == 6
        assert set(locations) == {
            FretPosition(6, 8),
            FretPosition(5, 3),
            FretPosition(4, 10),
            FretPosition(3, 5),
            FretPosition(2, 1),
            FretPosition(1, 8),
        }

    def test_e_pitch_class_locations_include_open_and_fret_12(self) -> None:
        locations = BOARD.pitch_class_locations(PitchClass.E)
        assert FretPosition(6, 0) in set(locations)
        assert FretPosition(6, 12) in set(locations)
        assert FretPosition(1, 0) in set(locations)

    def test_e_pitch_class_locations_count(self) -> None:
        locations = BOARD.pitch_class_locations(PitchClass.E)
        assert len(locations) == 8
        assert set(locations) == {
            FretPosition(6, 0),
            FretPosition(6, 12),
            FretPosition(5, 7),
            FretPosition(4, 2),
            FretPosition(3, 9),
            FretPosition(2, 5),
            FretPosition(1, 0),
            FretPosition(1, 12),
        }

    def test_exact_e3_locations(self) -> None:
        assert set(BOARD.pitch_locations(Pitch(PitchClass.E, 3))) == {
            FretPosition(6, 12),
            FretPosition(5, 7),
            FretPosition(4, 2),
        }

    def test_octave_spelled_exact_pitch_is_distinct_from_unison(self) -> None:
        assert BOARD.pitch_locations(Pitch(PitchClass.E, 2)) == (FretPosition(6, 0),)
        assert set(BOARD.pitch_locations(Pitch(PitchClass.E, 4))) == {
            FretPosition(3, 9),
            FretPosition(2, 5),
            FretPosition(1, 0),
        }


class TestPositionsIteration:
    def test_position_count_is_strings_times_frets(self) -> None:
        assert sum(1 for _ in BOARD.positions()) == 6 * (12 + 1)

    def test_iterates_low_string_first(self) -> None:
        positions = list(BOARD.positions())
        assert positions[0].string_number == 6
        assert positions[0].fret == 0
        assert positions[0].pitch == Pitch(PitchClass.E, 2)

    def test_position_at_returns_enriched_position(self) -> None:
        position = BOARD.position_at(6, 0)
        assert position.string_number == 6
        assert position.fret == 0
        assert position.pitch == Pitch(PitchClass.E, 2)
        assert position.pitch_class == PitchClass.E
        assert position.interval_from_root is None


class TestIntervalsFromRoot:
    def test_a_string_open_is_root_of_a(self) -> None:
        position = BOARD.position_at(5, 0, root=PitchClass.A)
        assert position.interval_from_root == Interval.UNISON

    def test_low_e_is_fifth_of_a(self) -> None:
        assert BOARD.position_at(6, 0, root=PitchClass.A).interval_from_root == (
            Interval.PERFECT_FIFTH
        )
        assert BOARD.position_at(6, 12, root=PitchClass.A).interval_from_root == (
            Interval.PERFECT_FIFTH
        )

    def test_c_is_minor_third_of_a(self) -> None:
        assert BOARD.position_at(5, 3, root=PitchClass.A).interval_from_root == (
            Interval.MINOR_THIRD
        )

    def test_b_is_major_second_of_a(self) -> None:
        assert BOARD.position_at(5, 2, root=PitchClass.A).interval_from_root == (
            Interval.MAJOR_SECOND
        )

    def test_relative_to_c_matches_major_scale(self) -> None:
        c_string = Tuning(
            "Single C string",
            (GuitarString(1, Pitch(PitchClass.C, 3)),),
        )
        board = Fretboard(c_string, 12)
        positions = {p.fret: p for p in board.positions(root=PitchClass.C)}
        for fret, interval in enumerate(
            [
                Interval.UNISON,  # C
                Interval.MINOR_SECOND,  # Db
                Interval.MAJOR_SECOND,  # D
                Interval.MINOR_THIRD,  # Eb
                Interval.MAJOR_THIRD,  # E
                Interval.PERFECT_FOURTH,  # F
                Interval.TRITONE,  # Gb
                Interval.PERFECT_FIFTH,  # G
                Interval.MINOR_SIXTH,  # Ab
                Interval.MAJOR_SIXTH,  # A
                Interval.MINOR_SEVENTH,  # Bb
                Interval.MAJOR_SEVENTH,  # B
                Interval.UNISON,  # C
            ]
        ):
            assert positions[fret].interval_from_root == interval


class TestBoundsAndAlternateTunings:
    def test_out_of_range_positions_rejected(self) -> None:
        with pytest.raises(InvalidPositionError):
            BOARD.pitch_at(0, 0)
        with pytest.raises(InvalidPositionError):
            BOARD.pitch_at(7, 0)
        with pytest.raises(InvalidPositionError):
            BOARD.pitch_at(6, 13)
        with pytest.raises(InvalidPositionError):
            BOARD.pitch_at(6, -1)
        with pytest.raises(InvalidPositionError):
            BOARD.position_at(6, 13)

    def test_negative_fret_count_rejected(self) -> None:
        with pytest.raises(InvalidPositionError):
            Fretboard(STANDARD, -1)

    def test_zero_fret_fretboard(self) -> None:
        board = Fretboard(STANDARD, 0)
        assert board.pitch_at(6, 0) == Pitch(PitchClass.E, 2)
        with pytest.raises(InvalidPositionError):
            board.pitch_at(6, 1)

    def test_alternate_tuning_is_respected(self) -> None:
        drop_d = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                *[s for s in STANDARD.strings if s.number != 6],
            ),
        )
        board = Fretboard(drop_d, 12)
        assert board.pitch_at(6, 0) == Pitch(PitchClass.D, 2)
        assert board.pitch_at(6, 2) == Pitch(PitchClass.E, 2)
        assert board.pitch_at(6, 12) == Pitch(PitchClass.D, 3)
        assert board.pitch_at(5, 0) == Pitch(PitchClass.A, 2)


class TestFretboardPosition:
    def test_interval_is_none_without_root(self) -> None:
        assert list(BOARD.positions())[0].interval_from_root is None

    def test_interval_present_with_root(self) -> None:
        assert list(BOARD.positions(root=PitchClass.C))[0].interval_from_root is not None

    def test_positions_are_frozen(self) -> None:
        position = BOARD.position_at(5, 0)
        with pytest.raises(AttributeError):
            position.string_number = 1  # type: ignore[misc]
