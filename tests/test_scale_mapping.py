"""Tests for scale-to-fretboard mapping."""

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.scale_mapping import (
    ScaleFretboardPosition,
    map_scale_to_fretboard,
)
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.theory.chromatic_interval import ChromaticInterval
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale import Scale
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula
from guitar_app.core.theory.scale_formulas import (
    MAJOR as MAJOR_PRESET,
)
from guitar_app.core.theory.scale_formulas import (
    MINOR_PENTATONIC as MINOR_PENTATONIC_PRESET,
)
from guitar_app.core.theory.scale_formulas import (
    NATURAL_MINOR as NATURAL_MINOR_PRESET,
)

DEG = ScaleDegree

BOARD = Fretboard(STANDARD, 12)
MAJOR_SCALE = Scale(PitchClass.C, MAJOR_PRESET.formula)
NATURAL_MINOR_SCALE = Scale(PitchClass.A, NATURAL_MINOR_PRESET.formula)
MINOR_PENTATONIC_SCALE = Scale(PitchClass.A, MINOR_PENTATONIC_PRESET.formula)

TRITONE_FORMULA = ScaleFormula((DEG(1), DEG(4, 1), DEG(5, -1), DEG(5)))
TRITONE_SCALE = Scale(PitchClass.C, TRITONE_FORMULA)


def at(
    results: tuple[ScaleFretboardPosition, ...], string_number: int, fret: int
) -> list[ScaleFretboardPosition]:
    return [r for r in results if r.position == FretPosition(string_number, fret)]


class TestCMajor:
    def test_total_mapped_positions_on_standard_12_fret(self) -> None:
        assert len(map_scale_to_fretboard(BOARD, MAJOR_SCALE)) == 48

    def test_known_positions_map_to_expected_degrees(self) -> None:
        results = map_scale_to_fretboard(BOARD, MAJOR_SCALE)
        assert at(results, 6, 0)[0].degree == DEG(3)  # open E
        assert at(results, 6, 1)[0].degree == DEG(4)  # F
        assert at(results, 6, 3)[0].degree == DEG(5)  # G
        assert at(results, 5, 0)[0].degree == DEG(6)  # open A
        assert at(results, 4, 0)[0].degree == DEG(2)  # open D
        assert at(results, 3, 0)[0].degree == DEG(5)  # open G
        assert at(results, 2, 0)[0].degree == DEG(7)  # open B
        assert at(results, 1, 0)[0].degree == DEG(3)  # open high E

    def test_known_positions_sound_expected_pitches(self) -> None:
        results = map_scale_to_fretboard(BOARD, MAJOR_SCALE)
        assert at(results, 6, 0)[0].pitch == Pitch(PitchClass.E, 2)
        assert at(results, 5, 3)[0].pitch == Pitch(PitchClass.C, 3)
        assert at(results, 2, 1)[0].pitch == Pitch(PitchClass.C, 4)
        assert at(results, 3, 5)[0].pitch == Pitch(PitchClass.C, 4)

    def test_root_positions_carry_degree_one_and_unison(self) -> None:
        results = map_scale_to_fretboard(BOARD, MAJOR_SCALE)
        for string_number, fret in [(6, 8), (5, 3), (4, 10), (3, 5), (2, 1), (1, 8)]:
            entry = at(results, string_number, fret)[0]
            assert entry.degree == DEG(1)
            assert entry.chromatic_interval == ChromaticInterval.UNISON
            assert entry.pitch_class == PitchClass.C

    def test_non_scale_notes_are_absent(self) -> None:
        results = map_scale_to_fretboard(BOARD, MAJOR_SCALE)
        assert at(results, 6, 2) == []  # F#
        assert at(results, 6, 4) == []  # G#
        assert at(results, 6, 9) == []  # C#
        assert at(results, 6, 11) == []  # D#
        assert at(results, 5, 4) == []  # A#


class TestANaturalMinor:
    def test_known_positions_map_to_expected_degrees(self) -> None:
        results = map_scale_to_fretboard(BOARD, NATURAL_MINOR_SCALE)
        assert at(results, 5, 0)[0].degree == DEG(1)  # open A
        assert at(results, 5, 2)[0].degree == DEG(2)  # B
        assert at(results, 5, 3)[0].degree == DEG(3, -1)  # C
        assert at(results, 4, 0)[0].degree == DEG(4)  # D
        assert at(results, 6, 0)[0].degree == DEG(5)  # E
        assert at(results, 6, 1)[0].degree == DEG(6, -1)  # F
        assert at(results, 6, 3)[0].degree == DEG(7, -1)  # G

    def test_root_position(self) -> None:
        results = map_scale_to_fretboard(BOARD, NATURAL_MINOR_SCALE)
        entry = at(results, 5, 0)[0]
        assert entry.degree == DEG(1)
        assert entry.chromatic_interval == ChromaticInterval.UNISON

    def test_non_scale_note_absent(self) -> None:
        results = map_scale_to_fretboard(BOARD, NATURAL_MINOR_SCALE)
        assert at(results, 6, 2) == []  # F# is not in A natural minor


class TestAMinorPentatonic:
    def test_total_mapped_positions_on_standard_12_fret(self) -> None:
        assert len(map_scale_to_fretboard(BOARD, MINOR_PENTATONIC_SCALE)) == 35

    def test_known_positions_map_to_expected_degrees(self) -> None:
        results = map_scale_to_fretboard(BOARD, MINOR_PENTATONIC_SCALE)
        assert at(results, 5, 0)[0].degree == DEG(1)  # A
        assert at(results, 5, 3)[0].degree == DEG(3, -1)  # C
        assert at(results, 5, 5)[0].degree == DEG(4)  # D
        assert at(results, 6, 0)[0].degree == DEG(5)  # E
        assert at(results, 6, 3)[0].degree == DEG(7, -1)  # G

    def test_non_scale_notes_absent(self) -> None:
        results = map_scale_to_fretboard(BOARD, MINOR_PENTATONIC_SCALE)
        assert at(results, 6, 1) == []  # F is not in A minor pentatonic
        assert at(results, 6, 2) == []  # F#
        assert at(results, 5, 1) == []  # A#


class TestDuplicatePitchClassDegrees:
    def test_sharp_four_and_flat_five_emit_two_results_at_same_location(self) -> None:
        results = map_scale_to_fretboard(BOARD, TRITONE_SCALE)
        fsharp_low_e = at(results, 6, 2)
        assert len(fsharp_low_e) == 2
        assert [r.degree for r in fsharp_low_e] == [DEG(4, 1), DEG(5, -1)]
        assert fsharp_low_e[0].pitch == fsharp_low_e[1].pitch == Pitch(PitchClass.FSHARP, 2)
        assert all(r.chromatic_interval == ChromaticInterval.TRITONE for r in fsharp_low_e)

    def test_results_are_not_collapsed_by_pitch_class(self) -> None:
        results = map_scale_to_fretboard(BOARD, TRITONE_SCALE)
        distinct_positions = {r.position for r in results}
        assert len(results) == 25  # 6 root + 7 fifth + 6 tritone positions x2 degrees
        assert len(distinct_positions) == 19
        assert len([r for r in results if r.position == FretPosition(6, 2)]) == 2


class TestOrdering:
    def test_matches_fretboard_iteration_order(self) -> None:
        results = map_scale_to_fretboard(BOARD, MAJOR_SCALE)
        order = {string.number: i for i, string in enumerate(STANDARD.strings)}
        positions = [(order[r.position.string_number], r.position.fret) for r in results]
        assert positions == sorted(positions)
        assert results[0].position == FretPosition(6, 0)
        assert results[0].degree == DEG(3)

    def test_duplicate_degree_order_follows_formula_order(self) -> None:
        results = map_scale_to_fretboard(BOARD, TRITONE_SCALE)
        fsharp_positions = [r for r in results if r.position == FretPosition(6, 2)]
        assert [r.degree for r in fsharp_positions] == [DEG(4, 1), DEG(5, -1)]


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
        results = map_scale_to_fretboard(board, MAJOR_SCALE)
        open_low = at(results, 6, 0)[0]
        assert open_low.degree == DEG(2)  # D2 is the second of C major
        assert open_low.pitch == Pitch(PitchClass.D, 2)
        assert open_low.chromatic_interval == ChromaticInterval.MAJOR_SECOND
        assert at(results, 6, 2)[0].degree == DEG(3)  # E2

    def test_arbitrary_fret_count_is_respected(self) -> None:
        board = Fretboard(STANDARD, 5)
        results = map_scale_to_fretboard(board, MAJOR_SCALE)
        assert all(r.position.fret <= 5 for r in results)
        assert FretPosition(6, 8) not in {r.position for r in results}
        assert FretPosition(6, 3) in {r.position for r in results}

    def test_zero_fret_board_keeps_only_open_strings(self) -> None:
        board = Fretboard(STANDARD, 0)
        results = map_scale_to_fretboard(board, MAJOR_SCALE)
        assert {r.position.fret for r in results} == {0}
        assert len(results) == 6  # E A D G B E are all in C major


class TestScaleFretboardPosition:
    def test_preserves_all_domain_fields(self) -> None:
        result = map_scale_to_fretboard(BOARD, MAJOR_SCALE)[0]
        assert result.position == FretPosition(6, 0)
        assert result.pitch == Pitch(PitchClass.E, 2)
        assert result.degree == DEG(3)
        assert result.chromatic_interval == ChromaticInterval.MAJOR_THIRD
        assert result.pitch_class == PitchClass.E

    def test_is_frozen(self) -> None:
        result = map_scale_to_fretboard(BOARD, MAJOR_SCALE)[0]
        with pytest.raises(FrozenInstanceError):
            result.position = FretPosition(5, 0)  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            result.degree = DEG(1)  # type: ignore[misc]
