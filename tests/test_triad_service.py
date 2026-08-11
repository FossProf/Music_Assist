"""Tests for the triad application service."""

from __future__ import annotations

from pathlib import Path

import pytest

from guitar_app import services as services_package
from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.triad_voicing import DEFAULT_MAX_FRET_SPAN
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.layers.triad_layer import TriadLayer, TriadLayerResult
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.triad import Triad, TriadQuality
from guitar_app.services.triad_service import (
    available_triad_qualities,
    evaluate_triad,
)

BOARD = Fretboard(STANDARD, 12)


class TestEvaluateTriad:
    def test_c_major_equals_direct_layer_evaluation(self) -> None:
        result = evaluate_triad(BOARD, PitchClass.C, TriadQuality.MAJOR)
        expected = TriadLayer().evaluate(BOARD, Triad(PitchClass.C, TriadQuality.MAJOR))
        assert result == expected
        assert result.layer_id == "triad"
        assert result.layer_name == "Triads"

    def test_a_minor(self) -> None:
        result = evaluate_triad(BOARD, PitchClass.A, TriadQuality.MINOR)
        expected = TriadLayer().evaluate(BOARD, Triad(PitchClass.A, TriadQuality.MINOR))
        assert result == expected

    def test_b_diminished(self) -> None:
        result = evaluate_triad(BOARD, PitchClass.B, TriadQuality.DIMINISHED)
        expected = TriadLayer().evaluate(BOARD, Triad(PitchClass.B, TriadQuality.DIMINISHED))
        assert result == expected
        assert {
            tone.pitch_class for tone in Triad(PitchClass.B, TriadQuality.DIMINISHED).tones
        } == {
            PitchClass.B,
            PitchClass.D,
            PitchClass.F,
        }

    def test_c_augmented(self) -> None:
        result = evaluate_triad(BOARD, PitchClass.C, TriadQuality.AUGMENTED)
        expected = TriadLayer().evaluate(BOARD, Triad(PitchClass.C, TriadQuality.AUGMENTED))
        assert result == expected
        assert {tone.pitch_class for tone in Triad(PitchClass.C, TriadQuality.AUGMENTED).tones} == {
            PitchClass.C,
            PitchClass.E,
            PitchClass.GSHARP,
        }

    def test_custom_max_fret_span_flows_through(self) -> None:
        result = evaluate_triad(
            BOARD,
            PitchClass.C,
            TriadQuality.MAJOR,
            max_fret_span=1,
        )
        expected = TriadLayer().evaluate(
            BOARD,
            Triad(PitchClass.C, TriadQuality.MAJOR),
            max_fret_span=1,
        )
        assert result == expected
        assert all(voicing.fret_span <= 1 for voicing in result.voicings)

    def test_default_max_fret_span_matches_layer_constant(self) -> None:
        default = evaluate_triad(BOARD, PitchClass.C, TriadQuality.MAJOR)
        explicit = evaluate_triad(
            BOARD,
            PitchClass.C,
            TriadQuality.MAJOR,
            max_fret_span=DEFAULT_MAX_FRET_SPAN,
        )
        assert default == explicit

    def test_alternate_tuning_flows_through(self) -> None:
        drop_d = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                *[s for s in STANDARD.strings if s.number != 6],
            ),
        )
        board = Fretboard(drop_d, 12)
        result = evaluate_triad(board, PitchClass.C, TriadQuality.MAJOR)
        assert result == TriadLayer().evaluate(board, Triad(PitchClass.C, TriadQuality.MAJOR))

    def test_returns_the_typed_result_shape(self) -> None:
        result = evaluate_triad(BOARD, PitchClass.C, TriadQuality.MAJOR)
        assert isinstance(result, TriadLayerResult)
        assert isinstance(result.voicings, tuple)
        assert result.annotations


class TestAvailableTriadQualities:
    def test_returns_natural_stable_order(self) -> None:
        assert available_triad_qualities() == (
            TriadQuality.MAJOR,
            TriadQuality.MINOR,
            TriadQuality.DIMINISHED,
            TriadQuality.AUGMENTED,
        )
        assert [quality.display_name for quality in available_triad_qualities()] == [
            "Major",
            "Minor",
            "Diminished",
            "Augmented",
        ]

    def test_reuses_the_shared_enum_members(self) -> None:
        assert all(
            quality is member
            for quality, member in zip(available_triad_qualities(), TriadQuality, strict=True)
        )

    def test_returns_an_immutable_tuple(self) -> None:
        available = available_triad_qualities()
        with pytest.raises(AttributeError):
            available.append(TriadQuality.MAJOR)  # type: ignore[attr-defined]


class TestNoUiDependency:
    def test_services_package_has_no_pyside6_reference(self) -> None:
        package_dir = Path(services_package.__file__).parent
        for source in package_dir.glob("*.py"):
            assert "PySide6" not in source.read_text(encoding="utf-8")
