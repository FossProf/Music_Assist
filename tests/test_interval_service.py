"""Tests for the interval application service."""

from __future__ import annotations

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.interval_mapping import IntervalFretboardPosition
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.layers.interval_layer import IntervalLayer
from guitar_app.core.theory.chromatic_interval import ChromaticInterval
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.services.interval_service import evaluate_intervals

BOARD = Fretboard(STANDARD, 12)


class TestEvaluateIntervals:
    def test_a_root_matches_direct_layer_evaluation(self) -> None:
        result = evaluate_intervals(BOARD, PitchClass.A)
        expected = IntervalLayer().evaluate(BOARD, PitchClass.A)
        assert result == expected
        assert isinstance(result, LayerResult)
        assert result.layer_id == "interval"
        assert result.layer_name == "Intervals"

    def test_c_root(self) -> None:
        result = evaluate_intervals(BOARD, PitchClass.C)
        assert result.annotations == IntervalLayer().evaluate(BOARD, PitchClass.C).annotations
        annotations = {annotation.position: annotation for annotation in result.annotations}
        assert annotations[FretPosition(5, 3)].chromatic_interval == ChromaticInterval.UNISON
        assert annotations[FretPosition(6, 0)].chromatic_interval == ChromaticInterval.MAJOR_THIRD
        assert (
            annotations[FretPosition(6, 1)].chromatic_interval == ChromaticInterval.PERFECT_FOURTH
        )
        assert annotations[FretPosition(2, 0)].chromatic_interval == ChromaticInterval.MAJOR_SEVENTH

    def test_alternate_tuning_flows_through(self) -> None:
        drop_d = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                *[s for s in STANDARD.strings if s.number != 6],
            ),
        )
        board = Fretboard(drop_d, 12)
        result = evaluate_intervals(board, PitchClass.C)
        assert result.annotations == IntervalLayer().evaluate(board, PitchClass.C).annotations
        open_low = [a for a in result.annotations if a.position == FretPosition(6, 0)]
        assert open_low[0].chromatic_interval == ChromaticInterval.MAJOR_SECOND
        assert open_low[0].pitch == Pitch(PitchClass.D, 2)

    def test_fret_count_is_respected(self) -> None:
        board = Fretboard(STANDARD, 5)
        result = evaluate_intervals(board, PitchClass.A)
        assert result.annotations == IntervalLayer().evaluate(board, PitchClass.A).annotations
        assert all(annotation.position.fret <= 5 for annotation in result.annotations)

    def test_one_annotation_per_fretboard_position(self) -> None:
        result = evaluate_intervals(BOARD, PitchClass.A)
        assert len(result.annotations) == 6 * 13
        assert len(result.annotations) == len(
            {annotation.position for annotation in result.annotations}
        )

    def test_returns_the_typed_result_shape(self) -> None:
        result = evaluate_intervals(BOARD, PitchClass.A)
        assert isinstance(result, LayerResult)
        assert result.layer_id == "interval"
        assert result.layer_name == "Intervals"
        assert all(
            isinstance(annotation, IntervalFretboardPosition) for annotation in result.annotations
        )
