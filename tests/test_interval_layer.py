"""Tests for the interval layer."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import ParamSpec

import pytest

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.interval_mapping import (
    IntervalFretboardPosition,
    map_intervals_to_fretboard,
)
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.layers.base import Layer, LayerResult
from guitar_app.core.layers.interval_layer import IntervalLayer
from guitar_app.core.theory.chromatic_interval import ChromaticInterval
from guitar_app.core.theory.pitch import Pitch, PitchClass

BOARD = Fretboard(STANDARD, 12)
LAYER = IntervalLayer()

P = ParamSpec("P")


def _evaluate_interval_layer(
    layer: Layer[P, IntervalFretboardPosition],
    *args: P.args,
    **kwargs: P.kwargs,
) -> LayerResult[IntervalFretboardPosition]:
    return layer.evaluate(*args, **kwargs)


def at(
    results: tuple[IntervalFretboardPosition, ...], string_number: int, fret: int
) -> list[IntervalFretboardPosition]:
    return [r for r in results if r.position == FretPosition(string_number, fret)]


class TestIntervalLayerProtocol:
    def test_interval_layer_satisfies_the_layer_protocol(self) -> None:
        # mypy infers P from the concrete call and verifies that IntervalLayer
        # conforms to Layer[P, IntervalFretboardPosition], preserving the
        # (Fretboard, PitchClass) argument types as well as the result type.
        result = _evaluate_interval_layer(LAYER, BOARD, PitchClass.A)
        assert isinstance(result, LayerResult)
        assert result.layer_id == "interval"
        assert result.layer_name == "Intervals"

    def test_interval_layer_exposes_required_members(self) -> None:
        assert LAYER.id == "interval"
        assert LAYER.name == "Intervals"
        assert callable(LAYER.evaluate)


class TestIntervalLayerMetadata:
    def test_stable_id_and_name(self) -> None:
        assert LAYER.id == "interval"
        assert LAYER.name == "Intervals"
        assert IntervalLayer.id == "interval"
        assert IntervalLayer.name == "Intervals"

    def test_id_does_not_embed_root(self) -> None:
        for root in (PitchClass.A, PitchClass.C):
            result = LAYER.evaluate(BOARD, root)
            assert result.layer_id == "interval"
            assert result.layer_name == "Intervals"


class TestEvaluation:
    def test_matches_direct_interval_mapping(self) -> None:
        result = LAYER.evaluate(BOARD, PitchClass.A)
        assert result.annotations == map_intervals_to_fretboard(BOARD, PitchClass.A)

    def test_annotations_are_interval_positions(self) -> None:
        result = LAYER.evaluate(BOARD, PitchClass.A)
        assert all(
            isinstance(annotation, IntervalFretboardPosition) for annotation in result.annotations
        )

    def test_a_root_known_positions_retain_interval_data(self) -> None:
        result = LAYER.evaluate(BOARD, PitchClass.A)
        annotations = {annotation.position: annotation for annotation in result.annotations}
        assert annotations[FretPosition(5, 0)].chromatic_interval == ChromaticInterval.UNISON
        assert annotations[FretPosition(5, 3)].chromatic_interval == ChromaticInterval.MINOR_THIRD
        assert annotations[FretPosition(5, 3)].chromatic_interval.abbreviation == "b3"
        assert annotations[FretPosition(5, 3)].pitch == Pitch(PitchClass.C, 3)
        assert annotations[FretPosition(6, 0)].chromatic_interval == ChromaticInterval.PERFECT_FIFTH
        assert annotations[FretPosition(6, 5)].chromatic_interval == ChromaticInterval.UNISON

    def test_one_annotation_per_fretboard_position(self) -> None:
        result = LAYER.evaluate(BOARD, PitchClass.A)
        assert len(result.annotations) == 6 * 13
        assert len(result.annotations) == len(
            {annotation.position for annotation in result.annotations}
        )


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
        result = LAYER.evaluate(board, PitchClass.C)
        assert result.annotations == map_intervals_to_fretboard(board, PitchClass.C)
        open_low = at(result.annotations, 6, 0)
        assert open_low[0].chromatic_interval == ChromaticInterval.MAJOR_SECOND  # D2 -> 2
        assert open_low[0].pitch == Pitch(PitchClass.D, 2)

    def test_fret_count_is_respected(self) -> None:
        board = Fretboard(STANDARD, 5)
        result = LAYER.evaluate(board, PitchClass.A)
        assert result.annotations == map_intervals_to_fretboard(board, PitchClass.A)
        assert all(annotation.position.fret <= 5 for annotation in result.annotations)
        assert len(result.annotations) == 6 * 6


class TestResultImmutability:
    def test_layer_result_is_frozen(self) -> None:
        result = LAYER.evaluate(BOARD, PitchClass.A)
        with pytest.raises(FrozenInstanceError):
            result.layer_id = "other"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            result.annotations = ()  # type: ignore[misc]

    def test_annotations_are_frozen(self) -> None:
        result = LAYER.evaluate(BOARD, PitchClass.A)
        annotation = result.annotations[0]
        with pytest.raises(FrozenInstanceError):
            annotation.chromatic_interval = ChromaticInterval.UNISON  # type: ignore[misc]
