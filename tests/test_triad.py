"""Tests for the foundational triad domain types."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula
from guitar_app.core.theory.triad import Triad, TriadQuality, TriadTone

DEG = ScaleDegree


def _formula(*pairs: tuple[int, int]) -> ScaleFormula:
    return ScaleFormula(tuple(ScaleDegree(number, alteration) for number, alteration in pairs))


class TestTriadQuality:
    def test_exact_formulas_for_all_four_qualities(self) -> None:
        assert TriadQuality.MAJOR.formula == _formula((1, 0), (3, 0), (5, 0))
        assert TriadQuality.MINOR.formula == _formula((1, 0), (3, -1), (5, 0))
        assert TriadQuality.DIMINISHED.formula == _formula((1, 0), (3, -1), (5, -1))
        assert TriadQuality.AUGMENTED.formula == _formula((1, 0), (3, 0), (5, 1))

    def test_member_formulas_are_immutable(self) -> None:
        with pytest.raises(AttributeError):
            TriadQuality.MAJOR.formula = _formula((1, 0), (3, 0), (5, 0))  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            TriadQuality.MAJOR.formula.degrees = ()  # type: ignore[misc]


class TestTriad:
    def test_c_major(self) -> None:
        triad = Triad(PitchClass.C, TriadQuality.MAJOR)
        assert triad.tones == (
            TriadTone(DEG(1), PitchClass.C),
            TriadTone(DEG(3), PitchClass.E),
            TriadTone(DEG(5), PitchClass.G),
        )
        assert triad.pitch_classes == (PitchClass.C, PitchClass.E, PitchClass.G)

    def test_a_minor(self) -> None:
        triad = Triad(PitchClass.A, TriadQuality.MINOR)
        assert triad.tones == (
            TriadTone(DEG(1), PitchClass.A),
            TriadTone(DEG(3, -1), PitchClass.C),
            TriadTone(DEG(5), PitchClass.E),
        )
        assert triad.pitch_classes == (PitchClass.A, PitchClass.C, PitchClass.E)

    def test_b_diminished(self) -> None:
        triad = Triad(PitchClass.B, TriadQuality.DIMINISHED)
        assert triad.tones == (
            TriadTone(DEG(1), PitchClass.B),
            TriadTone(DEG(3, -1), PitchClass.D),
            TriadTone(DEG(5, -1), PitchClass.F),
        )
        assert triad.pitch_classes == (PitchClass.B, PitchClass.D, PitchClass.F)

    def test_c_augmented(self) -> None:
        triad = Triad(PitchClass.C, TriadQuality.AUGMENTED)
        assert triad.tones == (
            TriadTone(DEG(1), PitchClass.C),
            TriadTone(DEG(3), PitchClass.E),
            TriadTone(DEG(5, 1), PitchClass.GSHARP),
        )
        assert triad.pitch_classes == (PitchClass.C, PitchClass.E, PitchClass.GSHARP)

    def test_degree_identity_is_preserved(self) -> None:
        triad = Triad(PitchClass.C, TriadQuality.AUGMENTED)
        assert triad.degrees == tuple(triad.quality.formula)
        assert triad.degrees == (DEG(1), DEG(3), DEG(5, 1))
        assert triad.tones[2].degree.label == "#5"
        assert triad.tones[2].pitch_class == PitchClass.GSHARP

    def test_ordered_degrees(self) -> None:
        triad = Triad(PitchClass.B, TriadQuality.DIMINISHED)
        assert [tone.degree.label for tone in triad.tones] == ["1", "b3", "b5"]

    def test_root_transposition_uses_the_same_quality(self) -> None:
        assert Triad(PitchClass.C, TriadQuality.MAJOR).pitch_classes == (
            PitchClass.C,
            PitchClass.E,
            PitchClass.G,
        )
        d_major = Triad(PitchClass.D, TriadQuality.MAJOR)
        assert d_major.quality is TriadQuality.MAJOR
        assert d_major.pitch_classes == (PitchClass.D, PitchClass.FSHARP, PitchClass.A)

    def test_tones_are_immutable(self) -> None:
        triad = Triad(PitchClass.C, TriadQuality.MAJOR)
        with pytest.raises(FrozenInstanceError):
            triad.root = PitchClass.D  # type: ignore[misc]
        tone = triad.tones[0]
        with pytest.raises(FrozenInstanceError):
            tone.pitch_class = PitchClass.D  # type: ignore[misc]
