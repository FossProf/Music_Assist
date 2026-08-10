# Domain model

This document describes the musical concepts modeled in Guitar Assist. The
guiding rule: significant musical concepts are **typed value objects or enums**,
never raw strings passed around the application.

## PitchClass

A pitch class: a normalized chromatic identity — a semitone offset from C
(0–11). It answers "which of the twelve chromatic pitch classes?" but does not
by itself choose an enharmonic spelling.

```python
PitchClass.FSHARP == 6
PitchClass.from_name("Gb") == PitchClass.FSHARP  # enharmonic input accepted
PitchClass.FSHARP.spelling() == "F#"
```

- Enharmonically equivalent spellings map to the same member (`C#` and `Db` are
  both `CSHARP`). All pitch-class math uses this normalized representation.
- Display spelling is currently normalized to sharps. Future context-aware
  spelling (e.g. `Eb` in a flat key) is a **music-theory/domain concern**, not
  merely a rendering concern: spellings such as `F` vs `E#`, `C` vs `B#`, or
  `Gb` vs `F#` may encode harmonic or scale-degree meaning. The UI may choose
  how a spelling is presented visually, but it must not invent theoretical
  spelling on its own. A full note-spelling engine is future work.

## Pitch

A specific pitch: a pitch class plus a scientific-pitch octave number.

```python
Pitch(PitchClass.C, 4).midi == 60  # middle C
Pitch(PitchClass.E, 2).midi == 40  # guitar low E
Pitch(PitchClass.E, 2).transpose(12)  # == Pitch(E, 3)
```

**Octave / MIDI convention.** Scientific pitch notation: middle C is `C4`.
MIDI note number is `12 * (octave + 1) + pitch_class`, so `C4 == 60` and the
standard guitar low E is `E2` (MIDI 40). This is the convention used throughout
guitar literature and MIDI software.

## ChromaticInterval

The chromatic (modulo-12) distance between two pitch classes. This is the type
used for root-relative fretboard analysis.

```python
ChromaticInterval.PERFECT_FIFTH.semitones == 7
ChromaticInterval.MINOR_THIRD.semitones == 3
ChromaticInterval.PERFECT_FIFTH.abbreviation == "5"
```

- The enum value is the ascending semitone displacement, always 0..11. There is
  **no octave member**, because pitch-class displacement is modulo 12.
- **It encodes only distance, not theoretical interval identity.** Six semitones
  may be spelled `#4` or `b5` depending on context; both map to `TRITONE`.
  Member names are conventional interval names used purely for readability.
- The `abbreviation` labels (`R`, `b2`, `2`, `b3`, `3`, `4`, `b5`, `5`, `b6`,
  `6`, `b7`, `7`) are default fretboard-analysis labels, not definitive
  theoretical spellings.

`chromatic_interval_between(source, target)` returns the ascending chromatic
displacement (mod 12) from one pitch class to another:

```python
chromatic_interval_between(PitchClass.A, PitchClass.E) == ChromaticInterval.PERFECT_FIFTH
chromatic_interval_between(PitchClass.C, PitchClass.FSHARP) == ChromaticInterval.TRITONE
```

A future theoretical `Interval` type may distinguish enharmonic interval
spellings — diminished fifth vs augmented fourth, augmented fifth vs minor
sixth, diminished seventh, compound intervals, and so on. That is intentionally
not modeled yet.

## GuitarString

A single string identified by its conventional number (1 = highest/thinnest,
6 = lowest for a standard guitar) and its open-string pitch.

```python
low_e = GuitarString(6, Pitch(PitchClass.E, 2))
low_e.pitch_at(0)  # E2 — open string
low_e.pitch_at(12)  # E3 — one octave up
```

The physical model is exact: **pitch at fret = open pitch + fret semitones**.

## Tuning

An immutable, validated collection of strings. A valid tuning must contain
exactly the string numbers `1..N` for an N-string instrument. Stored tuple
order may be anything — guitar display order is conventionally low to high
(`6, 5, 4, 3, 2, 1`) — but the set of string numbers must equal
`set(range(1, N + 1))`.

```python
STANDARD.string_count == 6
STANDARD.string(6).open_pitch == Pitch(PitchClass.E, 2)
```

`STANDARD` is the conventional six-string EADGBE tuning, stored low to high.
Malformed numbering — duplicates, gaps, starting at 2, or containing 0 — raises
`InvalidTuningError`. Alternate tunings and other string counts are
first-class: `Tuning(name, (GuitarString(3, D2), GuitarString(2, A2),
GuitarString(1, E4), ...))`.

## Fretboard, FretPosition, FretboardPosition

A `Fretboard` is a `Tuning` plus a fret count. Frets run 0 (open) through
`fret_count`.

- `FretPosition` is a pure location: `(string_number, fret)`.
- `FretboardPosition` adds the sounding `Pitch` and — when a root is given — the
  `interval_from_root`, a `ChromaticInterval` (the modulo-12 displacement from
  the root). It encodes distance only, not theoretical spelling.

```python
board = Fretboard(STANDARD, 12)

board.pitch_at(6, 12)  # Pitch(E, 3)
board.pitch_class_locations(PitchClass.C)  # 6 positions, one per string
board.pitch_locations(Pitch(E, 3))  # exact-octave E3 positions
board.position_at(5, 3, root=PitchClass.A)  # C3, MINOR_THIRD from A
list(board.positions(root=PitchClass.C))  # every position + displacement from C
```

## Planned concepts

The same style of typed value object will be used for:

- `ScaleFormula` / `Scale` (interval patterns and their root spellings)
- `ChordQuality` / `Chord` / `Triad`
- `Key`
- `Layer` / layer annotations (see `docs/architecture.md`)
- `Progression`

When a concept would otherwise be a raw string in the API (e.g. `"dorian"` or
`"maj7"`), prefer an enum or value object so that invalid musical states are
hard to express.

## Exceptions

- `InvalidPitchError` — unparseable note names, invalid pitch construction.
- `InvalidTuningError` — malformed tunings or string numbers.
- `InvalidPositionError` — string/fret positions outside the fretboard.

These are domain errors raised by the core engines; the application layer is
responsible for turning them into user-facing messages.
