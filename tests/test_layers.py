"""Tests for the fretboard layer contract and ScaleLayer."""

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError
from typing import ParamSpec

import pytest

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.scale_mapping import (
    ScaleFretboardPosition,
    map_scale_to_fretboard,
)
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.layers.base import Layer, LayerResult
from guitar_app.core.layers.scale_layer import ScaleLayer
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale import Scale
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula
from guitar_app.core.theory.scale_formulas import MAJOR, MINOR_PENTATONIC

DEG = ScaleDegree

BOARD = Fretboard(STANDARD, 12)
LAYER = ScaleLayer()
A_MINOR_PENTATONIC = Scale(PitchClass.A, MINOR_PENTATONIC.formula)

P = ParamSpec("P")


def _evaluate_layer(
    layer: Layer[P, ScaleFretboardPosition],
    *args: P.args,
    **kwargs: P.kwargs,
) -> LayerResult[ScaleFretboardPosition]:
    return layer.evaluate(*args, **kwargs)


class TestLayerProtocol:
    def test_scale_layer_satisfies_the_layer_protocol(self) -> None:
        # mypy infers P from the concrete call and verifies that ScaleLayer
        # conforms to Layer[P, ScaleFretboardPosition], preserving the
        # (Fretboard, Scale) argument types as well as the result type.
        result = _evaluate_layer(LAYER, BOARD, A_MINOR_PENTATONIC)
        assert isinstance(result, LayerResult)
        assert result.layer_id == "scale"
        assert result.layer_name == "Scale"

    def test_scale_layer_exposes_required_members(self) -> None:
        assert LAYER.id == "scale"
        assert LAYER.name == "Scale"
        assert callable(LAYER.evaluate)

    def test_evaluation_returns_the_common_result_type(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        assert isinstance(result, LayerResult)


class TestScaleLayerMetadata:
    def test_stable_id_and_name(self) -> None:
        assert LAYER.id == "scale"
        assert LAYER.name == "Scale"
        assert ScaleLayer.id == "scale"
        assert ScaleLayer.name == "Scale"

    def test_id_does_not_embed_root_or_scale_choice(self) -> None:
        for scale in (A_MINOR_PENTATONIC, Scale(PitchClass.C, MAJOR.formula)):
            result = LAYER.evaluate(BOARD, scale)
            assert result.layer_id == "scale"
            assert result.layer_name == "Scale"


class TestEvaluation:
    def test_a_minor_pentatonic_matches_scale_mapping(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        assert result.annotations == map_scale_to_fretboard(BOARD, A_MINOR_PENTATONIC)

    def test_result_carries_layer_metadata(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        assert result.layer_id == LAYER.id
        assert result.layer_name == LAYER.name

    def test_known_positions_keep_degree_identity(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        annotations = {annotation.position: annotation for annotation in result.annotations}
        assert annotations[FretPosition(5, 0)].degree == DEG(1)
        assert annotations[FretPosition(5, 0)].pitch_class == PitchClass.A
        assert annotations[FretPosition(5, 3)].degree == DEG(3, -1)
        assert annotations[FretPosition(6, 0)].degree == DEG(5)
        assert annotations[FretPosition(6, 3)].degree == DEG(7, -1)


class TestResultImmutability:
    def test_layer_result_is_frozen(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        with pytest.raises(FrozenInstanceError):
            result.layer_id = "other"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            result.annotations = ()  # type: ignore[misc]

    def test_annotation_tuple_is_immutable(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        with pytest.raises(TypeError):
            result.annotations[0] = result.annotations[1]  # type: ignore[index]

    def test_annotations_are_frozen(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        annotation = result.annotations[0]
        with pytest.raises(FrozenInstanceError):
            annotation.degree = DEG(1)  # type: ignore[misc]


class TestNoRenderingInformation:
    def test_annotation_fields_are_domain_only(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        fields = {field.name for field in dataclasses.fields(result.annotations[0])}
        assert fields == {"position", "pitch", "degree", "chromatic_interval"}

    def test_layer_result_fields_are_domain_only(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        fields = {field.name for field in dataclasses.fields(result)}
        assert fields == {"layer_id", "layer_name", "annotations"}

    def test_no_annotation_has_rendering_attributes(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR_PENTATONIC)
        for annotation in result.annotations:
            for field in ("color", "shape", "opacity", "font"):
                assert not hasattr(annotation, field)


class TestAlternateTuningsAndFretCounts:
    def test_alternate_tuning_flows_through(self) -> None:
        drop_d = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                *[s for s in STANDARD.strings if s.number != 6],
            ),
        )
        board = Fretboard(drop_d, 12)
        result = LAYER.evaluate(board, A_MINOR_PENTATONIC)
        assert result.annotations == map_scale_to_fretboard(board, A_MINOR_PENTATONIC)
        open_low = [a for a in result.annotations if a.position == FretPosition(6, 0)]
        assert open_low[0].degree == DEG(4)  # D2 is the fourth of A minor pentatonic
        assert open_low[0].pitch == Pitch(PitchClass.D, 2)

    def test_fret_count_is_respected(self) -> None:
        board = Fretboard(STANDARD, 5)
        result = LAYER.evaluate(board, A_MINOR_PENTATONIC)
        assert result.annotations == map_scale_to_fretboard(board, A_MINOR_PENTATONIC)
        assert all(annotation.position.fret <= 5 for annotation in result.annotations)


class TestDuplicatePitchClassDegrees:
    def test_duplicate_degrees_remain_preserved(self) -> None:
        tritone = ScaleFormula((DEG(1), DEG(4, 1), DEG(5, -1), DEG(5)))
        scale = Scale(PitchClass.C, tritone)
        result = LAYER.evaluate(BOARD, scale)
        assert result.annotations == map_scale_to_fretboard(BOARD, scale)
        fsharp = [a for a in result.annotations if a.position == FretPosition(6, 2)]
        assert [a.degree for a in fsharp] == [DEG(4, 1), DEG(5, -1)]
        assert len(fsharp) == 2
