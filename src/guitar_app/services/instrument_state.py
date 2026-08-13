"""Application-level instrument/workspace state for the active fretboard.

``InstrumentState`` is the immutable source of the active
:class:`~guitar_app.core.fretboard.fretboard.Fretboard` for the desktop UI and
future persistence/AI/API access. It lives above ``core`` (in ``services``) so
the core remains reusable and context-free: existing musical services keep
accepting a ``Fretboard`` and never depend on this state.

The state is not yet persistent and is not UI state; it is the future bridge
from the tuning preset catalog to the active fretboard:

``tuning preset catalog -> InstrumentState -> Fretboard -> services/layers``
"""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.errors import InvalidPositionError
from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.instrument.tuning import Tuning, tuning_from_low_to_high
from guitar_app.core.instrument.tuning_presets import tuning_by_id
from guitar_app.core.theory.pitch import Pitch

#: Default fret count for a normal guitar workspace (frets 0..22).
DEFAULT_FRET_COUNT = 22


@dataclass(frozen=True, slots=True)
class InstrumentState:
    """Immutable active-instrument configuration.

    ``tuning`` is the active tuning and ``fret_count`` the highest playable
    fret (frets run 0..``fret_count``, matching :class:`Fretboard`).
    ``tuning_id`` optionally records the built-in preset the state originated
    from (``None`` for custom tunings); ``display_name`` is the optional
    user-facing label — the preset's ``NamedTuning.name`` when created from the
    catalog, or a caller-supplied label for custom tunings.
    """

    tuning: Tuning
    fret_count: int
    tuning_id: str | None = None
    display_name: str | None = None

    def __post_init__(self) -> None:
        if self.fret_count < 0:
            raise InvalidPositionError(f"fret count must be >= 0, got {self.fret_count}")

    @property
    def fretboard(self) -> Fretboard:
        """The active fretboard derived from this state.

        A fresh :class:`Fretboard` is derived on every access; nothing is
        cached, so the state stays immutable and its value semantics simple.
        """
        return Fretboard(self.tuning, self.fret_count)


def instrument_from_tuning_id(
    tuning_id: str,
    *,
    fret_count: int = DEFAULT_FRET_COUNT,
) -> InstrumentState:
    """Build the instrument state for the built-in preset ``tuning_id``.

    Resolves the ID through the tuning catalog, preserving the preset ID and
    its user-facing display name, and uses the preset's :class:`Tuning`.
    Unknown IDs propagate :class:`UnknownTuningError`.
    """
    named = tuning_by_id(tuning_id)
    return InstrumentState(
        tuning=named.tuning,
        fret_count=fret_count,
        tuning_id=named.id,
        display_name=named.name,
    )


def instrument_from_string_pitches(
    pitches: tuple[Pitch, ...],
    *,
    fret_count: int = DEFAULT_FRET_COUNT,
    display_name: str = "Custom",
) -> InstrumentState:
    """Build a custom instrument state from explicit low-to-high pitches.

    ``pitches`` is ordered **low → high**: the first entry is the conventional
    lowest string (string ``N`` for an ``N``-string tuning) and the last entry
    is the highest (string 1). String numbers ``N..1`` are derived from that
    order via :func:`tuning_from_low_to_high`, reusing the existing
    :class:`GuitarString` and :class:`Tuning` construction and validation.

    The resulting state carries no preset identity (``tuning_id`` is ``None``)
    and preserves ``display_name`` (default ``"Custom"``). Preset identity
    describes origin/selection, never inferred pitch equality, so a custom
    state is never silently identified as a built-in preset.
    """
    tuning = tuning_from_low_to_high(display_name, pitches)
    return InstrumentState(
        tuning=tuning,
        fret_count=fret_count,
        tuning_id=None,
        display_name=display_name,
    )


#: Canonical application default: Standard tuning, 22 frets.
DEFAULT_INSTRUMENT_STATE = instrument_from_tuning_id("standard")
