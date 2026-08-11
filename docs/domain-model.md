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

## ScaleDegree

A diatonic scale degree: a position in the major-scale (diatonic) sequence plus
an accidental alteration. `number` is always 1..7; `alteration` is the semitone
deviation from the natural degree, bounded to -2..+2.

```python
ScaleDegree(1)  # 1  — tonic
ScaleDegree(3, -1)  # b3
ScaleDegree(4, 1)  # #4
ScaleDegree(7, -2)  # bb7
ScaleDegree(5, 2)  # ##5
```

- Natural-degree offsets follow the major scale: 1→0, 2→2, 3→4, 4→5, 5→7,
  6→9, 7→11. `chromatic_offset` is that offset plus the alteration, modulo 12.
- **A degree preserves its identity independently of the chromatic pitch it
  resolves to.** `#4` (`ScaleDegree(4, 1)`) and `b5` (`ScaleDegree(5, -1)`) are
  distinct values even though both have chromatic offset 6. The degree is not
  reducible to a `ChromaticInterval`.
- Out-of-range numbers or alterations raise `InvalidScaleDegreeError`.

## ScaleFormula

An immutable, ordered collection of `ScaleDegree` values, tonic first. It holds
at least one degree, rejects duplicate identical degrees, and supports sequence
access (indexing, slicing, iteration, `len`).

```python
MAJOR = ScaleFormula(
    (
        ScaleDegree(1),
        ScaleDegree(2),
        ScaleDegree(3),
        ScaleDegree(4),
        ScaleDegree(5),
        ScaleDegree(6),
        ScaleDegree(7),
    )
)
MAJOR.chromatic_offsets  # (0, 2, 4, 5, 7, 9, 11) as ChromaticIntervals
```

Because a formula stores degrees (not raw offsets), it can express spellings the
degree value encodes: `#4` and `b5` may coexist in one formula, resolving to the
same chromatic offset, without colliding. Named presets live in a separate
catalog (see below); `ScaleFormula` itself has no names.

## Scale, ScaleTone

A `Scale` binds a root `PitchClass` to a `ScaleFormula`, producing the concrete
tone set.

```python
scale = Scale(PitchClass.C, MAJOR)
scale.root  # PitchClass.C
scale.formula  # MAJOR
scale.pitch_classes  # (C, D, E, F, G, A, B)
```

- A `ScaleTone` pairs a preserved `ScaleDegree` with the `PitchClass` it
  resolves to. Derivation is `(root pitch-class value + degree chromatic
  offset) mod 12`.
- **Degree identity is preserved.** A formula containing both `#4` and `b5`
  produces two distinct `ScaleTone` values that share a pitch class. Tones are
  never reduced to a bare set/list of pitch classes.
- `tones`, `pitch_classes`, and `scale_degrees` are ordered like the formula.
  `pitch_classes` may repeat a pitch class when different degrees resolve to it.
- `tone_for(degree)` returns the tone bound to a degree in the formula and
  raises `InvalidScaleDegreeError` for a degree the formula does not contain.
- Transposition is achieved by constructing the same formula with a different
  root; there is no dedicated transpose API yet.
- Enharmonic spelling is out of scope: tones use the normalized `PitchClass`,
  and degree identity carries the theoretical distinction for now.

## Named scale formulas

Built-in, reusable `ScaleFormula` presets live in a theory-domain catalog,
separate from scale mechanics: `Scale` and `ScaleFormula` know nothing about
names such as "Major" or "Dorian".

```python
from guitar_app.core.theory.scale_formulas import MAJOR, IONIAN, SCALE_FORMULAS

IONIAN.formula is MAJOR.formula  # same formula, different identity
scale_formula_by_id("dorian")  # the Dorian entry
[entry.id for entry in SCALE_FORMULAS]  # stable enumeration order
```

- `NamedScaleFormula(id, name, formula)` pairs a stable programmatic ID
  (snake_case) with a human-readable display name and its `ScaleFormula`.
- Catalog entries: Major, Natural Minor, Major Pentatonic, Minor Pentatonic,
  and the seven modes (Ionian, Dorian, Phrygian, Lydian, Mixolydian, Aeolian,
  Locrian). Ionian reuses the Major formula and Aeolian reuses Natural Minor,
  so the same `ScaleFormula` instance backs both identities.
- `scale_formula_by_id(id)` returns the matching entry and raises
  `UnknownScaleFormulaError` for an unknown ID.
- No aliases, fuzzy search, localization, user-defined catalogs, persistence,
  or categories yet.

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

## ScaleFretboardPosition, map_scale_to_fretboard

Scale-to-fretboard mapping is the integration boundary between the theory
domain and the fretboard domain. `Scale` itself never imports guitar or
fretboard modules; a focused function in `core.fretboard` projects a scale onto
a fretboard.

```python
from guitar_app.core.fretboard.scale_mapping import map_scale_to_fretboard

map_scale_to_fretboard(board, Scale(PitchClass.C, MAJOR.formula))
```

- `ScaleFretboardPosition` preserves the string/fret location, the sounding
  `Pitch`, the `ScaleDegree`, and the root-relative `ChromaticInterval`. It
  contains **no rendering information**.
- Matching emits **one result per matching `ScaleTone`**. If a scale contains
  two degrees resolving to the same pitch class (e.g. `#4` and `b5`), the same
  fretboard location yields two results, one per degree — results are never
  collapsed by pitch class.
- Ordering is deterministic: fretboard iteration order (stored string order,
  lowest fret first), then formula/tone order for multiple matches at one
  position.

## IntervalFretboardPosition, map_intervals_to_fretboard

Interval-to-fretboard mapping is the chromatic-displacement equivalent of the
scale mapping: **every** fretboard position annotated with its root-relative
`ChromaticInterval`, with no filtering or grouping.

```python
from guitar_app.core.fretboard.interval_mapping import map_intervals_to_fretboard

map_intervals_to_fretboard(board, PitchClass.A)
```

- `IntervalFretboardPosition` preserves the string/fret location, the sounding
  `Pitch`, and the root-relative `ChromaticInterval`. It contains **no
  rendering information** and provides a `pitch_class` convenience property.
- For each position in fretboard iteration order (stored string order, lowest
  fret first), the interval is `chromatic_interval_between(root,
  position.pitch_class)` — always exactly one result per position.
- The mapping represents **chromatic displacement only** (`A`→`R`, `Bb`→`b2`,
  `B`→`2`, `C`→`b3`, `C#`→`3`, `D`→`4`, `Eb`→`b5`, `E`→`5`, `F`→`b6`,
  `F#`→`6`, `G`→`b7`, `G#`→`7`). It does not introduce a theoretical
  interval/spelling model; the degree-style labels come from
  `ChromaticInterval.abbreviation`.
- No service or UI exists yet; the mapping is a raw fretboard domain function.

## Layer results

Fretboard overlays are implemented as layers in `core.layers` (see
`docs/architecture.md`). A layer has a stable `id`, a human-readable `name`,
and an `evaluate` operation returning an immutable `LayerResult` — layer
metadata plus a tuple of layer-specific annotations. Every annotation
identifies its fretboard location via a `FretPosition`; results never contain
rendering fields such as color, shape, opacity, font, or pixel coordinates.

`ScaleLayer` (`id="scale"`, `name="Scale"`) is the first concrete layer. It is
stateless: the fretboard and scale are supplied at evaluation time, and its
result preserves the `ScaleFretboardPosition` data by delegating to
`map_scale_to_fretboard`.

`IntervalLayer` (`id="interval"`, `name="Intervals"`) is the second concrete
layer. It is stateless: the fretboard and root are supplied at evaluation time,
and its result preserves the `IntervalFretboardPosition` data by delegating to
`map_intervals_to_fretboard`.

## Planned concepts

The same style of typed value object will be used for:

- `ChordQuality` / `Chord` / `Triad`
- `Key`
- `Progression`

When a concept would otherwise be a raw string in the API (e.g. `"dorian"` or
`"maj7"`), prefer an enum or value object so that invalid musical states are
hard to express.

## Exceptions

- `InvalidPitchError` — unparseable note names, invalid pitch construction.
- `InvalidTuningError` — malformed tunings or string numbers.
- `InvalidPositionError` — string/fret positions outside the fretboard.
- `InvalidScaleDegreeError` — invalid scale degrees or malformed scale formulas.
- `UnknownScaleFormulaError` — a named scale formula ID is not in the catalog.

These are domain errors raised by the core engines; the application layer is
responsible for turning them into user-facing messages.
