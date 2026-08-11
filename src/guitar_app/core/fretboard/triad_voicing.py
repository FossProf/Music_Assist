"""Adjacent-string triad voicings: three-note voicings on three adjacent strings.

This is the first guitar-specific voicing model. Given a ``Fretboard`` and a
``Triad``, it finds every combination of one triad tone per string across the
adjacent three-string sets (1-2-3, 2-3-4, ...) that satisfies a deliberately
coarse playability rule (fret span within a named limit) and classifies the
inversion from the actual lowest sounding pitch.

The tone mapping and the voicing detection stay separate:
``map_triad_to_fretboard`` supplies the source data and is never re-derived
here.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import product

from guitar_app.core.errors import InvalidVoicingError
from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.triad_mapping import (
    TriadFretboardPosition,
    map_triad_to_fretboard,
)
from guitar_app.core.theory.pitch import Pitch
from guitar_app.core.theory.triad import Triad, TriadInversion

#: Default maximum fret span for the first-pass playability rule.
DEFAULT_MAX_FRET_SPAN = 4


def _adjacent_string_sets(string_count: int) -> tuple[tuple[int, int, int], ...]:
    """Return every adjacent three-string set for an N-string instrument."""
    return tuple((s, s + 1, s + 2) for s in range(1, string_count - 1))


@dataclass(frozen=True, slots=True)
class TriadVoicing:
    """A three-note triad voicing on one adjacent three-string set.

    Invariants (enforced at construction):

    * exactly three tones, one per string in ``string_set``, stored in
      string-set order (ascending string number)
    * all three triad degree identities occur exactly once
    * every tone belongs to the same ``Triad`` (guaranteed by construction
      from ``map_triad_to_fretboard``; not independently checkable here)

    ``inversion`` is classified from the actual lowest sounding pitch, never
    from physical string number. No fingering or finger-number data is stored.
    """

    string_set: tuple[int, int, int]
    tones: tuple[TriadFretboardPosition, ...]
    inversion: TriadInversion

    def __post_init__(self) -> None:
        if len(self.string_set) != 3 or not (
            self.string_set[0] >= 1 and self.string_set[0] < self.string_set[1] < self.string_set[2]
        ):
            raise InvalidVoicingError(
                f"string_set must be three distinct ascending strings, got {self.string_set}"
            )
        if len(self.tones) != 3:
            raise InvalidVoicingError(
                f"a triad voicing needs exactly three tones, got {len(self.tones)}"
            )
        if tuple(tone.position.string_number for tone in self.tones) != self.string_set:
            raise InvalidVoicingError(
                f"tones must contain exactly one position per string in {self.string_set}"
            )
        if len({tone.degree for tone in self.tones}) != 3:
            raise InvalidVoicingError(
                "tones must contain each triad degree exactly once, got "
                f"{[tone.degree.label for tone in self.tones]}"
            )

    @property
    def fret_span(self) -> int:
        """Highest minus lowest fret across the three tones (open = 0)."""
        frets = [tone.position.fret for tone in self.tones]
        return max(frets) - min(frets)

    @property
    def lowest_pitch(self) -> Pitch:
        """The lowest sounding pitch of the voicing (the bass)."""
        return min((tone.pitch for tone in self.tones), key=lambda pitch: pitch.midi)


def find_triad_voicings(
    fretboard: Fretboard,
    triad: Triad,
    *,
    max_fret_span: int = DEFAULT_MAX_FRET_SPAN,
) -> tuple[TriadVoicing, ...]:
    """Return playable adjacent-string triad voicings for ``triad`` on ``fretboard``.

    Playability is the first-pass geometric rule: exactly one note per string
    on three adjacent strings, all three triad tones present exactly once, and
    a fret span (highest minus lowest fret, open strings count as 0) of at most
    ``max_fret_span``. This is deliberately a coarse heuristic, not a complete
    ergonomic model: finger stretches, barre technique, hand size, and physical
    impossibility are not modeled.

    Inversion is classified from the actual lowest sounding pitch of each
    completed voicing (``min`` pitch), never from physical string number, which
    matters for alternate tunings where nominally lower strings may not sound
    lowest.

    Results are deterministic: string sets in ascending tuple order, then
    lowest fret ascending, then the fret tuple in string-set order, with the
    inversion as a final stable tie-breaker (unreachable in practice because
    the fret tuple uniquely identifies a combination).

    Raises ``ValueError`` for a negative ``max_fret_span``. A fretboard with
    fewer than three strings yields no voicings rather than failing.
    """
    if max_fret_span < 0:
        raise ValueError(f"max_fret_span must be >= 0, got {max_fret_span}")

    mapped = map_triad_to_fretboard(fretboard, triad)
    if fretboard.tuning.string_count < 3:
        return ()

    by_string: dict[int, list[TriadFretboardPosition]] = defaultdict(list)
    for position in mapped:
        by_string[position.position.string_number].append(position)

    voicings: list[TriadVoicing] = []
    for string_set in _adjacent_string_sets(fretboard.tuning.string_count):
        candidates = [by_string.get(string, ()) for string in string_set]
        if any(not candidate for candidate in candidates):
            continue
        for combo in product(*candidates):
            tones = tuple(combo)
            if len({tone.degree for tone in tones}) != 3:
                continue
            frets = tuple(tone.position.fret for tone in tones)
            if max(frets) - min(frets) > max_fret_span:
                continue
            bass_tone = min(tones, key=lambda tone: tone.pitch.midi)
            voicings.append(
                TriadVoicing(
                    string_set=string_set,
                    tones=tones,
                    inversion=TriadInversion.from_lowest_degree(bass_tone.degree),
                )
            )

    voicings.sort(
        key=lambda voicing: (
            voicing.string_set,
            min(tone.position.fret for tone in voicing.tones),
            tuple(tone.position.fret for tone in voicing.tones),
            voicing.inversion.value,
        )
    )
    return tuple(voicings)
