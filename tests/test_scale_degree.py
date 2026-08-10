"""Tests for ScaleDegree and natural degree offsets."""

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.errors import InvalidScaleDegreeError
from guitar_app.core.theory.scale_degree import ScaleDegree, natural_scale_degree_offset


class TestNaturalScaleDegreeOffset:
    @pytest.mark.parametrize(
        ("number", "expected"),
        [
            (1, 0),
            (2, 2),
            (3, 4),
            (4, 5),
            (5, 7),
            (6, 9),
            (7, 11),
        ],
    )
    def test_natural_offsets(self, number: int, expected: int) -> None:
        assert natural_scale_degree_offset(number) == expected

    @pytest.mark.parametrize("number", [0, -1, 8, 12, 100])
    def test_invalid_numbers_raise(self, number: int) -> None:
        with pytest.raises(InvalidScaleDegreeError):
            natural_scale_degree_offset(number)


class TestScaleDegreeOffsets:
    @pytest.mark.parametrize(
        ("degree", "expected_offset"),
        [
            (ScaleDegree(1), 0),
            (ScaleDegree(2), 2),
            (ScaleDegree(3, -1), 3),
            (ScaleDegree(3), 4),
            (ScaleDegree(4), 5),
            (ScaleDegree(4, 1), 6),
            (ScaleDegree(5, -1), 6),
            (ScaleDegree(5), 7),
            (ScaleDegree(6, -1), 8),
            (ScaleDegree(6), 9),
            (ScaleDegree(7, -1), 10),
            (ScaleDegree(7), 11),
        ],
    )
    def test_chromatic_offsets(self, degree: ScaleDegree, expected_offset: int) -> None:
        assert degree.chromatic_offset.semitones == expected_offset

    def test_sharp_four_and_flat_five_are_distinct(self) -> None:
        sharp_four = ScaleDegree(4, 1)
        flat_five = ScaleDegree(5, -1)
        assert sharp_four != flat_five
        assert sharp_four.number == 4
        assert flat_five.number == 5
        assert sharp_four.chromatic_offset == flat_five.chromatic_offset

    def test_chromatic_offset_is_modulo_12(self) -> None:
        # bb7 = 11 - 2 = 9; ##5 = 7 + 2 = 9; both stay within 0..11.
        assert ScaleDegree(7, -2).chromatic_offset.semitones == 9
        assert ScaleDegree(5, 2).chromatic_offset.semitones == 9
        # b1 wraps to 11.
        assert ScaleDegree(1, -1).chromatic_offset.semitones == 11


class TestScaleDegreeLabels:
    @pytest.mark.parametrize(
        ("degree", "expected_label"),
        [
            (ScaleDegree(1), "1"),
            (ScaleDegree(2), "2"),
            (ScaleDegree(3), "3"),
            (ScaleDegree(4), "4"),
            (ScaleDegree(5), "5"),
            (ScaleDegree(6), "6"),
            (ScaleDegree(7), "7"),
            (ScaleDegree(3, -1), "b3"),
            (ScaleDegree(6, -1), "b6"),
            (ScaleDegree(4, 1), "#4"),
            (ScaleDegree(5, 1), "#5"),
            (ScaleDegree(7, -2), "bb7"),
            (ScaleDegree(5, 2), "##5"),
        ],
    )
    def test_labels(self, degree: ScaleDegree, expected_label: str) -> None:
        assert degree.label == expected_label
        assert str(degree) == expected_label

    def test_label_uses_flat_for_negative_alteration(self) -> None:
        assert ScaleDegree(2, -1).label == "b2"


class TestScaleDegreeValidation:
    @pytest.mark.parametrize("number", [0, -1, 8, 12, 100])
    def test_invalid_numbers_raise(self, number: int) -> None:
        with pytest.raises(InvalidScaleDegreeError):
            ScaleDegree(number)

    @pytest.mark.parametrize("alteration", [3, 4, -3, -5])
    def test_out_of_range_alterations_raise(self, alteration: int) -> None:
        with pytest.raises(InvalidScaleDegreeError):
            ScaleDegree(1, alteration)

    def test_valid_boundary_alterations_are_accepted(self) -> None:
        assert ScaleDegree(1, -2).alteration == -2
        assert ScaleDegree(1, 2).alteration == 2

    def test_error_is_a_value_error(self) -> None:
        with pytest.raises(ValueError):
            ScaleDegree(9)


class TestScaleDegreeImmutability:
    def test_fields_are_frozen(self) -> None:
        degree = ScaleDegree(3)
        with pytest.raises(FrozenInstanceError):
            degree.number = 5  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            degree.alteration = 1  # type: ignore[misc]
