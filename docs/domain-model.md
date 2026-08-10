# Domain model

This document describes the musical concepts modeled in Guitar Assist. The
guiding rule: significant musical concepts are **typed value objects or enums**,
never raw strings passed around the application.

## PitchClass

A pitch class, normalized internally to a semitone offset from C (0–11).

```python
PitchClass.FSHARP == 6
PitchClass.from_name("Gb") == PitchClass.FSHARP  # enharmonic input accepted
PitchClass.FSHARP.spelling() == "F#"
```

- Enharmonically equivalent spellings map to the same member (`C#` and `Db` are
  both `CSHARP`). All pitch-class math uses this normalized representation.
- Display spelling is currently fixed to sharps. Context-aware spelling (e.g.
  `Eb` in a flat key) is planned; it will be a *rendering* concern layered on
  top of the same normalized value.

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

## Interval

A named interval from unison through one octave, whose enum value is its size in
semitones.

```python
Interval.PERFECT_FIFTH == 7
Interval.MINOR_THIRD == 3
Interval.PERFECT_FIFTH.abbreviation == "5"
```

`interval_between(source, target)` returns the ascending pitch-class interval
(mod 12) from one pitch class to another:

```python
interval_between(PitchClass.E, PitchClass.A) == Interval.PERFECT_FOURTH
interval_between(PitchClass.A, PitchClass.E) == Interval.PERFECT_FIFTH
```

Compound intervals (larger than an octave) are not modeled yet; a perfect
twelfth can be expressed as octave + fifth.

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

An immutable, validated collection of strings. String numbers must be unique
and positive; a tuning must have at least one string.

```python
STANDARD.string_count == 6
STANDARD.string(6).open_pitch == Pitch(PitchClass.E, 2)
```

`STANDARD` is the conventional six-string EADGBE tuning, stored low to high
(string 6 first). Alternate tunings and other string counts are first-class:
`Tuning(name, (GuitarString(6, D2), GuitarString(5, A2), ...))`.

## Fretboard, FretPosition, FretboardPosition

A `Fretboard` is a `Tuning` plus a fret count. Frets run 0 (open) through
`fret_count`.

- `FretPosition` is a pure location: `(string_number, fret)`.
- `FretboardPosition` adds the sounding `Pitch` and — when a root is given — the
  `interval_from_root` (a pitch-class `Interval`).

```python
board = Fretboard(STANDARD, 12)

board.pitch_at(6, 12)  # Pitch(E, 3)
board.pitch_class_locations(PitchClass.C)  # 6 positions, one per string
board.pitch_locations(Pitch(E, 3))  # exact-octave E3 positions
board.position_at(5, 3, root=PitchClass.A)  # C3, MINOR_THIRD from A
list(board.positions(root=PitchClass.C))  # every position + interval from C
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
