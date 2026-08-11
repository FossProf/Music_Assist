"""Tests for adjacent-string triad voicing detection."""

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.errors import InvalidScaleDegreeError, InvalidVoicingError
from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.triad_mapping import TriadFretboardPosition
from guitar_app.core.fretboard.triad_voicing import (
    DEFAULT_MAX_FRET_SPAN,
    TriadVoicing,
    find_triad_voicings,
)
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.theory.chromatic_interval import ChromaticInterval
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale_degree import ScaleDegree
from guitar_app.core.theory.triad import Triad, TriadInversion, TriadQuality

DEG = ScaleDegree

BOARD = Fretboard(STANDARD, 12)
C_MAJOR = Triad(PitchClass.C, TriadQuality.MAJOR)
A_MINOR = Triad(PitchClass.A, TriadQuality.MINOR)
B_DIMINISHED = Triad(PitchClass.B, TriadQuality.DIMINISHED)
C_AUGMENTED = Triad(PitchClass.C, TriadQuality.AUGMENTED)

ADJACENT_SIX_STRING = {(1, 2, 3), (2, 3, 4), (3, 4, 5), (4, 5, 6)}


def shape(
    results: tuple[TriadVoicing, ...],
    string_set: tuple[int, int, int],
    frets: tuple[int, int, int],
) -> TriadVoicing:
    matches = [
        voicing
        for voicing in results
        if voicing.string_set == string_set
        and tuple(tone.position.fret for tone in voicing.tones) == frets
    ]
    assert len(matches) == 1, f"expected exactly one voicing at {string_set} {frets}"
    return matches[0]


class TestCMajor:
    def test_total_voicings_on_standard_12_fret(self) -> None:
        assert len(find_triad_voicings(BOARD, C_MAJOR)) == 12

    def test_root_position_shapes(self) -> None:
        results = find_triad_voicings(BOARD, C_MAJOR)
        assert shape(results, (1, 2, 3), (3, 5, 5)).inversion == TriadInversion.ROOT_POSITION
        assert shape(results, (2, 3, 4), (8, 9, 10)).inversion == TriadInversion.ROOT_POSITION
        assert shape(results, (3, 4, 5), (0, 2, 3)).inversion == TriadInversion.ROOT_POSITION
        assert shape(results, (4, 5, 6), (5, 7, 8)).inversion == TriadInversion.ROOT_POSITION

    def test_first_inversion_shapes(self) -> None:
        results = find_triad_voicings(BOARD, C_MAJOR)
        assert shape(results, (1, 2, 3), (8, 8, 9)).inversion == TriadInversion.FIRST_INVERSION
        assert shape(results, (2, 3, 4), (1, 0, 2)).inversion == TriadInversion.FIRST_INVERSION
        assert shape(results, (3, 4, 5), (5, 5, 7)).inversion == TriadInversion.FIRST_INVERSION
        assert shape(results, (4, 5, 6), (10, 10, 12)).inversion == TriadInversion.FIRST_INVERSION

    def test_second_inversion_shapes(self) -> None:
        results = find_triad_voicings(BOARD, C_MAJOR)
        assert shape(results, (1, 2, 3), (0, 1, 0)).inversion == TriadInversion.SECOND_INVERSION
        assert shape(results, (2, 3, 4), (5, 5, 5)).inversion == TriadInversion.SECOND_INVERSION
        assert shape(results, (3, 4, 5), (9, 10, 10)).inversion == TriadInversion.SECOND_INVERSION
        assert shape(results, (4, 5, 6), (2, 3, 3)).inversion == TriadInversion.SECOND_INVERSION

    def test_tones_are_ordered_by_string_set(self) -> None:
        voicing = shape(find_triad_voicings(BOARD, C_MAJOR), (3, 4, 5), (0, 2, 3))
        assert [tone.position.string_number for tone in voicing.tones] == [3, 4, 5]
        assert [tone.degree for tone in voicing.tones] == [DEG(5), DEG(3), DEG(1)]
        assert voicing.string_set == (3, 4, 5)

    def test_lowest_pitch_and_fret_span(self) -> None:
        results = find_triad_voicings(BOARD, C_MAJOR)
        open_c = shape(results, (3, 4, 5), (0, 2, 3))
        assert open_c.lowest_pitch == Pitch(PitchClass.C, 3)
        assert open_c.fret_span == 3
        assert shape(results, (1, 2, 3), (0, 1, 0)).fret_span == 1
        assert shape(results, (2, 3, 4), (5, 5, 5)).fret_span == 0


class TestAMinor:
    def test_total_voicings_on_standard_12_fret(self) -> None:
        assert len(find_triad_voicings(BOARD, A_MINOR)) == 12

    def test_known_shapes(self) -> None:
        results = find_triad_voicings(BOARD, A_MINOR)
        assert shape(results, (1, 2, 3), (0, 1, 2)).inversion == TriadInversion.ROOT_POSITION
        assert shape(results, (1, 2, 3), (5, 5, 5)).inversion == TriadInversion.FIRST_INVERSION
        assert shape(results, (1, 2, 3), (8, 10, 9)).inversion == TriadInversion.SECOND_INVERSION
        assert shape(results, (2, 3, 4), (1, 2, 2)).inversion == TriadInversion.SECOND_INVERSION
        assert shape(results, (2, 3, 4), (5, 5, 7)).inversion == TriadInversion.ROOT_POSITION
        assert shape(results, (2, 3, 4), (10, 9, 10)).inversion == TriadInversion.FIRST_INVERSION
        assert shape(results, (3, 4, 5), (2, 2, 3)).inversion == TriadInversion.FIRST_INVERSION
        assert shape(results, (3, 4, 5), (5, 7, 7)).inversion == TriadInversion.SECOND_INVERSION
        assert shape(results, (3, 4, 5), (9, 10, 12)).inversion == TriadInversion.ROOT_POSITION
        assert shape(results, (4, 5, 6), (2, 3, 5)).inversion == TriadInversion.ROOT_POSITION
        assert shape(results, (4, 5, 6), (7, 7, 8)).inversion == TriadInversion.FIRST_INVERSION
        assert shape(results, (4, 5, 6), (10, 12, 12)).inversion == TriadInversion.SECOND_INVERSION


class TestInvariants:
    def test_exactly_three_tones_one_per_string(self) -> None:
        for triad in (C_MAJOR, A_MINOR, B_DIMINISHED, C_AUGMENTED):
            for voicing in find_triad_voicings(BOARD, triad):
                assert len(voicing.tones) == 3
                assert tuple(tone.position.string_number for tone in voicing.tones) == (
                    voicing.string_set
                )

    def test_each_degree_exactly_once(self) -> None:
        for triad in (C_MAJOR, A_MINOR, B_DIMINISHED, C_AUGMENTED):
            expected = set(triad.degrees)
            for voicing in find_triad_voicings(BOARD, triad):
                assert {tone.degree for tone in voicing.tones} == expected

    def test_only_adjacent_string_sets_are_used(self) -> None:
        results = find_triad_voicings(BOARD, C_MAJOR)
        assert {voicing.string_set for voicing in results} == ADJACENT_SIX_STRING

    def test_diminished_and_augmented_produce_voicings(self) -> None:
        assert len(find_triad_voicings(BOARD, B_DIMINISHED)) >= 1
        assert len(find_triad_voicings(BOARD, C_AUGMENTED)) >= 1


class TestMaxFretSpan:
    def test_default_span_constant_is_four(self) -> None:
        assert DEFAULT_MAX_FRET_SPAN == 4
        assert find_triad_voicings(BOARD, C_MAJOR) == find_triad_voicings(
            BOARD, C_MAJOR, max_fret_span=4
        )

    def test_all_voicings_respect_the_span(self) -> None:
        for voicing in find_triad_voicings(BOARD, C_MAJOR):
            assert voicing.fret_span <= 4

    def test_smaller_span_changes_result_set(self) -> None:
        results = find_triad_voicings(BOARD, C_MAJOR, max_fret_span=1)
        assert len(results) == 5
        assert {tuple(tone.position.fret for tone in v.tones) for v in results} == {
            (0, 1, 0),
            (8, 8, 9),
            (5, 5, 5),
            (9, 10, 10),
            (2, 3, 3),
        }

    def test_zero_span_keeps_only_same_fret_shapes(self) -> None:
        results = find_triad_voicings(BOARD, C_MAJOR, max_fret_span=0)
        assert len(results) == 1
        assert tuple(tone.position.fret for tone in results[0].tones) == (5, 5, 5)

    def test_negative_span_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            find_triad_voicings(BOARD, C_MAJOR, max_fret_span=-1)


class TestAlternateTunings:
    def _drop_d(self) -> Fretboard:
        tuning = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                *[s for s in STANDARD.strings if s.number != 6],
            ),
        )
        return Fretboard(tuning, 12)

    def test_standard_and_drop_d_four_five_six_shapes(self) -> None:
        standard = find_triad_voicings(BOARD, C_MAJOR)
        drop_d = find_triad_voicings(self._drop_d(), C_MAJOR)
        assert {
            (tuple(tone.position.fret for tone in v.tones), v.inversion)
            for v in standard
            if v.string_set == (4, 5, 6)
        } == {
            ((2, 3, 3), TriadInversion.SECOND_INVERSION),
            ((5, 7, 8), TriadInversion.ROOT_POSITION),
            ((10, 10, 12), TriadInversion.FIRST_INVERSION),
        }
        assert {
            (tuple(tone.position.fret for tone in v.tones), v.inversion)
            for v in drop_d
            if v.string_set == (4, 5, 6)
        } == {
            ((2, 3, 5), TriadInversion.SECOND_INVERSION),
            ((5, 3, 2), TriadInversion.FIRST_INVERSION),
        }

    def test_inversion_uses_actual_pitch_not_string_number(self) -> None:
        reentrant = Tuning(
            "Re-entrant",
            (
                GuitarString(1, Pitch(PitchClass.E, 5)),
                GuitarString(2, Pitch(PitchClass.C, 4)),
                GuitarString(3, Pitch(PitchClass.E, 4)),
                GuitarString(4, Pitch(PitchClass.G, 5)),
            ),
        )
        board = Fretboard(reentrant, 12)
        results = find_triad_voicings(board, C_MAJOR)
        assert len(results) == 6
        voicing = shape(results, (2, 3, 4), (0, 0, 0))
        assert voicing.lowest_pitch == Pitch(PitchClass.C, 4)
        assert voicing.tones[2].pitch == Pitch(PitchClass.G, 5)
        assert voicing.inversion == TriadInversion.ROOT_POSITION


class TestInstrumentSizes:
    def test_three_string_instrument(self) -> None:
        treble = Tuning(
            "Treble",
            (
                GuitarString(1, Pitch(PitchClass.G, 3)),
                GuitarString(2, Pitch(PitchClass.C, 4)),
                GuitarString(3, Pitch(PitchClass.E, 4)),
            ),
        )
        results = find_triad_voicings(Fretboard(treble, 12), C_MAJOR)
        assert len(results) == 4
        assert {voicing.string_set for voicing in results} == {(1, 2, 3)}
        assert shape(results, (1, 2, 3), (0, 0, 0)).inversion == TriadInversion.SECOND_INVERSION
        assert shape(results, (1, 2, 3), (5, 4, 3)).inversion == TriadInversion.ROOT_POSITION
        assert shape(results, (1, 2, 3), (9, 7, 8)).inversion == TriadInversion.FIRST_INVERSION
        assert shape(results, (1, 2, 3), (12, 12, 12)).inversion == TriadInversion.SECOND_INVERSION

    def test_fewer_than_three_strings_returns_empty(self) -> None:
        two_strings = Tuning(
            "Duo",
            (
                GuitarString(1, Pitch(PitchClass.E, 4)),
                GuitarString(2, Pitch(PitchClass.B, 3)),
            ),
        )
        one_string = Tuning(
            "Mono",
            (GuitarString(1, Pitch(PitchClass.E, 4)),),
        )
        assert find_triad_voicings(Fretboard(two_strings, 12), C_MAJOR) == ()
        assert find_triad_voicings(Fretboard(one_string, 12), C_MAJOR) == ()


class TestOrdering:
    def test_results_are_deterministically_ordered(self) -> None:
        results = find_triad_voicings(BOARD, C_MAJOR)
        expected = [
            ((1, 2, 3), (0, 1, 0)),
            ((1, 2, 3), (3, 5, 5)),
            ((1, 2, 3), (8, 8, 9)),
            ((2, 3, 4), (1, 0, 2)),
            ((2, 3, 4), (5, 5, 5)),
            ((2, 3, 4), (8, 9, 10)),
            ((3, 4, 5), (0, 2, 3)),
            ((3, 4, 5), (5, 5, 7)),
            ((3, 4, 5), (9, 10, 10)),
            ((4, 5, 6), (2, 3, 3)),
            ((4, 5, 6), (5, 7, 8)),
            ((4, 5, 6), (10, 10, 12)),
        ]
        actual = [
            (voicing.string_set, tuple(tone.position.fret for tone in voicing.tones))
            for voicing in results
        ]
        assert actual == expected


class TestTriadVoicing:
    def _position(
        self,
        string_number: int,
        fret: int,
        degree: ScaleDegree,
    ) -> TriadFretboardPosition:
        pitch = Pitch.from_midi(40 + string_number * 5 + fret)
        return TriadFretboardPosition(
            position=FretPosition(string_number, fret),
            pitch=pitch,
            degree=degree,
            chromatic_interval=ChromaticInterval.PERFECT_FIFTH,
        )

    def test_is_frozen(self) -> None:
        voicing = find_triad_voicings(BOARD, C_MAJOR)[0]
        with pytest.raises(FrozenInstanceError):
            voicing.inversion = TriadInversion.FIRST_INVERSION  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            voicing.string_set = (2, 3, 4)  # type: ignore[misc]

    def test_rejects_duplicate_degrees(self) -> None:
        tones = (
            self._position(1, 0, DEG(1)),
            self._position(2, 0, DEG(3)),
            self._position(3, 0, DEG(3)),
        )
        with pytest.raises(InvalidVoicingError):
            TriadVoicing((1, 2, 3), tones, TriadInversion.ROOT_POSITION)

    def test_rejects_strings_mismatching_the_string_set(self) -> None:
        tones = (
            self._position(1, 0, DEG(1)),
            self._position(3, 0, DEG(3)),
            self._position(4, 0, DEG(5)),
        )
        with pytest.raises(InvalidVoicingError):
            TriadVoicing((1, 2, 3), tones, TriadInversion.ROOT_POSITION)

    def test_rejects_wrong_tone_count(self) -> None:
        tones = (
            self._position(1, 0, DEG(1)),
            self._position(2, 0, DEG(3)),
        )
        with pytest.raises(InvalidVoicingError):
            TriadVoicing((1, 2, 3), tones, TriadInversion.ROOT_POSITION)

    def test_rejects_non_ascending_string_set(self) -> None:
        tones = (
            self._position(2, 0, DEG(1)),
            self._position(1, 0, DEG(3)),
            self._position(3, 0, DEG(5)),
        )
        with pytest.raises(InvalidVoicingError):
            TriadVoicing((2, 1, 3), tones, TriadInversion.ROOT_POSITION)


class TestTriadInversion:
    def test_classification_from_lowest_degree(self) -> None:
        assert TriadInversion.from_lowest_degree(DEG(1)) is TriadInversion.ROOT_POSITION
        assert TriadInversion.from_lowest_degree(DEG(3)) is TriadInversion.FIRST_INVERSION
        assert TriadInversion.from_lowest_degree(DEG(3, -1)) is TriadInversion.FIRST_INVERSION
        assert TriadInversion.from_lowest_degree(DEG(5)) is TriadInversion.SECOND_INVERSION
        assert TriadInversion.from_lowest_degree(DEG(5, -1)) is TriadInversion.SECOND_INVERSION
        assert TriadInversion.from_lowest_degree(DEG(5, 1)) is TriadInversion.SECOND_INVERSION

    def test_rejects_non_triad_degrees(self) -> None:
        with pytest.raises(InvalidScaleDegreeError):
            TriadInversion.from_lowest_degree(DEG(2))
