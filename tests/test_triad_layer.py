"""Tests for the triad layer."""

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.fretboard.triad_mapping import (
    TriadFretboardPosition,
    map_triad_to_fretboard,
)
from guitar_app.core.fretboard.triad_voicing import (
    DEFAULT_MAX_FRET_SPAN,
    TriadVoicing,
    find_triad_voicings,
)
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.layers.triad_layer import TriadLayer, TriadLayerResult
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.core.theory.scale_degree import ScaleDegree
from guitar_app.core.theory.triad import Triad, TriadInversion, TriadQuality

DEG = ScaleDegree

BOARD = Fretboard(STANDARD, 12)
LAYER = TriadLayer()
C_MAJOR = Triad(PitchClass.C, TriadQuality.MAJOR)
A_MINOR = Triad(PitchClass.A, TriadQuality.MINOR)


class TestTriadLayerMetadata:
    def test_stable_id_and_name(self) -> None:
        assert LAYER.id == "triad"
        assert LAYER.name == "Triads"
        assert TriadLayer.id == "triad"
        assert TriadLayer.name == "Triads"
        assert callable(LAYER.evaluate)

    def test_id_does_not_embed_triad_choice(self) -> None:
        for triad in (C_MAJOR, A_MINOR):
            result = LAYER.evaluate(BOARD, triad)
            assert result.layer_id == "triad"
            assert result.layer_name == "Triads"


class TestEvaluation:
    def test_annotations_equal_direct_mapping(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        assert result.annotations == map_triad_to_fretboard(BOARD, C_MAJOR)

    def test_voicings_equal_direct_detection(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        assert result.voicings == find_triad_voicings(BOARD, C_MAJOR)

    def test_annotations_are_triad_positions(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        assert all(isinstance(a, TriadFretboardPosition) for a in result.annotations)

    def test_voicings_are_triad_voicings(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        assert all(isinstance(v, TriadVoicing) for v in result.voicings)

    def test_c_major_known_annotations(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        by_position = {a.position: a for a in result.annotations}
        assert by_position[FretPosition(6, 8)].degree == DEG(1)  # C3
        assert by_position[FretPosition(6, 3)].degree == DEG(5)  # G2
        assert by_position[FretPosition(6, 0)].degree == DEG(3)  # E2

    def test_a_minor_known_annotations(self) -> None:
        result = LAYER.evaluate(BOARD, A_MINOR)
        by_position = {a.position: a for a in result.annotations}
        assert by_position[FretPosition(5, 0)].degree == DEG(1)  # A2
        assert by_position[FretPosition(5, 3)].degree == DEG(3, -1)  # C3

    def test_c_major_known_voicing_shape(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        open_c = [
            v
            for v in result.voicings
            if v.string_set == (3, 4, 5) and tuple(t.position.fret for t in v.tones) == (0, 2, 3)
        ]
        assert len(open_c) == 1
        assert open_c[0].inversion is TriadInversion.ROOT_POSITION

    def test_layer_does_not_prefer_a_single_voicing(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        assert len(result.voicings) == 12


class TestMaxFretSpan:
    def test_custom_span_flows_through_to_voicings(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR, max_fret_span=1)
        assert result.annotations == map_triad_to_fretboard(BOARD, C_MAJOR)
        assert result.voicings == find_triad_voicings(BOARD, C_MAJOR, max_fret_span=1)
        assert all(v.fret_span <= 1 for v in result.voicings)
        assert len(result.voicings) == 5

    def test_default_span_constant_is_used(self) -> None:
        assert DEFAULT_MAX_FRET_SPAN == 4
        default = LAYER.evaluate(BOARD, C_MAJOR)
        explicit = LAYER.evaluate(BOARD, C_MAJOR, max_fret_span=4)
        assert default.voicings == explicit.voicings


class TestAlternateTuning:
    def test_alternate_tuning_flows_through(self) -> None:
        drop_d = Tuning(
            "Drop D",
            (
                GuitarString(6, Pitch(PitchClass.D, 2)),
                *[s for s in STANDARD.strings if s.number != 6],
            ),
        )
        board = Fretboard(drop_d, 12)
        result = LAYER.evaluate(board, C_MAJOR)
        assert result.annotations == map_triad_to_fretboard(board, C_MAJOR)
        assert result.voicings == find_triad_voicings(board, C_MAJOR)
        four_five_six = [v for v in result.voicings if v.string_set == (4, 5, 6)]
        assert {tuple(t.position.fret for t in v.tones) for v in four_five_six} == {
            (2, 3, 5),
            (5, 3, 2),
        }


class TestFewerThanThreeStrings:
    def test_annotations_but_no_voicings(self) -> None:
        duo = Tuning(
            "Duo",
            (
                GuitarString(1, Pitch(PitchClass.E, 4)),
                GuitarString(2, Pitch(PitchClass.B, 3)),
            ),
        )
        board = Fretboard(duo, 12)
        result = LAYER.evaluate(board, C_MAJOR)
        assert result.annotations == map_triad_to_fretboard(board, C_MAJOR)
        assert len(result.annotations) >= 1  # open high E is a C major chord tone
        assert result.voicings == ()


class TestResultImmutability:
    def test_result_is_frozen(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        with pytest.raises(FrozenInstanceError):
            result.layer_id = "other"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            result.annotations = ()  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            result.voicings = ()  # type: ignore[misc]

    def test_annotations_are_frozen(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        annotation = result.annotations[0]
        with pytest.raises(FrozenInstanceError):
            annotation.degree = DEG(1)  # type: ignore[misc]

    def test_voicings_are_frozen(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        voicing = result.voicings[0]
        with pytest.raises(FrozenInstanceError):
            voicing.inversion = TriadInversion.ROOT_POSITION  # type: ignore[misc]

    def test_result_is_not_a_generic_layer_result(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        assert isinstance(result, TriadLayerResult)
        assert not isinstance(result, LayerResult)


class TestNoRenderingInformation:
    def test_result_fields_are_domain_only(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        fields = {field.name for field in dataclasses.fields(result)}
        assert fields == {"layer_id", "layer_name", "annotations", "voicings"}

    def test_no_rendering_attributes_anywhere(self) -> None:
        result = LAYER.evaluate(BOARD, C_MAJOR)
        for annotation in result.annotations:
            for field in ("color", "shape", "opacity", "font", "fingering"):
                assert not hasattr(annotation, field)
        for voicing in result.voicings:
            for field in ("color", "shape", "opacity", "font", "fingering"):
                assert not hasattr(voicing, field)
