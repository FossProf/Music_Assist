"""Tests for ScaleFormula."""

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.errors import InvalidScaleDegreeError
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula

DEG = ScaleDegree


class TestFormulaOrderAndOffsets:
    def test_major_scale(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(2), DEG(3), DEG(4), DEG(5), DEG(6), DEG(7)))
        assert [int(offset) for offset in formula.chromatic_offsets] == [0, 2, 4, 5, 7, 9, 11]

    def test_natural_minor_scale(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(2), DEG(3, -1), DEG(4), DEG(5), DEG(6, -1), DEG(7, -1)))
        assert [int(offset) for offset in formula.chromatic_offsets] == [0, 2, 3, 5, 7, 8, 10]

    def test_minor_pentatonic_scale(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(3, -1), DEG(4), DEG(5), DEG(7, -1)))
        assert [int(offset) for offset in formula.chromatic_offsets] == [0, 3, 5, 7, 10]


class TestFormulaSequenceAccess:
    def test_len_and_indexing(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(3, -1), DEG(5)))
        assert len(formula) == 3
        assert formula[0] == DEG(1)
        assert formula[1] == DEG(3, -1)
        assert formula[-1] == DEG(5)

    def test_slicing_returns_tuple(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(3, -1), DEG(5)))
        assert formula[1:] == (DEG(3, -1), DEG(5))

    def test_iteration_preserves_order(self) -> None:
        degrees = (DEG(1), DEG(3, -1), DEG(5))
        assert list(ScaleFormula(degrees)) == list(degrees)

    def test_string_renders_labels_in_order(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(3, -1), DEG(4), DEG(5), DEG(7, -1)))
        assert str(formula) == "1 b3 4 5 b7"


class TestFormulaValidation:
    def test_empty_formula_is_rejected(self) -> None:
        with pytest.raises(InvalidScaleDegreeError):
            ScaleFormula(())

    def test_duplicate_degrees_are_rejected(self) -> None:
        with pytest.raises(InvalidScaleDegreeError):
            ScaleFormula((DEG(1), DEG(3), DEG(3)))

    def test_duplicate_after_alteration_is_rejected(self) -> None:
        # Different degrees may share a chromatic offset, but identical
        # (number, alteration) pairs are duplicates.
        with pytest.raises(InvalidScaleDegreeError):
            ScaleFormula((DEG(4, 1), DEG(5, -1), DEG(4, 1)))

    def test_sharp_four_and_flat_five_coexist(self) -> None:
        # #4 and b5 are distinct degrees even though both resolve to offset 6.
        formula = ScaleFormula((DEG(1), DEG(4, 1), DEG(5, -1), DEG(5)))
        assert len(formula) == 4
        assert [int(offset) for offset in formula.chromatic_offsets] == [0, 6, 6, 7]

    def test_error_is_a_value_error(self) -> None:
        with pytest.raises(ValueError):
            ScaleFormula(())


class TestFormulaImmutability:
    def test_formula_is_frozen(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(3)))
        with pytest.raises(FrozenInstanceError):
            formula.degrees = ()  # type: ignore[misc]

    def test_inner_tuple_is_immutable(self) -> None:
        formula = ScaleFormula((DEG(1), DEG(3)))
        with pytest.raises(TypeError):
            formula.degrees[0] = DEG(5)  # type: ignore[index]
