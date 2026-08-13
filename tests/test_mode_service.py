"""Tests for the mode application service."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from guitar_app import services as services_package
from guitar_app.core.theory.mode import (
    Mode,
    parallel_mode,
    parent_major_root_for,
    relative_mode,
)
from guitar_app.core.theory.mode import (
    available_modes as theory_available_modes,
)
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale import Scale
from guitar_app.core.theory.scale_degree import ScaleDegree
from guitar_app.services.mode_service import (
    ModeSelection,
    ModeView,
    available_mode_views,
    available_modes,
    evaluate_mode,
)

DEG = ScaleDegree

MODES = (
    Mode.IONIAN,
    Mode.DORIAN,
    Mode.PHRYGIAN,
    Mode.LYDIAN,
    Mode.MIXOLYDIAN,
    Mode.AEOLIAN,
    Mode.LOCRIAN,
)


class TestModeViews:
    def test_stable_view_order(self) -> None:
        assert available_mode_views() == (ModeView.PARALLEL, ModeView.RELATIVE)

    def test_tuple_of_enum_in_stable_order(self) -> None:
        assert tuple(ModeView) == (ModeView.PARALLEL, ModeView.RELATIVE)

    def test_human_readable_labels(self) -> None:
        assert ModeView.PARALLEL.display_name == "Parallel"
        assert ModeView.RELATIVE.display_name == "Relative"
        assert str(ModeView.PARALLEL) == "Parallel"
        assert str(ModeView.RELATIVE) == "Relative"


class TestAvailableModes:
    def test_delegates_to_theory_catalog_in_stable_order(self) -> None:
        assert available_modes() == theory_available_modes()
        assert available_modes() == MODES

    def test_exactly_seven_modes(self) -> None:
        assert len(available_modes()) == 7


class TestParallelView:
    def test_a_dorian_parallel(self) -> None:
        selection = evaluate_mode(PitchClass.A, Mode.DORIAN, ModeView.PARALLEL)
        assert selection.view is ModeView.PARALLEL
        assert selection.mode is Mode.DORIAN
        assert selection.input_root is PitchClass.A
        assert selection.modal_root is PitchClass.A
        assert selection.parent_major_root is PitchClass.G
        assert selection.scale.root is PitchClass.A
        assert selection.scale.formula is Mode.DORIAN.scale_formula.formula

    def test_a_aeolian_parallel(self) -> None:
        selection = evaluate_mode(PitchClass.A, Mode.AEOLIAN, ModeView.PARALLEL)
        assert selection.modal_root is PitchClass.A
        assert selection.parent_major_root is PitchClass.C
        assert selection.scale.root is PitchClass.A

    def test_parallel_matches_theory_operation(self) -> None:
        for root in PitchClass:
            for mode in available_modes():
                selection = evaluate_mode(root, mode, ModeView.PARALLEL)
                expected = parallel_mode(root, mode)
                assert selection.modal_root is root
                assert selection.parent_major_root is parent_major_root_for(root, mode)
                assert selection.scale == expected
                assert selection.scale.pitch_classes == expected.pitch_classes


class TestRelativeView:
    def test_c_to_d_dorian_relative(self) -> None:
        selection = evaluate_mode(PitchClass.C, Mode.DORIAN, ModeView.RELATIVE)
        assert selection.view is ModeView.RELATIVE
        assert selection.mode is Mode.DORIAN
        assert selection.input_root is PitchClass.C
        assert selection.modal_root is PitchClass.D
        assert selection.parent_major_root is PitchClass.C
        assert selection.scale.root is PitchClass.D

    def test_c_to_a_aeolian_relative(self) -> None:
        selection = evaluate_mode(PitchClass.C, Mode.AEOLIAN, ModeView.RELATIVE)
        assert selection.modal_root is PitchClass.A
        assert selection.parent_major_root is PitchClass.C
        assert selection.scale.root is PitchClass.A

    def test_g_to_a_dorian_relative(self) -> None:
        selection = evaluate_mode(PitchClass.G, Mode.DORIAN, ModeView.RELATIVE)
        assert selection.modal_root is PitchClass.A
        assert selection.parent_major_root is PitchClass.G
        assert selection.scale.root is PitchClass.A

    def test_all_seven_c_major_relative_roots(self) -> None:
        expected_roots = (
            (Mode.IONIAN, PitchClass.C),
            (Mode.DORIAN, PitchClass.D),
            (Mode.PHRYGIAN, PitchClass.E),
            (Mode.LYDIAN, PitchClass.F),
            (Mode.MIXOLYDIAN, PitchClass.G),
            (Mode.AEOLIAN, PitchClass.A),
            (Mode.LOCRIAN, PitchClass.B),
        )
        for mode, expected_root in expected_roots:
            selection = evaluate_mode(PitchClass.C, mode, ModeView.RELATIVE)
            assert selection.modal_root is expected_root
            assert selection.parent_major_root is PitchClass.C

    def test_relative_matches_theory_operation(self) -> None:
        for root in PitchClass:
            for mode in available_modes():
                selection = evaluate_mode(root, mode, ModeView.RELATIVE)
                expected = relative_mode(root, mode)
                assert selection.input_root is root
                assert selection.parent_major_root is root
                assert selection.modal_root is expected.root
                assert selection.scale == expected


class TestConsistencyAcrossRoots:
    def test_all_roots_modes_and_views(self) -> None:
        for root in PitchClass:
            for mode in available_modes():
                for view in available_mode_views():
                    selection = evaluate_mode(root, mode, view)
                    assert selection.view is view
                    assert selection.mode is mode
                    assert selection.input_root is root
                    assert selection.modal_root is selection.scale.root
                    assert selection.scale.formula is mode.scale_formula.formula
                    if view is ModeView.PARALLEL:
                        assert selection.modal_root is root
                    else:
                        assert selection.parent_major_root is root

    def test_parallel_and_relative_share_pitch_collection(self) -> None:
        parallel = evaluate_mode(PitchClass.A, Mode.DORIAN, ModeView.PARALLEL)
        relative = evaluate_mode(PitchClass.G, Mode.DORIAN, ModeView.RELATIVE)
        assert parallel.scale.root is relative.scale.root is PitchClass.A
        assert set(parallel.scale.pitch_classes) == set(relative.scale.pitch_classes)
        assert parallel.scale.formula is relative.scale.formula


class TestAlteredDegreesPassthrough:
    def test_altered_degrees_unchanged_for_every_view_and_root(self) -> None:
        for root in PitchClass:
            for mode in available_modes():
                for view in available_mode_views():
                    selection = evaluate_mode(root, mode, view)
                    assert selection.altered_degrees_from_ionian == (
                        mode.altered_degrees_from_ionian
                    )

    def test_ionian_has_no_altered_degrees(self) -> None:
        selection = evaluate_mode(PitchClass.C, Mode.IONIAN, ModeView.RELATIVE)
        assert selection.altered_degrees_from_ionian == ()

    def test_values_are_scale_degrees(self) -> None:
        selection = evaluate_mode(PitchClass.G, Mode.LOCRIAN, ModeView.RELATIVE)
        assert all(
            isinstance(degree, ScaleDegree) for degree in selection.altered_degrees_from_ionian
        )
        assert selection.altered_degrees_from_ionian == (
            DEG(2, -1),
            DEG(3, -1),
            DEG(5, -1),
            DEG(6, -1),
            DEG(7, -1),
        )


class TestResultImmutability:
    def test_mode_selection_is_frozen(self) -> None:
        selection = evaluate_mode(PitchClass.C, Mode.DORIAN, ModeView.RELATIVE)
        with pytest.raises(FrozenInstanceError):
            selection.scale = Scale(PitchClass.C, Mode.IONIAN.scale_formula.formula)  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            selection.modal_root = PitchClass.E  # type: ignore[misc]

    def test_scale_inside_result_is_immutable(self) -> None:
        selection = evaluate_mode(PitchClass.C, Mode.DORIAN, ModeView.RELATIVE)
        with pytest.raises(FrozenInstanceError):
            selection.scale.root = PitchClass.E  # type: ignore[misc]

    def test_result_is_a_mode_selection(self) -> None:
        selection = evaluate_mode(PitchClass.C, Mode.DORIAN, ModeView.RELATIVE)
        assert isinstance(selection, ModeSelection)


class TestNoUiOrFretboardDependency:
    def test_mode_service_module_has_no_fretboard_or_ui_dependency(self) -> None:
        src = str(Path(__file__).resolve().parents[1] / "src")
        code = (
            "import sys;"
            "import guitar_app.services.mode_service as service;"
            "assert 'guitar_app.core.fretboard' not in sys.modules;"
            "assert 'guitar_app.ui' not in sys.modules;"
            "assert len(service.available_modes()) == 7"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": src},
        )
        assert result.returncode == 0, result.stderr

    def test_services_package_has_no_pyside6_reference(self) -> None:
        package_dir = Path(services_package.__file__).parent
        for source in package_dir.glob("*.py"):
            assert "PySide6" not in source.read_text(encoding="utf-8")
