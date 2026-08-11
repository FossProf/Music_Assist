"""Tests for triad-to-fretboard mapping."""

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.triad_mapping import (
    TriadFretboardPosition,
    map_triad_to_fretboard,
)
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.theory.chromatic_interval import ChromaticInterval
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale_degree import ScaleDegree
from guitar_app.core.theory.triad import Triad, TriadQuality

DEG = ScaleDegree

BOARD = Fretboard(STANDARD, 12)
C_MAJOR = Triad(PitchClass.C, TriadQuality.MAJOR)
A_MINOR = Triad(PitchClass.A, TriadQuality.MINOR)
B_DIMINISHED = Triad(PitchClass.B, TriadQuality.DIMINISHED)
C_AUGMENTED = Triad(PitchClass.C, TriadQuality.AUGMENTED)


def at(
    results: tuple[TriadFretboardPosition, ...], string_number: int, fret: int
) -> list[TriadFretboardPosition]:
    return [r for r in results if r.position == FretPosition(string_number, fret)]


class TestCMajor:
    def test_total_mapped_positions_on_standard_12_fret(self) -> None:
        assert len(map_triad_to_fretboard(BOARD, C_MAJOR)) == 21

    def test_known_positions_map_to_expected_degrees(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_MAJOR)
        assert at(results, 6, 0)[0].degree == DEG(3)  # open E
        assert at(results, 6, 3)[0].degree == DEG(5)  # G
        assert at(results, 6, 8)[0].degree == DEG(1)  # C
        assert at(results, 5, 7)[0].degree == DEG(3)  # E
        assert at(results, 5, 10)[0].degree == DEG(5)  # G
        assert at(results, 4, 2)[0].degree == DEG(3)  # E
        assert at(results, 4, 5)[0].degree == DEG(5)  # G
        assert at(results, 3, 9)[0].degree == DEG(3)  # E
        assert at(results, 2, 5)[0].degree == DEG(3)  # E
        assert at(results, 2, 8)[0].degree == DEG(5)  # G
        assert at(results, 1, 3)[0].degree == DEG(5)  # G
        assert at(results, 1, 12)[0].degree == DEG(3)  # high E

    def test_known_positions_sound_expected_pitches(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_MAJOR)
        assert at(results, 6, 8)[0].pitch == Pitch(PitchClass.C, 3)
        assert at(results, 5, 3)[0].pitch == Pitch(PitchClass.C, 3)
        assert at(results, 2, 1)[0].pitch == Pitch(PitchClass.C, 4)
        assert at(results, 3, 5)[0].pitch == Pitch(PitchClass.C, 4)
        assert at(results, 6, 3)[0].pitch == Pitch(PitchClass.G, 2)

    def test_known_positions_carry_expected_intervals(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_MAJOR)
        assert at(results, 6, 0)[0].chromatic_interval == ChromaticInterval.MAJOR_THIRD
        assert at(results, 6, 3)[0].chromatic_interval == ChromaticInterval.PERFECT_FIFTH
        assert at(results, 6, 8)[0].chromatic_interval == ChromaticInterval.UNISON

    def test_root_positions_carry_degree_one_and_unison(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_MAJOR)
        for string_number, fret in [(6, 8), (5, 3), (4, 10), (3, 5), (2, 1), (1, 8)]:
            entry = at(results, string_number, fret)[0]
            assert entry.degree == DEG(1)
            assert entry.chromatic_interval == ChromaticInterval.UNISON
            assert entry.pitch_class == PitchClass.C

    def test_non_triad_tones_are_absent(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_MAJOR)
        assert at(results, 6, 2) == []  # F#
        assert at(results, 6, 4) == []  # G#
        assert at(results, 6, 5) == []  # A
        assert at(results, 6, 9) == []  # C#
        assert at(results, 6, 11) == []  # D#
        assert at(results, 5, 0) == []  # A
        assert at(results, 5, 4) == []  # A#
        assert at(results, 4, 0) == []  # D
        assert at(results, 4, 1) == []  # D#
        assert at(results, 2, 0) == []  # B


class TestAMinor:
    def test_known_positions_map_to_expected_degrees(self) -> None:
        results = map_triad_to_fretboard(BOARD, A_MINOR)
        assert at(results, 5, 0)[0].degree == DEG(1)  # open A
        assert at(results, 5, 3)[0].degree == DEG(3, -1)  # C
        assert at(results, 6, 0)[0].degree == DEG(5)  # E
        assert at(results, 6, 5)[0].degree == DEG(1)  # A
        assert at(results, 6, 8)[0].degree == DEG(3, -1)  # C
        assert at(results, 5, 7)[0].degree == DEG(5)  # E
        assert at(results, 3, 2)[0].degree == DEG(1)  # A
        assert at(results, 2, 1)[0].degree == DEG(3, -1)  # C
        assert at(results, 1, 5)[0].degree == DEG(1)  # A

    def test_root_positions_carry_degree_one_and_unison(self) -> None:
        results = map_triad_to_fretboard(BOARD, A_MINOR)
        for string_number, fret in [(6, 5), (5, 0), (4, 7), (3, 2), (2, 10), (1, 5)]:
            entry = at(results, string_number, fret)[0]
            assert entry.degree == DEG(1)
            assert entry.chromatic_interval == ChromaticInterval.UNISON

    def test_non_triad_tones_are_absent(self) -> None:
        results = map_triad_to_fretboard(BOARD, A_MINOR)
        assert at(results, 6, 1) == []  # F
        assert at(results, 6, 2) == []  # F#
        assert at(results, 6, 4) == []  # G#
        assert at(results, 5, 1) == []  # A#
        assert at(results, 5, 2) == []  # B
        assert at(results, 4, 0) == []  # D
        assert at(results, 4, 1) == []  # D#


class TestBDiminished:
    def test_known_positions_map_to_expected_degrees(self) -> None:
        results = map_triad_to_fretboard(BOARD, B_DIMINISHED)
        assert at(results, 6, 7)[0].degree == DEG(1)  # B
        assert at(results, 6, 10)[0].degree == DEG(3, -1)  # D
        assert at(results, 6, 1)[0].degree == DEG(5, -1)  # F
        assert at(results, 5, 2)[0].degree == DEG(1)  # B
        assert at(results, 5, 5)[0].degree == DEG(3, -1)  # D
        assert at(results, 5, 8)[0].degree == DEG(5, -1)  # F
        assert at(results, 4, 0)[0].degree == DEG(3, -1)  # D
        assert at(results, 3, 4)[0].degree == DEG(1)  # B
        assert at(results, 2, 3)[0].degree == DEG(3, -1)  # D
        assert at(results, 2, 6)[0].degree == DEG(5, -1)  # F
        assert at(results, 1, 1)[0].degree == DEG(5, -1)  # F
        assert at(results, 1, 7)[0].degree == DEG(1)  # B
        assert at(results, 1, 10)[0].degree == DEG(3, -1)  # D

    def test_known_positions_carry_expected_intervals(self) -> None:
        results = map_triad_to_fretboard(BOARD, B_DIMINISHED)
        assert at(results, 6, 7)[0].chromatic_interval == ChromaticInterval.UNISON
        assert at(results, 6, 10)[0].chromatic_interval == ChromaticInterval.MINOR_THIRD
        assert at(results, 6, 1)[0].chromatic_interval == ChromaticInterval.TRITONE

    def test_degree_identity_is_preserved(self) -> None:
        results = map_triad_to_fretboard(BOARD, B_DIMINISHED)
        flat_five = at(results, 6, 1)[0]
        assert flat_five.degree == DEG(5, -1)
        assert flat_five.degree.label == "b5"
        assert flat_five.degree.chromatic_offset == ChromaticInterval.TRITONE
        assert flat_five.pitch_class == PitchClass.F

    def test_non_triad_tones_are_absent(self) -> None:
        results = map_triad_to_fretboard(BOARD, B_DIMINISHED)
        assert at(results, 6, 0) == []  # E
        assert at(results, 6, 2) == []  # F#
        assert at(results, 6, 4) == []  # G#
        assert at(results, 6, 11) == []  # D#


class TestCAugmented:
    def test_known_positions_map_to_expected_degrees(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_AUGMENTED)
        assert at(results, 6, 0)[0].degree == DEG(3)  # E
        assert at(results, 6, 4)[0].degree == DEG(5, 1)  # G#
        assert at(results, 6, 8)[0].degree == DEG(1)  # C
        assert at(results, 6, 12)[0].degree == DEG(3)  # E
        assert at(results, 5, 3)[0].degree == DEG(1)  # C
        assert at(results, 5, 7)[0].degree == DEG(3)  # E
        assert at(results, 5, 11)[0].degree == DEG(5, 1)  # G#
        assert at(results, 4, 6)[0].degree == DEG(5, 1)  # G#
        assert at(results, 4, 10)[0].degree == DEG(1)  # C
        assert at(results, 3, 1)[0].degree == DEG(5, 1)  # G#
        assert at(results, 3, 5)[0].degree == DEG(1)  # C
        assert at(results, 3, 9)[0].degree == DEG(3)  # E
        assert at(results, 2, 5)[0].degree == DEG(3)  # E
        assert at(results, 2, 9)[0].degree == DEG(5, 1)  # G#
        assert at(results, 1, 4)[0].degree == DEG(5, 1)  # G#
        assert at(results, 1, 12)[0].degree == DEG(3)  # E

    def test_known_positions_carry_expected_intervals(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_AUGMENTED)
        assert at(results, 6, 0)[0].chromatic_interval == ChromaticInterval.MAJOR_THIRD
        assert at(results, 6, 4)[0].chromatic_interval == ChromaticInterval.MINOR_SIXTH
        assert at(results, 6, 8)[0].chromatic_interval == ChromaticInterval.UNISON

    def test_sharp_five_degree_identity_is_preserved(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_AUGMENTED)
        sharp_five = at(results, 6, 4)[0]
        assert sharp_five.degree == DEG(5, 1)
        assert sharp_five.degree.label == "#5"
        assert sharp_five.degree.chromatic_offset == ChromaticInterval.MINOR_SIXTH
        assert sharp_five.pitch_class == PitchClass.GSHARP

    def test_non_triad_tones_are_absent(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_AUGMENTED)
        assert at(results, 6, 2) == []  # F#
        assert at(results, 6, 3) == []  # G
        assert at(results, 6, 5) == []  # A
        assert at(results, 5, 4) == []  # A#
        assert at(results, 4, 0) == []  # D
        assert at(results, 3, 0) == []  # G
        assert at(results, 2, 0) == []  # B


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
        results = map_triad_to_fretboard(board, C_MAJOR)
        assert at(results, 6, 0) == []  # D2 is not a C major chord tone
        assert at(results, 6, 2)[0].degree == DEG(3)  # E2
        assert at(results, 6, 5)[0].degree == DEG(5)  # G2
        assert at(results, 6, 10)[0].degree == DEG(1)  # C3
        assert at(results, 6, 10)[0].pitch == Pitch(PitchClass.C, 3)

    def test_arbitrary_fret_count_is_respected(self) -> None:
        board = Fretboard(STANDARD, 5)
        results = map_triad_to_fretboard(board, C_MAJOR)
        assert all(r.position.fret <= 5 for r in results)
        assert FretPosition(6, 8) not in {r.position for r in results}
        assert FretPosition(6, 3) in {r.position for r in results}
        assert FretPosition(5, 3) in {r.position for r in results}

    def test_zero_fret_board_keeps_only_open_strings(self) -> None:
        board = Fretboard(STANDARD, 0)
        results = map_triad_to_fretboard(board, C_MAJOR)
        assert {r.position.fret for r in results} == {0}
        assert len(results) == 3  # open E, G, and high E


class TestOrdering:
    def test_matches_fretboard_iteration_order(self) -> None:
        results = map_triad_to_fretboard(BOARD, C_MAJOR)
        order = {string.number: i for i, string in enumerate(STANDARD.strings)}
        positions = [(order[r.position.string_number], r.position.fret) for r in results]
        assert positions == sorted(positions)
        assert results[0].position == FretPosition(6, 0)
        assert results[0].degree == DEG(3)

    def test_single_result_per_position_for_all_qualities(self) -> None:
        for triad in (C_MAJOR, A_MINOR, B_DIMINISHED, C_AUGMENTED):
            results = map_triad_to_fretboard(BOARD, triad)
            for position in {r.position for r in results}:
                assert len(at(results, position.string_number, position.fret)) == 1


class TestTriadFretboardPosition:
    def test_preserves_all_domain_fields(self) -> None:
        result = map_triad_to_fretboard(BOARD, C_MAJOR)[0]
        assert result.position == FretPosition(6, 0)
        assert result.pitch == Pitch(PitchClass.E, 2)
        assert result.degree == DEG(3)
        assert result.chromatic_interval == ChromaticInterval.MAJOR_THIRD
        assert result.pitch_class == PitchClass.E

    def test_is_frozen(self) -> None:
        result = map_triad_to_fretboard(BOARD, C_MAJOR)[0]
        with pytest.raises(FrozenInstanceError):
            result.position = FretPosition(5, 0)  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            result.degree = DEG(1)  # type: ignore[misc]
