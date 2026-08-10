"""Tests for the named scale formula catalog."""

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.errors import UnknownScaleFormulaError
from guitar_app.core.theory.scale_degree import ScaleDegree, ScaleFormula
from guitar_app.core.theory.scale_formulas import (
    AEOLIAN,
    DORIAN,
    IONIAN,
    LOCRIAN,
    LYDIAN,
    MAJOR,
    MAJOR_PENTATONIC,
    MINOR_PENTATONIC,
    MIXOLYDIAN,
    NATURAL_MINOR,
    PHRYGIAN,
    SCALE_FORMULAS,
    NamedScaleFormula,
    scale_formula_by_id,
)


def formula(*pairs: tuple[int, int]) -> ScaleFormula:
    return ScaleFormula(tuple(ScaleDegree(number, alteration) for number, alteration in pairs))


class TestCatalogContents:
    def test_required_entries_exact_formulas(self) -> None:
        assert MAJOR.formula == formula((1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0))
        assert NATURAL_MINOR.formula == formula(
            (1, 0), (2, 0), (3, -1), (4, 0), (5, 0), (6, -1), (7, -1)
        )
        assert MAJOR_PENTATONIC.formula == formula((1, 0), (2, 0), (3, 0), (5, 0), (6, 0))
        assert MINOR_PENTATONIC.formula == formula((1, 0), (3, -1), (4, 0), (5, 0), (7, -1))

    def test_seven_modes_exact_formulas(self) -> None:
        assert IONIAN.formula == formula((1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0))
        assert DORIAN.formula == formula((1, 0), (2, 0), (3, -1), (4, 0), (5, 0), (6, 0), (7, -1))
        assert PHRYGIAN.formula == formula(
            (1, 0), (2, -1), (3, -1), (4, 0), (5, 0), (6, -1), (7, -1)
        )
        assert LYDIAN.formula == formula((1, 0), (2, 0), (3, 0), (4, 1), (5, 0), (6, 0), (7, 0))
        assert MIXOLYDIAN.formula == formula(
            (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, -1)
        )
        assert AEOLIAN.formula == formula((1, 0), (2, 0), (3, -1), (4, 0), (5, 0), (6, -1), (7, -1))
        assert LOCRIAN.formula == formula(
            (1, 0), (2, -1), (3, -1), (4, 0), (5, -1), (6, -1), (7, -1)
        )

    def test_mode_labels(self) -> None:
        expected = {
            IONIAN: "1 2 3 4 5 6 7",
            DORIAN: "1 2 b3 4 5 6 b7",
            PHRYGIAN: "1 b2 b3 4 5 b6 b7",
            LYDIAN: "1 2 3 #4 5 6 7",
            MIXOLYDIAN: "1 2 3 4 5 6 b7",
            AEOLIAN: "1 2 b3 4 5 b6 b7",
            LOCRIAN: "1 b2 b3 4 b5 b6 b7",
        }
        for entry, labels in expected.items():
            assert str(entry.formula) == labels

    def test_ionian_reuses_major_formula(self) -> None:
        assert IONIAN.formula is MAJOR.formula
        assert IONIAN is not MAJOR

    def test_aeolian_reuses_natural_minor_formula(self) -> None:
        assert AEOLIAN.formula is NATURAL_MINOR.formula
        assert AEOLIAN is not NATURAL_MINOR


class TestNamesAndIds:
    @pytest.mark.parametrize(
        ("entry", "expected_id", "expected_name"),
        [
            (MAJOR, "major", "Major"),
            (NATURAL_MINOR, "natural_minor", "Natural Minor"),
            (MAJOR_PENTATONIC, "major_pentatonic", "Major Pentatonic"),
            (MINOR_PENTATONIC, "minor_pentatonic", "Minor Pentatonic"),
            (IONIAN, "ionian", "Ionian"),
            (DORIAN, "dorian", "Dorian"),
            (PHRYGIAN, "phrygian", "Phrygian"),
            (LYDIAN, "lydian", "Lydian"),
            (MIXOLYDIAN, "mixolydian", "Mixolydian"),
            (AEOLIAN, "aeolian", "Aeolian"),
            (LOCRIAN, "locrian", "Locrian"),
        ],
    )
    def test_stable_ids_and_names(
        self, entry: NamedScaleFormula, expected_id: str, expected_name: str
    ) -> None:
        assert entry.id == expected_id
        assert entry.name == expected_name


class TestLookup:
    def test_lookup_by_id(self) -> None:
        assert scale_formula_by_id("major") is MAJOR
        assert scale_formula_by_id("dorian") is DORIAN
        assert scale_formula_by_id("minor_pentatonic") is MINOR_PENTATONIC
        assert scale_formula_by_id("locrian") is LOCRIAN

    def test_unknown_id_raises(self) -> None:
        with pytest.raises(UnknownScaleFormulaError):
            scale_formula_by_id("super_locrian")

    def test_unknown_id_error_is_a_value_error(self) -> None:
        with pytest.raises(ValueError):
            scale_formula_by_id("not-a-scale")


class TestEnumerationOrder:
    def test_stable_enumeration_order(self) -> None:
        assert len(SCALE_FORMULAS) == 11
        assert [entry.id for entry in SCALE_FORMULAS] == [
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


class TestImmutability:
    def test_catalog_tuple_cannot_be_mutated(self) -> None:
        with pytest.raises(AttributeError):
            SCALE_FORMULAS.append(MAJOR)  # type: ignore[attr-defined]
        with pytest.raises(TypeError):
            SCALE_FORMULAS[0] = DORIAN  # type: ignore[index]

    def test_named_formula_is_frozen(self) -> None:
        entry = NamedScaleFormula("test", "Test", MINOR_PENTATONIC.formula)
        with pytest.raises(FrozenInstanceError):
            entry.id = "other"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            entry.formula = MAJOR.formula  # type: ignore[misc]

    def test_underlying_formula_is_immutable(self) -> None:
        with pytest.raises(TypeError):
            MAJOR.formula.degrees[0] = ScaleDegree(2)  # type: ignore[index]
