"""Tests for the UI projection of layer results into render annotations."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.instrument.tuning import STANDARD
from guitar_app.core.theory.chromatic_interval import ChromaticInterval
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.services.interval_service import evaluate_intervals
from guitar_app.services.scale_service import evaluate_scale
from guitar_app.ui import render_annotations as render_module
from guitar_app.ui.render_annotations import (
    FretboardRenderAnnotation,
    RenderRole,
    render_interval_result,
    render_scale_result,
)

BOARD = Fretboard(STANDARD, 12)


class TestRenderModel:
    def test_annotations_are_immutable(self) -> None:
        annotation = FretboardRenderAnnotation(FretPosition(6, 0), "R", RenderRole.ROOT)
        with pytest.raises(FrozenInstanceError):
            annotation.label = "5"  # type: ignore[misc]

    def test_module_is_free_of_qt(self) -> None:
        source = Path(render_module.__file__).read_text(encoding="utf-8")
        assert "from PySide6" not in source
        assert "import PySide6" not in source
        assert "QColor" not in source


class TestRenderScaleResult:
    def test_a_minor_pentatonic_labels_and_roles(self) -> None:
        result = evaluate_scale(BOARD, PitchClass.A, "minor_pentatonic")
        annotations = {
            annotation.position: annotation for annotation in render_scale_result(result)
        }
        assert annotations[FretPosition(6, 0)] == FretboardRenderAnnotation(
            FretPosition(6, 0), "5", RenderRole.SCALE_TONE
        )
        assert annotations[FretPosition(5, 0)] == FretboardRenderAnnotation(
            FretPosition(5, 0), "1", RenderRole.ROOT
        )
        assert annotations[FretPosition(5, 3)] == FretboardRenderAnnotation(
            FretPosition(5, 3), "b3", RenderRole.SCALE_TONE
        )

    def test_roles_are_restricted_to_scale_roles(self) -> None:
        result = evaluate_scale(BOARD, PitchClass.A, "minor_pentatonic")
        annotations = render_scale_result(result)
        assert all(
            annotation.role in (RenderRole.ROOT, RenderRole.SCALE_TONE)
            for annotation in annotations
        )

    def test_only_the_tonic_gets_the_root_role(self) -> None:
        result = evaluate_scale(BOARD, PitchClass.A, "minor_pentatonic")
        root_annotations = [
            annotation
            for annotation in render_scale_result(result)
            if annotation.role is RenderRole.ROOT
        ]
        assert len(root_annotations) == len(BOARD.pitch_class_locations(PitchClass.A))
        assert all(annotation.label == "1" for annotation in root_annotations)


class TestRenderIntervalResult:
    def test_every_position_is_projected_with_abbreviation_labels(self) -> None:
        result = evaluate_intervals(BOARD, PitchClass.A)
        annotations = render_interval_result(result)
        assert len(annotations) == sum(1 for _ in BOARD.positions())
        for annotation, source in zip(annotations, result.annotations, strict=True):
            assert annotation.position == source.position
            assert annotation.label == source.chromatic_interval.abbreviation

    def test_root_positions_get_root_role(self) -> None:
        result = evaluate_intervals(BOARD, PitchClass.A)
        annotations = {
            annotation.position: annotation for annotation in render_interval_result(result)
        }
        assert annotations[FretPosition(5, 0)] == FretboardRenderAnnotation(
            FretPosition(5, 0), "R", RenderRole.ROOT
        )
        assert annotations[FretPosition(6, 5)] == FretboardRenderAnnotation(
            FretPosition(6, 5), "R", RenderRole.ROOT
        )

    def test_non_root_positions_get_interval_role(self) -> None:
        result = evaluate_intervals(BOARD, PitchClass.A)
        annotations = {
            annotation.position: annotation for annotation in render_interval_result(result)
        }
        assert annotations[FretPosition(6, 0)] == FretboardRenderAnnotation(
            FretPosition(6, 0), "5", RenderRole.INTERVAL
        )
        assert annotations[FretPosition(5, 3)] == FretboardRenderAnnotation(
            FretPosition(5, 3), "b3", RenderRole.INTERVAL
        )

    def test_c_root_marks_unison_positions(self) -> None:
        result = evaluate_intervals(BOARD, PitchClass.C)
        annotations = {
            annotation.position: annotation for annotation in render_interval_result(result)
        }
        assert annotations[FretPosition(5, 3)].role is RenderRole.ROOT
        assert annotations[FretPosition(5, 3)].label == ChromaticInterval.UNISON.abbreviation


class TestCombinedProjections:
    def test_combined_annotations_preserve_both_at_a_shared_position(self) -> None:
        scale_annotations = render_scale_result(
            evaluate_scale(BOARD, PitchClass.A, "minor_pentatonic")
        )
        interval_annotations = render_interval_result(evaluate_intervals(BOARD, PitchClass.A))
        combined = scale_annotations + interval_annotations

        by_position: dict[FretPosition, list[FretboardRenderAnnotation]] = {}
        for annotation in combined:
            by_position.setdefault(annotation.position, []).append(annotation)

        shared = FretPosition(6, 0)  # open E is both the scale fifth and interval fifth
        assert shared in by_position
        roles = {annotation.role for annotation in by_position[shared]}
        assert RenderRole.SCALE_TONE in roles
        assert RenderRole.INTERVAL in roles
