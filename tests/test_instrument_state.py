"""Tests for the application-level instrument/workspace state."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from guitar_app.core.errors import InvalidPositionError, InvalidTuningError, UnknownTuningError
from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import Tuning
from guitar_app.core.instrument.tuning_presets import (
    DADGAD_TUNING,
    DROP_D_TUNING,
    STANDARD_TUNING,
)
from guitar_app.core.theory.pitch import Pitch, PitchClass
from guitar_app.services import instrument_state as instrument_state_module
from guitar_app.services.instrument_state import (
    DEFAULT_FRET_COUNT,
    DEFAULT_INSTRUMENT_STATE,
    InstrumentState,
    instrument_from_string_pitches,
    instrument_from_tuning_id,
)


def _custom_tuning(name: str = "Custom", count: int = 6) -> Tuning:
    pitches = (Pitch(PitchClass.E, 2),) * count
    strings = tuple(
        GuitarString(number, pitch)
        for number, pitch in zip(range(count, 0, -1), pitches, strict=True)
    )
    return Tuning(name, strings)


class TestDefaultState:
    def test_default_uses_standard_tuning(self) -> None:
        assert DEFAULT_INSTRUMENT_STATE.tuning is STANDARD_TUNING.tuning

    def test_default_has_22_frets(self) -> None:
        assert DEFAULT_INSTRUMENT_STATE.fret_count == 22
        assert DEFAULT_INSTRUMENT_STATE.fret_count == DEFAULT_FRET_COUNT

    def test_default_preserves_preset_identity(self) -> None:
        assert DEFAULT_INSTRUMENT_STATE.tuning_id == "standard"
        assert DEFAULT_INSTRUMENT_STATE.display_name == "Standard"


class TestPresetConstruction:
    def test_drop_d_state(self) -> None:
        state = instrument_from_tuning_id("drop_d")
        assert state.tuning is DROP_D_TUNING.tuning
        assert state.tuning_id == "drop_d"
        assert state.display_name == "Drop D"

    def test_dadgad_state(self) -> None:
        state = instrument_from_tuning_id("dadgad")
        assert state.tuning is DADGAD_TUNING.tuning
        assert state.tuning_id == "dadgad"
        assert state.display_name == "DADGAD"

    def test_preset_id_and_display_name_preserved(self) -> None:
        state = instrument_from_tuning_id("eb_standard", fret_count=24)
        assert state.tuning_id == "eb_standard"
        assert state.display_name == "Eb Standard"
        assert state.fret_count == 24

    def test_custom_fret_count(self) -> None:
        state = instrument_from_tuning_id("standard", fret_count=24)
        assert state.fret_count == 24

    def test_default_fret_count_used_when_omitted(self) -> None:
        assert instrument_from_tuning_id("standard").fret_count == DEFAULT_FRET_COUNT

    def test_unknown_tuning_id_propagates_unknown_tuning_error(self) -> None:
        with pytest.raises(UnknownTuningError):
            instrument_from_tuning_id("no_such_tuning")


class TestDerivedFretboard:
    def test_derived_fretboard_matches_state(self) -> None:
        state = instrument_from_tuning_id("drop_d", fret_count=24)
        assert state.fretboard == Fretboard(state.tuning, 24)

    def test_derived_fretboard_uses_state_tuning(self) -> None:
        state = instrument_from_tuning_id("dadgad")
        assert state.fretboard.tuning is DADGAD_TUNING.tuning

    def test_derived_fretboard_has_expected_fret_count(self) -> None:
        state = instrument_from_tuning_id("standard", fret_count=12)
        assert state.fretboard.fret_count == 12

    def test_derived_fretboard_supports_normal_queries(self) -> None:
        state = instrument_from_tuning_id("standard")
        assert state.fretboard.pitch_at(6, 0) == Pitch(PitchClass.E, 2)

    def test_two_equal_states_derive_equal_fretboards(self) -> None:
        first = instrument_from_tuning_id("standard")
        second = InstrumentState(
            tuning=STANDARD_TUNING.tuning,
            fret_count=22,
            tuning_id="standard",
            display_name="Standard",
        )
        assert first.fretboard == second.fretboard


class TestCustomConstruction:
    def test_custom_tuning_without_preset_id(self) -> None:
        tuning = _custom_tuning()
        state = InstrumentState(tuning=tuning, fret_count=24)
        assert state.tuning is tuning
        assert state.tuning_id is None
        assert state.display_name is None
        assert state.fretboard.tuning is tuning

    def test_arbitrary_string_count_accepted(self) -> None:
        tuning = _custom_tuning(count=7)
        state = InstrumentState(tuning=tuning, fret_count=22)
        assert state.fretboard.tuning.string_count == 7

    def test_zero_frets_accepted(self) -> None:
        state = InstrumentState(tuning=STANDARD_TUNING.tuning, fret_count=0)
        assert state.fret_count == 0
        assert state.fretboard == Fretboard(STANDARD_TUNING.tuning, 0)

    def test_custom_tuning_may_provide_own_display_name(self) -> None:
        tuning = _custom_tuning()
        state = InstrumentState(tuning=tuning, fret_count=24, display_name="My Tuning")
        assert state.display_name == "My Tuning"
        assert state.tuning_id is None


class TestStringPitchConstruction:
    STANDARD_PITCHES = (
        Pitch(PitchClass.E, 2),
        Pitch(PitchClass.A, 2),
        Pitch(PitchClass.D, 3),
        Pitch(PitchClass.G, 3),
        Pitch(PitchClass.B, 3),
        Pitch(PitchClass.E, 4),
    )

    def test_from_standard_pitches(self) -> None:
        state = instrument_from_string_pitches(self.STANDARD_PITCHES)
        assert tuple(string.open_pitch for string in state.tuning.strings) == (
            self.STANDARD_PITCHES
        )
        assert state.fretboard == Fretboard(state.tuning, DEFAULT_FRET_COUNT)

    def test_arbitrary_valid_pitches(self) -> None:
        pitches = (
            Pitch(PitchClass.C, 2),
            Pitch(PitchClass.F, 3),
            Pitch(PitchClass.GSHARP, 4),
        )
        state = instrument_from_string_pitches(pitches)
        assert state.tuning.string_count == 3
        assert tuple(string.open_pitch for string in state.tuning.strings) == pitches
        assert state.fretboard.pitch_at(3, 0) == Pitch(PitchClass.C, 2)

    def test_tuning_id_is_none(self) -> None:
        state = instrument_from_string_pitches(self.STANDARD_PITCHES)
        assert state.tuning_id is None

    def test_custom_display_name_preserved(self) -> None:
        state = instrument_from_string_pitches(self.STANDARD_PITCHES, display_name="My Tuning")
        assert state.display_name == "My Tuning"

    def test_default_display_name_is_custom(self) -> None:
        state = instrument_from_string_pitches(self.STANDARD_PITCHES)
        assert state.display_name == "Custom"

    def test_exact_string_numbering(self) -> None:
        state = instrument_from_string_pitches(self.STANDARD_PITCHES)
        assert {string.number for string in state.tuning.strings} == set(range(1, 7))
        assert state.tuning.string(6).open_pitch == Pitch(PitchClass.E, 2)
        assert state.tuning.string(1).open_pitch == Pitch(PitchClass.E, 4)

    def test_low_to_high_input_ordering(self) -> None:
        state = instrument_from_string_pitches(
            (
                Pitch(PitchClass.D, 2),
                Pitch(PitchClass.A, 2),
                Pitch(PitchClass.D, 3),
                Pitch(PitchClass.G, 3),
                Pitch(PitchClass.B, 3),
                Pitch(PitchClass.E, 4),
            )
        )
        assert state.tuning.string(6).open_pitch == Pitch(PitchClass.D, 2)
        assert state.tuning.string(1).open_pitch == Pitch(PitchClass.E, 4)

    def test_fret_count_preserved(self) -> None:
        state = instrument_from_string_pitches(self.STANDARD_PITCHES, fret_count=24)
        assert state.fret_count == 24
        assert state.fretboard == Fretboard(state.tuning, 24)

    def test_constructed_tuning_is_immutable(self) -> None:
        state = instrument_from_string_pitches(self.STANDARD_PITCHES)
        with pytest.raises(FrozenInstanceError):
            state.tuning.strings = ()  # type: ignore[misc]

    def test_empty_pitches_rejected(self) -> None:
        with pytest.raises(InvalidTuningError):
            instrument_from_string_pitches(())

    def test_negative_fret_count_rejected(self) -> None:
        with pytest.raises(InvalidPositionError):
            instrument_from_string_pitches(self.STANDARD_PITCHES, fret_count=-1)

    def test_drop_d_equivalent_is_not_the_drop_d_preset(self) -> None:
        drop_d_pitches = tuple(string.open_pitch for string in DROP_D_TUNING.tuning.strings)
        state = instrument_from_string_pitches(drop_d_pitches)
        assert state.tuning_id is None
        assert state.display_name == "Custom"
        assert state.tuning is not DROP_D_TUNING.tuning
        assert tuple(string.open_pitch for string in state.tuning.strings) == drop_d_pitches


class TestValidation:
    def test_negative_fret_count_rejected(self) -> None:
        with pytest.raises(InvalidPositionError):
            InstrumentState(tuning=STANDARD_TUNING.tuning, fret_count=-1)

    def test_negative_fret_count_rejected_for_preset(self) -> None:
        with pytest.raises(InvalidPositionError):
            instrument_from_tuning_id("standard", fret_count=-1)

    def test_negative_fret_count_error_is_a_value_error(self) -> None:
        with pytest.raises(ValueError):
            InstrumentState(tuning=STANDARD_TUNING.tuning, fret_count=-1)


class TestImmutability:
    def test_state_is_frozen(self) -> None:
        state = InstrumentState(tuning=STANDARD_TUNING.tuning, fret_count=22)
        with pytest.raises(FrozenInstanceError):
            state.fret_count = 24  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            state.tuning = DROP_D_TUNING.tuning  # type: ignore[misc]

    def test_changing_fret_count_requires_new_state(self) -> None:
        original = instrument_from_tuning_id("standard")
        changed = instrument_from_tuning_id("standard", fret_count=24)
        assert changed.fret_count == 24
        assert original.fret_count == DEFAULT_FRET_COUNT
        assert original != changed

    def test_value_equality_and_hash(self) -> None:
        first = instrument_from_tuning_id("standard")
        second = InstrumentState(
            tuning=STANDARD_TUNING.tuning,
            fret_count=22,
            tuning_id="standard",
            display_name="Standard",
        )
        assert first == second
        assert hash(first) == hash(second)


class TestNoQtDependency:
    def test_module_is_free_of_qt_and_ui(self) -> None:
        source = Path(instrument_state_module.__file__).read_text(encoding="utf-8")
        assert "from PySide6" not in source
        assert "import PySide6" not in source
        assert "guitar_app.ui" not in source
