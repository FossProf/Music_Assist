"""Built-in named tuning presets.

Keeps named tuning definitions separate from tuning mechanics:
:class:`~guitar_app.core.instrument.tuning.Tuning` and
:class:`~guitar_app.core.instrument.guitar_string.GuitarString` know nothing
about catalog IDs or preset names. Preset IDs are intended to become stable
persistence/API identifiers and must not be renamed casually.
"""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.errors import UnknownTuningError
from guitar_app.core.instrument.guitar_string import GuitarString
from guitar_app.core.instrument.tuning import STANDARD, Tuning
from guitar_app.core.theory.pitch import Pitch, PitchClass


def _low_to_high(*pitches: Pitch) -> tuple[GuitarString, ...]:
    """Build strings ``N..1`` from low-to-high ``pitches`` (first = lowest)."""
    count = len(pitches)
    return tuple(
        GuitarString(number, pitch)
        for number, pitch in zip(range(count, 0, -1), pitches, strict=True)
    )


def _six_string(name: str, *pitches: Pitch) -> Tuning:
    """Build a six-string ``Tuning`` from low-to-high open-string pitches."""
    return Tuning(name, _low_to_high(*pitches))


@dataclass(frozen=True, slots=True)
class NamedTuning:
    """A named tuning preset in the built-in catalog.

    ``id`` is the stable programmatic identifier (snake_case); ``name`` is the
    human-readable display name. The wrapped ``tuning`` is immutable. Preset
    IDs are intended to become stable persistence/API identifiers, so they
    must not be renamed casually.
    """

    id: str
    name: str
    tuning: Tuning

    def __str__(self) -> str:
        return self.name


#: Standard six-string EADGBE tuning (the canonical ``STANDARD`` instance).
STANDARD_TUNING = NamedTuning("standard", "Standard", STANDARD)

DROP_D_TUNING = NamedTuning(
    "drop_d",
    "Drop D",
    _six_string(
        "Drop D",
        Pitch(PitchClass.D, 2),
        Pitch(PitchClass.A, 2),
        Pitch(PitchClass.D, 3),
        Pitch(PitchClass.G, 3),
        Pitch(PitchClass.B, 3),
        Pitch(PitchClass.E, 4),
    ),
)

D_STANDARD_TUNING = NamedTuning(
    "d_standard",
    "D Standard",
    _six_string(
        "D Standard",
        Pitch(PitchClass.D, 2),
        Pitch(PitchClass.G, 2),
        Pitch(PitchClass.C, 3),
        Pitch(PitchClass.F, 3),
        Pitch(PitchClass.A, 3),
        Pitch(PitchClass.D, 4),
    ),
)

#: Eb Standard — pitch classes are the normalized sharp spellings of
#: Eb/Ab/Db/Gb/Bb.
EB_STANDARD_TUNING = NamedTuning(
    "eb_standard",
    "Eb Standard",
    _six_string(
        "Eb Standard",
        Pitch(PitchClass.DSHARP, 2),
        Pitch(PitchClass.GSHARP, 2),
        Pitch(PitchClass.CSHARP, 3),
        Pitch(PitchClass.FSHARP, 3),
        Pitch(PitchClass.ASHARP, 3),
        Pitch(PitchClass.DSHARP, 4),
    ),
)

DADGAD_TUNING = NamedTuning(
    "dadgad",
    "DADGAD",
    _six_string(
        "DADGAD",
        Pitch(PitchClass.D, 2),
        Pitch(PitchClass.A, 2),
        Pitch(PitchClass.D, 3),
        Pitch(PitchClass.G, 3),
        Pitch(PitchClass.A, 3),
        Pitch(PitchClass.D, 4),
    ),
)

OPEN_D_TUNING = NamedTuning(
    "open_d",
    "Open D",
    _six_string(
        "Open D",
        Pitch(PitchClass.D, 2),
        Pitch(PitchClass.A, 2),
        Pitch(PitchClass.D, 3),
        Pitch(PitchClass.FSHARP, 3),
        Pitch(PitchClass.A, 3),
        Pitch(PitchClass.D, 4),
    ),
)

OPEN_E_TUNING = NamedTuning(
    "open_e",
    "Open E",
    _six_string(
        "Open E",
        Pitch(PitchClass.E, 2),
        Pitch(PitchClass.B, 2),
        Pitch(PitchClass.E, 3),
        Pitch(PitchClass.GSHARP, 3),
        Pitch(PitchClass.B, 3),
        Pitch(PitchClass.E, 4),
    ),
)

OPEN_G_TUNING = NamedTuning(
    "open_g",
    "Open G",
    _six_string(
        "Open G",
        Pitch(PitchClass.D, 2),
        Pitch(PitchClass.G, 2),
        Pitch(PitchClass.D, 3),
        Pitch(PitchClass.G, 3),
        Pitch(PitchClass.B, 3),
        Pitch(PitchClass.D, 4),
    ),
)

#: Every named tuning preset, in stable enumeration order.
TUNING_PRESETS: tuple[NamedTuning, ...] = (
    STANDARD_TUNING,
    DROP_D_TUNING,
    D_STANDARD_TUNING,
    EB_STANDARD_TUNING,
    DADGAD_TUNING,
    OPEN_D_TUNING,
    OPEN_E_TUNING,
    OPEN_G_TUNING,
)


def available_tunings() -> tuple[NamedTuning, ...]:
    """Return the catalog's named tunings in stable order.

    The returned values are the shared :class:`NamedTuning` instances; callers
    must not mutate them.
    """
    return TUNING_PRESETS


def tuning_by_id(tuning_id: str) -> NamedTuning:
    """Return the named tuning with the given stable ID.

    Raises :class:`UnknownTuningError` if the ID is not in the catalog.
    """
    for entry in TUNING_PRESETS:
        if entry.id == tuning_id:
            return entry
    raise UnknownTuningError(f"unknown tuning id: {tuning_id!r}")
