"""Tests for Scale and ScaleTone."""

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.errors import InvalidScaleDegreeError
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale import Scale, ScaleTone
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula

DEG = ScaleDegree

MAJOR = ScaleFormula((DEG(1), DEG(2), DEG(3), DEG(4), DEG(5), DEG(6), DEG(7)))
NATURAL_MINOR = ScaleFormula((DEG(1), DEG(2), DEG(3, -1), DEG(4), DEG(5), DEG(6, -1), DEG(7, -1)))
MINOR_PENTATONIC = ScaleFormula((DEG(1), DEG(3, -1), DEG(4), DEG(5), DEG(7, -1)))


def pitch_classes(scale: Scale) -> tuple[str, ...]:
    return tuple(pitch.spelling() for pitch in scale.pitch_classes)


class TestScalePitchClasses:
    def test_c_major(self) -> None:
        scale = Scale(PitchClass.C, MAJOR)
        assert pitch_classes(scale) == ("C", "D", "E", "F", "G", "A", "B")

    def test_a_natural_minor(self) -> None:
        scale = Scale(PitchClass.A, NATURAL_MINOR)
        assert pitch_classes(scale) == ("A", "B", "C", "D", "E", "F", "G")

    def test_f_sharp_minor_pentatonic(self) -> None:
        scale = Scale(PitchClass.FSHARP, MINOR_PENTATONIC)
        assert pitch_classes(scale) == ("F#", "A", "B", "C#", "E")

    def test_same_formula_two_roots_is_a_transposition(self) -> None:
        c_major = Scale(PitchClass.C, MAJOR)
        g_major = Scale(PitchClass.G, MAJOR)
        assert pitch_classes(c_major) == ("C", "D", "E", "F", "G", "A", "B")
        assert pitch_classes(g_major) == ("G", "A", "B", "C", "D", "E", "F#")


class TestScaleStructure:
    def test_tones_order_matches_formula_order(self) -> None:
        scale = Scale(PitchClass.C, MAJOR)
        assert [tone.degree for tone in scale.tones] == list(MAJOR)

    def test_scale_degrees_match_formula(self) -> None:
        scale = Scale(PitchClass.A, NATURAL_MINOR)
        assert scale.scale_degrees == NATURAL_MINOR.degrees

    def test_tones_pair_degree_with_pitch_class(self) -> None:
        scale = Scale(PitchClass.C, MAJOR)
        assert scale.tones[2] == ScaleTone(DEG(3), PitchClass.E)
        assert scale.tones[4] == ScaleTone(DEG(5), PitchClass.G)

    def test_degree_identity_is_preserved(self) -> None:
        scale = Scale(PitchClass.C, MAJOR)
        assert scale.tones[3].degree == DEG(4)
        assert scale.tones[3].pitch_class == PitchClass.F

    def test_sharp_four_and_flat_five_share_pitch_class_but_stay_distinct(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(4, 1), DEG(5, -1), DEG(5)))
        scale = Scale(PitchClass.C, formula)
        sharp_four, flat_five = scale.tones[1], scale.tones[2]
        assert sharp_four.degree == DEG(4, 1)
        assert flat_five.degree == DEG(5, -1)
        assert sharp_four.pitch_class == flat_five.pitch_class == PitchClass.FSHARP
        assert sharp_four != flat_five
        assert scale.pitch_classes.count(PitchClass.FSHARP) == 2

    def test_root_and_formula_are_exposed(self) -> None:
        scale = Scale(PitchClass.FSHARP, MINOR_PENTATONIC)
        assert scale.root is PitchClass.FSHARP
        assert scale.formula is MINOR_PENTATONIC

    def test_string_shows_root_and_degrees(self) -> None:
        assert str(Scale(PitchClass.C, MAJOR)) == "C 1 2 3 4 5 6 7"


class TestScaleLookup:
    def test_tone_for_returns_degree_tone(self) -> None:
        scale = Scale(PitchClass.C, MAJOR)
        assert scale.tone_for(DEG(3)) == ScaleTone(DEG(3), PitchClass.E)

    def test_tone_for_flat_degree_in_minor(self) -> None:
        scale = Scale(PitchClass.A, NATURAL_MINOR)
        assert scale.tone_for(DEG(3, -1)) == ScaleTone(DEG(3, -1), PitchClass.C)

    def test_tone_for_missing_degree_raises(self) -> None:
        scale = Scale(PitchClass.C, MAJOR)
        with pytest.raises(InvalidScaleDegreeError):
            scale.tone_for(DEG(7, -1))  # b7 is not in the major formula
        with pytest.raises(InvalidScaleDegreeError):
            scale.tone_for(DEG(4, 1))  # #4 is not in the major formula

    def test_missing_degree_error_is_a_value_error(self) -> None:
        with pytest.raises(ValueError):
            Scale(PitchClass.C, MAJOR).tone_for(DEG(3, -1))


class TestScaleImmutability:
    def test_scale_is_frozen(self) -> None:
        scale = Scale(PitchClass.C, MAJOR)
        with pytest.raises(FrozenInstanceError):
            scale.root = PitchClass.G  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            scale.formula = MINOR_PENTATONIC  # type: ignore[misc]

    def test_scale_tone_is_frozen(self) -> None:
        tone = ScaleTone(DEG(3), PitchClass.E)
        with pytest.raises(FrozenInstanceError):
            tone.pitch_class = PitchClass.F  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            tone.degree = DEG(4)  # type: ignore[misc]
