"""Tests for the mode model and its parallel/relative relationships."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from guitar_app.core.theory.mode import (
    Mode,
    available_modes,
    parallel_mode,
    parent_major_root_for,
    relative_mode,
)
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale import Scale, ScaleTone
from guitar_app.core.theory.scale_degree import (
    ScaleDegree,
    natural_scale_degree_offset,
)
from guitar_app.core.theory.scale_formulas import (
    AEOLIAN,
    DORIAN,
    IONIAN,
    LOCRIAN,
    LYDIAN,
    MIXOLYDIAN,
    PHRYGIAN,
    SCALE_FORMULAS,
    NamedScaleFormula,
)

DEG = ScaleDegree

CANONICAL_ORDER = (
    Mode.IONIAN,
    Mode.DORIAN,
    Mode.PHRYGIAN,
    Mode.LYDIAN,
    Mode.MIXOLYDIAN,
    Mode.AEOLIAN,
    Mode.LOCRIAN,
)


def spellings(scale: Scale) -> tuple[str, ...]:
    return tuple(pitch.spelling() for pitch in scale.pitch_classes)


class TestCanonicalOrder:
    def test_enum_members_in_canonical_order(self) -> None:
        assert tuple(Mode) == CANONICAL_ORDER

    def test_available_modes_in_canonical_order(self) -> None:
        assert available_modes() == CANONICAL_ORDER

    def test_exactly_seven_modes(self) -> None:
        assert len(Mode) == 7
        assert len(available_modes()) == 7


class TestStableIdsNamesDegrees:
    @pytest.mark.parametrize(
        ("mode", "expected_id", "expected_name", "expected_degree"),
        [
            (Mode.IONIAN, "ionian", "Ionian", 1),
            (Mode.DORIAN, "dorian", "Dorian", 2),
            (Mode.PHRYGIAN, "phrygian", "Phrygian", 3),
            (Mode.LYDIAN, "lydian", "Lydian", 4),
            (Mode.MIXOLYDIAN, "mixolydian", "Mixolydian", 5),
            (Mode.AEOLIAN, "aeolian", "Aeolian", 6),
            (Mode.LOCRIAN, "locrian", "Locrian", 7),
        ],
    )
    def test_stable_metadata(
        self, mode: Mode, expected_id: str, expected_name: str, expected_degree: int
    ) -> None:
        assert mode.id == expected_id
        assert mode.display_name == expected_name
        assert mode.degree == expected_degree

    def test_string_is_display_name(self) -> None:
        assert str(Mode.DORIAN) == "Dorian"
        assert str(Mode.LOCRIAN) == "Locrian"


class TestAssociatedScaleFormulas:
    @pytest.mark.parametrize(
        ("mode", "catalog_entry"),
        [
            (Mode.IONIAN, IONIAN),
            (Mode.DORIAN, DORIAN),
            (Mode.PHRYGIAN, PHRYGIAN),
            (Mode.LYDIAN, LYDIAN),
            (Mode.MIXOLYDIAN, MIXOLYDIAN),
            (Mode.AEOLIAN, AEOLIAN),
            (Mode.LOCRIAN, LOCRIAN),
        ],
    )
    def test_bound_to_catalog_entry(self, mode: Mode, catalog_entry: NamedScaleFormula) -> None:
        assert mode.scale_formula is catalog_entry

    def test_formulas_are_catalog_instances_not_duplicates(self) -> None:
        assert all(mode.scale_formula in SCALE_FORMULAS for mode in Mode)
        assert Mode.IONIAN.scale_formula is IONIAN
        assert Mode.AEOLIAN.scale_formula is AEOLIAN

    def test_ionian_reuses_major_and_aeolian_reuses_natural_minor(self) -> None:
        from guitar_app.core.theory.scale_formulas import MAJOR, NATURAL_MINOR

        assert Mode.IONIAN.scale_formula.formula is MAJOR.formula
        assert Mode.AEOLIAN.scale_formula.formula is NATURAL_MINOR.formula


class TestExactDegreeFormulas:
    @pytest.mark.parametrize(
        ("mode", "expected_labels"),
        [
            (Mode.IONIAN, "1 2 3 4 5 6 7"),
            (Mode.DORIAN, "1 2 b3 4 5 6 b7"),
            (Mode.PHRYGIAN, "1 b2 b3 4 5 b6 b7"),
            (Mode.LYDIAN, "1 2 3 #4 5 6 7"),
            (Mode.MIXOLYDIAN, "1 2 3 4 5 6 b7"),
            (Mode.AEOLIAN, "1 2 b3 4 5 b6 b7"),
            (Mode.LOCRIAN, "1 b2 b3 4 b5 b6 b7"),
        ],
    )
    def test_exact_degree_formula(self, mode: Mode, expected_labels: str) -> None:
        assert str(mode.scale_formula.formula) == expected_labels


class TestAlteredDegreesFromIonian:
    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            (Mode.IONIAN, ()),
            (Mode.DORIAN, (DEG(3, -1), DEG(7, -1))),
            (Mode.PHRYGIAN, (DEG(2, -1), DEG(3, -1), DEG(6, -1), DEG(7, -1))),
            (Mode.LYDIAN, (DEG(4, 1),)),
            (Mode.MIXOLYDIAN, (DEG(7, -1),)),
            (Mode.AEOLIAN, (DEG(3, -1), DEG(6, -1), DEG(7, -1))),
            (Mode.LOCRIAN, (DEG(2, -1), DEG(3, -1), DEG(5, -1), DEG(6, -1), DEG(7, -1))),
        ],
    )
    def test_exact_altered_degrees(self, mode: Mode, expected: tuple[ScaleDegree, ...]) -> None:
        assert mode.altered_degrees_from_ionian == expected

    def test_altered_degrees_use_scale_degree_values(self) -> None:
        assert all(isinstance(d, ScaleDegree) for d in Mode.DORIAN.altered_degrees_from_ionian)

    def test_ionian_is_the_baseline(self) -> None:
        assert Mode.IONIAN.altered_degrees_from_ionian == ()


class TestParallelModes:
    @pytest.mark.parametrize(
        ("mode", "expected_spellings"),
        [
            (Mode.IONIAN, ("A", "B", "C#", "D", "E", "F#", "G#")),
            (Mode.DORIAN, ("A", "B", "C", "D", "E", "F#", "G")),
            (Mode.PHRYGIAN, ("A", "A#", "C", "D", "E", "F", "G")),
            (Mode.LYDIAN, ("A", "B", "C#", "D#", "E", "F#", "G#")),
            (Mode.MIXOLYDIAN, ("A", "B", "C#", "D", "E", "F#", "G")),
            (Mode.AEOLIAN, ("A", "B", "C", "D", "E", "F", "G")),
            (Mode.LOCRIAN, ("A", "A#", "C", "D", "D#", "F", "G")),
        ],
    )
    def test_parallel_a_modes_preserve_root_a(
        self, mode: Mode, expected_spellings: tuple[str, ...]
    ) -> None:
        scale = parallel_mode(PitchClass.A, mode)
        assert scale.root is PitchClass.A
        assert spellings(scale) == expected_spellings

    def test_parallel_preserves_root_on_chromatic_roots(self) -> None:
        for root in PitchClass:
            for mode in Mode:
                scale = parallel_mode(root, mode)
                assert scale.root is root
                assert scale.formula is mode.scale_formula.formula

    def test_parallel_modes_share_root_and_differ_in_pitches(self) -> None:
        ionian = parallel_mode(PitchClass.A, Mode.IONIAN)
        aeolian = parallel_mode(PitchClass.A, Mode.AEOLIAN)
        assert ionian.root is aeolian.root is PitchClass.A
        assert ionian.pitch_classes != aeolian.pitch_classes


class TestRelativeModes:
    @pytest.mark.parametrize(
        ("mode", "expected_root", "expected_spellings"),
        [
            (Mode.IONIAN, PitchClass.C, ("C", "D", "E", "F", "G", "A", "B")),
            (Mode.DORIAN, PitchClass.D, ("D", "E", "F", "G", "A", "B", "C")),
            (Mode.PHRYGIAN, PitchClass.E, ("E", "F", "G", "A", "B", "C", "D")),
            (Mode.LYDIAN, PitchClass.F, ("F", "G", "A", "B", "C", "D", "E")),
            (Mode.MIXOLYDIAN, PitchClass.G, ("G", "A", "B", "C", "D", "E", "F")),
            (Mode.AEOLIAN, PitchClass.A, ("A", "B", "C", "D", "E", "F", "G")),
            (Mode.LOCRIAN, PitchClass.B, ("B", "C", "D", "E", "F", "G", "A")),
        ],
    )
    def test_relative_modes_of_c_major(
        self, mode: Mode, expected_root: PitchClass, expected_spellings: tuple[str, ...]
    ) -> None:
        scale = relative_mode(PitchClass.C, mode)
        assert scale.root is expected_root
        assert spellings(scale) == expected_spellings

    def test_relative_tones_are_concrete(self) -> None:
        scale = relative_mode(PitchClass.C, Mode.DORIAN)
        assert scale.tones[0] == ScaleTone(DEG(1), PitchClass.D)
        assert scale.tones[6] == ScaleTone(DEG(7, -1), PitchClass.C)

    def test_relative_derives_root_from_degree_offset(self) -> None:
        for parent_root in PitchClass:
            for mode in Mode:
                scale = relative_mode(parent_root, mode)
                expected = PitchClass(
                    (int(parent_root) + natural_scale_degree_offset(mode.degree)) % 12
                )
                assert scale.root is expected

    def test_relative_on_chromatic_parent(self) -> None:
        scale = relative_mode(PitchClass.FSHARP, Mode.DORIAN)
        assert scale.root is PitchClass.GSHARP
        assert spellings(scale) == ("G#", "A#", "B", "C#", "D#", "F", "F#")

    def test_all_relative_modes_share_the_parent_collection(self) -> None:
        parent = set(relative_mode(PitchClass.C, Mode.IONIAN).pitch_classes)
        for mode in Mode:
            assert set(relative_mode(PitchClass.C, mode).pitch_classes) == parent


class TestParentMajorReverse:
    @pytest.mark.parametrize(
        ("modal_root", "mode", "expected_parent"),
        [
            (PitchClass.D, Mode.DORIAN, PitchClass.C),
            (PitchClass.G, Mode.MIXOLYDIAN, PitchClass.C),
            (PitchClass.A, Mode.AEOLIAN, PitchClass.C),
            (PitchClass.B, Mode.LOCRIAN, PitchClass.C),
        ],
    )
    def test_parent_major_root_for_examples(
        self, modal_root: PitchClass, mode: Mode, expected_parent: PitchClass
    ) -> None:
        assert parent_major_root_for(modal_root, mode) is expected_parent

    def test_round_trip_parent_to_relative_to_parent(self) -> None:
        for parent_root in PitchClass:
            for mode in Mode:
                modal_scale = relative_mode(parent_root, mode)
                assert parent_major_root_for(modal_scale.root, mode) is parent_root

    def test_round_trip_modal_root_to_parent_to_modal_root(self) -> None:
        for modal_root in PitchClass:
            for mode in Mode:
                parent = parent_major_root_for(modal_root, mode)
                assert relative_mode(parent, mode).root is modal_root


class TestEnumStability:
    def test_members_are_immutable(self) -> None:
        with pytest.raises(AttributeError):
            Mode.DORIAN.id = "changed"  # type: ignore[misc]
        with pytest.raises(AttributeError):
            Mode.DORIAN.display_name = "Changed"  # type: ignore[misc]

    def test_members_are_distinct_singletons(self) -> None:
        assert len({mode for mode in Mode}) == 7
        assert Mode.DORIAN is Mode.DORIAN


class TestDependencyIsolation:
    def test_mode_module_has_no_guitar_or_ui_dependencies(self) -> None:
        src = str(Path(__file__).resolve().parents[1] / "src")
        code = (
            "import sys;"
            "import guitar_app.core.theory.mode as mode;"
            "assert 'guitar_app.core.fretboard' not in sys.modules;"
            "assert 'guitar_app.core.instrument' not in sys.modules;"
            "assert 'guitar_app.ui' not in sys.modules;"
            "assert len(mode.available_modes()) == 7"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": src},
        )
        assert result.returncode == 0, result.stderr
