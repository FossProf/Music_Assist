"""Tests for the built-in named tuning presets."""

from dataclasses import FrozenInstanceError

import pytest

from guitar_app.core.errors import UnknownTuningError
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD
from guitar_app.core.instrument.tuning_presets import (
    D_STANDARD_TUNING,
    DADGAD_TUNING,
    DROP_D_TUNING,
    EB_STANDARD_TUNING,
    OPEN_D_TUNING,
    OPEN_E_TUNING,
    OPEN_G_TUNING,
    STANDARD_TUNING,
    TUNING_PRESETS,
    NamedTuning,
    available_tunings,
    tuning_by_id,
)
from guitar_app.core.theory.pitch import Pitch, PitchClass


def _pitches(entry: NamedTuning) -> tuple[Pitch, ...]:
    return tuple(string.open_pitch for string in entry.tuning.strings)


def _P(name: str, octave: int) -> Pitch:
    return Pitch(PitchClass.from_name(name), octave)


class TestOpenStringPitches:
    @pytest.mark.parametrize(
        ("entry", "expected"),
        [
            (
                STANDARD_TUNING,
                (_P("E", 2), _P("A", 2), _P("D", 3), _P("G", 3), _P("B", 3), _P("E", 4)),
            ),
            (
                DROP_D_TUNING,
                (_P("D", 2), _P("A", 2), _P("D", 3), _P("G", 3), _P("B", 3), _P("E", 4)),
            ),
            (
                D_STANDARD_TUNING,
                (_P("D", 2), _P("G", 2), _P("C", 3), _P("F", 3), _P("A", 3), _P("D", 4)),
            ),
            (
                EB_STANDARD_TUNING,
                (_P("Eb", 2), _P("Ab", 2), _P("Db", 3), _P("Gb", 3), _P("Bb", 3), _P("Eb", 4)),
            ),
            (
                DADGAD_TUNING,
                (_P("D", 2), _P("A", 2), _P("D", 3), _P("G", 3), _P("A", 3), _P("D", 4)),
            ),
            (
                OPEN_D_TUNING,
                (_P("D", 2), _P("A", 2), _P("D", 3), _P("F#", 3), _P("A", 3), _P("D", 4)),
            ),
            (
                OPEN_E_TUNING,
                (_P("E", 2), _P("B", 2), _P("E", 3), _P("G#", 3), _P("B", 3), _P("E", 4)),
            ),
            (
                OPEN_G_TUNING,
                (_P("D", 2), _P("G", 2), _P("D", 3), _P("G", 3), _P("B", 3), _P("D", 4)),
            ),
        ],
    )
    def test_open_string_pitches(self, entry: NamedTuning, expected: tuple[Pitch, ...]) -> None:
        assert _pitches(entry) == expected


class TestStringNumbering:
    def test_every_preset_numbered_low_to_high(self) -> None:
        for entry in TUNING_PRESETS:
            assert [string.number for string in entry.tuning.strings] == [6, 5, 4, 3, 2, 1]

    def test_every_preset_satisfies_exact_string_number_invariant(self) -> None:
        for entry in TUNING_PRESETS:
            count = entry.tuning.string_count
            numbers = {string.number for string in entry.tuning.strings}
            assert numbers == set(range(1, count + 1))

    def test_lowest_string_is_lowest_pitch(self) -> None:
        for entry in TUNING_PRESETS:
            lowest = min(string.open_pitch.midi for string in entry.tuning.strings)
            assert entry.tuning.string(6).open_pitch.midi == lowest

    def test_spot_check_lowest_and_highest_strings(self) -> None:
        assert DROP_D_TUNING.tuning.string(6).open_pitch == _P("D", 2)
        assert DROP_D_TUNING.tuning.string(1).open_pitch == _P("E", 4)
        assert OPEN_G_TUNING.tuning.string(6).open_pitch == _P("D", 2)
        assert OPEN_G_TUNING.tuning.string(1).open_pitch == _P("D", 4)


class TestNamesAndIds:
    @pytest.mark.parametrize(
        ("entry", "expected_id", "expected_name"),
        [
            (STANDARD_TUNING, "standard", "Standard"),
            (DROP_D_TUNING, "drop_d", "Drop D"),
            (D_STANDARD_TUNING, "d_standard", "D Standard"),
            (EB_STANDARD_TUNING, "eb_standard", "Eb Standard"),
            (DADGAD_TUNING, "dadgad", "DADGAD"),
            (OPEN_D_TUNING, "open_d", "Open D"),
            (OPEN_E_TUNING, "open_e", "Open E"),
            (OPEN_G_TUNING, "open_g", "Open G"),
        ],
    )
    def test_stable_ids_and_names(
        self, entry: NamedTuning, expected_id: str, expected_name: str
    ) -> None:
        assert entry.id == expected_id
        assert entry.name == expected_name

    def test_ids_are_unique(self) -> None:
        ids = [entry.id for entry in TUNING_PRESETS]
        assert len(ids) == len(set(ids))


class TestCatalogOrder:
    def test_stable_catalog_order(self) -> None:
        assert [entry.id for entry in available_tunings()] == [
            "standard",
            "drop_d",
            "d_standard",
            "eb_standard",
            "dadgad",
            "open_d",
            "open_e",
            "open_g",
        ]

    def test_catalog_exposes_shared_instances(self) -> None:
        assert available_tunings() == TUNING_PRESETS
        assert available_tunings()[0] is STANDARD_TUNING
        assert available_tunings()[3] is EB_STANDARD_TUNING


class TestLookup:
    def test_lookup_by_id(self) -> None:
        assert tuning_by_id("standard") is STANDARD_TUNING
        assert tuning_by_id("drop_d") is DROP_D_TUNING
        assert tuning_by_id("d_standard") is D_STANDARD_TUNING
        assert tuning_by_id("eb_standard") is EB_STANDARD_TUNING
        assert tuning_by_id("dadgad") is DADGAD_TUNING
        assert tuning_by_id("open_d") is OPEN_D_TUNING
        assert tuning_by_id("open_e") is OPEN_E_TUNING
        assert tuning_by_id("open_g") is OPEN_G_TUNING

    def test_unknown_id_raises(self) -> None:
        with pytest.raises(UnknownTuningError):
            tuning_by_id("open_c")

    def test_unknown_id_error_is_a_value_error(self) -> None:
        with pytest.raises(ValueError):
            tuning_by_id("not-a-tuning")


class TestNamingRule:
    def test_preset_label_and_intrinsic_label_are_distinct_for_standard(self) -> None:
        assert STANDARD_TUNING.name == "Standard"
        assert STANDARD_TUNING.tuning.name == "Standard (EADGBE)"

    def test_intrinsic_label_is_not_the_user_facing_label(self) -> None:
        user_facing = {entry.name for entry in TUNING_PRESETS}
        intrinsic = {entry.tuning.name for entry in TUNING_PRESETS}
        assert user_facing == {
            "Standard",
            "Drop D",
            "D Standard",
            "Eb Standard",
            "DADGAD",
            "Open D",
            "Open E",
            "Open G",
        }
        assert intrinsic == {
            "Standard (EADGBE)",
            "Drop D (DADGBE)",
            "D Standard (DGCFAD)",
            "Eb Standard (EbAbDbGbBbEb)",
            "DADGAD",
            "Open D (DADF#AD)",
            "Open E (EBEG#BE)",
            "Open G (DGDGBD)",
        }


class TestStandardReuse:
    def test_catalog_standard_reuses_existing_standard(self) -> None:
        assert STANDARD_TUNING.tuning is STANDARD
        assert tuning_by_id("standard").tuning is STANDARD

    def test_catalog_standard_matches_existing_standard_pitches(self) -> None:
        assert _pitches(STANDARD_TUNING) == tuple(string.open_pitch for string in STANDARD.strings)
        assert _pitches(STANDARD_TUNING) == (
            _P("E", 2),
            _P("A", 2),
            _P("D", 3),
            _P("G", 3),
            _P("B", 3),
            _P("E", 4),
        )

    def test_standard_remains_a_six_string_tuning(self) -> None:
        assert STANDARD.string_count == 6
        assert STANDARD.string(6).open_pitch == _P("E", 2)


class TestImmutability:
    def test_catalog_tuple_cannot_be_mutated(self) -> None:
        with pytest.raises(AttributeError):
            TUNING_PRESETS.append(STANDARD_TUNING)  # type: ignore[attr-defined]
        with pytest.raises(TypeError):
            TUNING_PRESETS[0] = DROP_D_TUNING  # type: ignore[index]

    def test_named_tuning_is_frozen(self) -> None:
        entry = NamedTuning("test", "Test", STANDARD)
        with pytest.raises(FrozenInstanceError):
            entry.id = "other"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            entry.name = "Other"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            entry.tuning = DROP_D_TUNING.tuning  # type: ignore[misc]

    def test_wrapped_tuning_is_immutable(self) -> None:
        with pytest.raises(FrozenInstanceError):
            STANDARD_TUNING.tuning.name = "Standard"  # type: ignore[misc]

    def test_strings_are_guitar_strings(self) -> None:
        for entry in TUNING_PRESETS:
            assert all(isinstance(string, GuitarString) for string in entry.tuning.strings)
