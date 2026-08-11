"""Tests for the scale application service."""

from __future__ import annotations

from pathlib import Path

import pytest

from guitar_app import services as services_package
from guitar_app.core.errors import UnknownScaleFormulaError
from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.scale_mapping import map_scale_to_fretboard
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.layers.scale_layer import ScaleLayer
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale import Scale
from guitar_app.core.theory.scale_degree import ScaleDegree
from guitar_app.core.theory.scale_formulas import (
    DORIAN,
    MAJOR,
    MINOR_PENTATONIC,
    SCALE_FORMULAS,
)
from guitar_app.services.scale_service import (
    available_scale_formulas,
    evaluate_scale,
)

DEG = ScaleDegree

BOARD = Fretboard(STANDARD, 12)
MINOR_PENTATONIC_SCALE = Scale(PitchClass.A, MINOR_PENTATONIC.formula)


class TestEvaluateScale:
    def test_a_minor_pentatonic_matches_direct_layer_evaluation(self) -> None:
        result = evaluate_scale(BOARD, PitchClass.A, "minor_pentatonic")
        expected = ScaleLayer().evaluate(BOARD, MINOR_PENTATONIC_SCALE)
        assert result == expected
        assert isinstance(result, LayerResult)
        assert result.layer_id == "scale"
        assert result.layer_name == "Scale"

    def test_c_major(self) -> None:
        result = evaluate_scale(BOARD, PitchClass.C, "major")
        assert result.annotations == map_scale_to_fretboard(
            BOARD, Scale(PitchClass.C, MAJOR.formula)
        )
        annotations = {annotation.position: annotation for annotation in result.annotations}
        assert annotations[FretPosition(5, 3)].degree == DEG(1)  # C3 is the root
        assert annotations[FretPosition(5, 3)].pitch == Pitch(PitchClass.C, 3)
        assert annotations[FretPosition(6, 0)].degree == DEG(3)  # open E is the third

    def test_d_dorian_modal_scale(self) -> None:
        result = evaluate_scale(BOARD, PitchClass.D, "dorian")
        assert result.annotations == map_scale_to_fretboard(
            BOARD, Scale(PitchClass.D, DORIAN.formula)
        )
        annotations = {annotation.position: annotation for annotation in result.annotations}
        assert annotations[FretPosition(4, 0)].degree == DEG(1)  # open D is the root
        assert annotations[FretPosition(6, 0)].degree == DEG(2)  # open E is the second
        assert annotations[FretPosition(3, 0)].degree == DEG(4)  # open G is the fourth
        assert annotations[FretPosition(5, 3)].degree == DEG(7, -1)  # C3 is the minor seventh

    def test_unknown_scale_id_propagates(self) -> None:
        with pytest.raises(UnknownScaleFormulaError):
            evaluate_scale(BOARD, PitchClass.C, "super_locrian")
        with pytest.raises(ValueError):
            evaluate_scale(BOARD, PitchClass.C, "not-a-scale")

    def test_unknown_scale_id_reports_the_id(self) -> None:
        with pytest.raises(UnknownScaleFormulaError, match="super_locrian"):
            evaluate_scale(BOARD, PitchClass.C, "super_locrian")


class TestAvailableScaleFormulas:
    def test_returns_catalog_in_stable_order(self) -> None:
        available = available_scale_formulas()
        assert available == SCALE_FORMULAS
        assert [entry.id for entry in available] == [
            "major",
            "natural_minor",
            "major_pentatonic",
            "minor_pentatonic",
            "ionian",
            "dorian",
            "phrygian",
            "lydian",
            "mixolydian",
            "aeolian",
            "locrian",
        ]

    def test_reuses_the_shared_catalog_instances(self) -> None:
        available = available_scale_formulas()
        assert all(
            entry is expected for entry, expected in zip(available, SCALE_FORMULAS, strict=True)
        )

    def test_returns_an_immutable_tuple(self) -> None:
        available = available_scale_formulas()
        with pytest.raises(AttributeError):
            available.append(MINOR_PENTATONIC)  # type: ignore[attr-defined]


class TestTuningsAndFretCounts:
    def test_alternate_tuning_flows_through(self) -> None:
        drop_d = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                *[s for s in STANDARD.strings if s.number != 6],
            ),
        )
        board = Fretboard(drop_d, 12)
        result = evaluate_scale(board, PitchClass.C, "major")
        assert result.annotations == map_scale_to_fretboard(
            board, Scale(PitchClass.C, MAJOR.formula)
        )
        open_low = [a for a in result.annotations if a.position == FretPosition(6, 0)]
        assert open_low[0].degree == DEG(2)  # D2 is the second of C major
        assert open_low[0].pitch == Pitch(PitchClass.D, 2)

    def test_fret_count_is_respected(self) -> None:
        board = Fretboard(STANDARD, 5)
        result = evaluate_scale(board, PitchClass.A, "minor_pentatonic")
        assert result.annotations == map_scale_to_fretboard(board, MINOR_PENTATONIC_SCALE)
        assert all(annotation.position.fret <= 5 for annotation in result.annotations)


class TestNoUiDependency:
    def test_services_package_has_no_pyside6_reference(self) -> None:
        package_dir = Path(services_package.__file__).parent
        for source in package_dir.glob("*.py"):
            assert "PySide6" not in source.read_text(encoding="utf-8")
