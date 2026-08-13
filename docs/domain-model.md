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

## Mode, parallel and relative relationships

A `Mode` is a typed enum for the seven modes of the major scale, each bound to
its existing `NamedScaleFormula` catalog entry — no formulas are redefined.

```python
from guitar_app.core.theory.mode import (
    Mode,
    available_modes,
    parallel_mode,
    relative_mode,
    parent_major_root_for,
)

Mode.DORIAN.id  # "dorian"
Mode.DORIAN.display_name  # "Dorian"
Mode.DORIAN.degree  # 2 — the mode's degree within the parent major scale
Mode.DORIAN.scale_formula  # the catalog's DORIAN NamedScaleFormula
Mode.DORIAN.altered_degrees_from_ionian  # (b3, b7) as ScaleDegrees
```

- Members are declared in canonical order: Ionian, Dorian, Phrygian, Lydian,
  Mixolydian, Aeolian, Locrian. `available_modes()` returns them in that order.
- Each mode exposes a stable snake_case `id`, a human-readable `display_name`,
  its `degree` (1..7) within the parent major scale, the associated catalog
  `NamedScaleFormula` (`scale_formula` — the same instance the catalog uses),
  and `altered_degrees_from_ionian`, the degrees altered relative to Ionian:
  `()`, `(b3, b7)`, `(b2, b3, b6, b7)`, `(#4,)`, `(b7,)`, `(b3, b6, b7)`,
  `(b2, b3, b5, b6, b7)`. The altered degrees are **derived** from the mode's
  formula (every degree with a non-zero alteration), not stored separately, so
  the metadata can never drift from the formula.
- Ionian reuses the Major formula and Aeolian reuses Natural Minor, exactly as
  in the named-formula catalog: the same `ScaleFormula` instance backs both.

**Parallel modes — same root, different formula.** The scale is built on the
same tonal root with the mode's formula:

```python
parallel_mode(PitchClass.A, Mode.IONIAN)  # A Ionian:  A B C# D E F# G#
parallel_mode(PitchClass.A, Mode.DORIAN)  # A Dorian:  A B C D E F# G
parallel_mode(PitchClass.A, Mode.PHRYGIAN)  # A Phrygian: A Bb C D E F G
```

**Relative modes — same pitch collection, different tonal center.** The modal
root is derived from the parent major scale's natural degree offsets (the
existing major-scale degree table), never a hard-coded pitch-name table:

```python
relative_mode(PitchClass.C, Mode.DORIAN)  # D Dorian
relative_mode(PitchClass.C, Mode.AEOLIAN)  # A Aeolian
relative_mode(PitchClass.C, Mode.LOCRIAN)  # B Locrian
```

**Parent-major reverse relationship.** `parent_major_root_for(modal_root, mode)`
returns the major-scale root that contains the modal root as the mode's degree:

```python
parent_major_root_for(PitchClass.D, Mode.DORIAN)  # C
parent_major_root_for(PitchClass.A, Mode.AEOLIAN)  # C
parent_major_root_for(PitchClass.G, Mode.MIXOLYDIAN)  # C
```

The relationship round-trips: for every parent root and mode,
`parent_major_root_for(relative_mode(parent, mode).root, mode) == parent`, and
the reverse direction holds too. These pure-theory helpers keep the future Mode
Explorer's parallel/relative view switching in the domain layer instead of
recomputing relationships in Qt code.

The degree formulas are pinned exactly:

| Mode       | Formula                 | Altered vs Ionian          |
| ---------- | ----------------------- | -------------------------- |
| Ionian     | 1 2 3 4 5 6 7           |                            |
| Dorian     | 1 2 b3 4 5 6 b7         | b3, b7                     |
| Phrygian   | 1 b2 b3 4 5 b6 b7       | b2, b3, b6, b7             |
| Lydian     | 1 2 3 #4 5 6 7          | #4                         |
| Mixolydian | 1 2 3 4 5 6 b7          | b7                         |
| Aeolian    | 1 2 b3 4 5 b6 b7        | b3, b6, b7                 |
| Locrian    | 1 b2 b3 4 b5 b6 b7      | b2, b3, b5, b6, b7         |

Mode is pure theory: it references only `PitchClass`, `Scale`, `ScaleDegree`,
and the scale-formula catalog, and adds no fretboard, instrument, service, or
UI concepts.

## Triad, TriadTone, TriadQuality

The pure theory model of a triad: what a triad *is* (root, quality, chord-tone
identities, resulting pitch classes), with **no guitar voicing, string, fret,
or fingering data**. Fretboard logic is deliberately excluded for now.

```python
from guitar_app.core.theory.triad import Triad, TriadQuality

Triad(PitchClass.C, TriadQuality.MAJOR).tones
# (TriadTone(1, C), TriadTone(3, E), TriadTone(5, G))
```

- `TriadQuality` — the four qualities, each with its chord-tone formula
  (`1 3 5`, `1 b3 5`, `1 b3 b5`, `1 3 #5`). Formulas reuse `ScaleFormula` so
  chord tones keep their `ScaleDegree` identities (diminished `b5` vs
  augmented `#5` stay distinct spellings). The formula lives in the immutable
  enum value and is exposed via read-only properties; quality/formula data
  cannot be mutated.
- `TriadTone(degree, pitch_class)` — a chord-tone identity bound to the pitch
  class it resolves to.
- `Triad(root, quality)` — derives ordered `tones` from the quality formula as
  `(root + degree chromatic offset) mod 12`, and exposes ordered
  `pitch_classes` and `degrees`. Root transposition is just constructing the
  same quality on another root.
- Examples: C major `1 C / 3 E / 5 G`, A minor `1 A / b3 C / 5 E`, B
  diminished `1 B / b3 D / b5 F`, C augmented `1 C / 3 E / #5 G#`. Enharmonic
  spelling stays normalized through `PitchClass`; degree identity preserves
  theoretical intent.
- Inversion is *not* part of the pure `Triad` type (which holds no octave or
  register data); it is modeled in the fretboard layer via `TriadInversion` and
  `TriadVoicing`, where a concrete bass pitch exists (see the voicing section
  below).

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

## Named tuning presets

`NamedTuning` is a built-in catalog entry wrapping a `Tuning` with a stable
programmatic ID and a user-facing name:

```python
NamedTuning(
    id: str,        # stable snake_case identifier, e.g. "drop_d"
    name: str,      # user-facing preset label, e.g. "Drop D"
    tuning: Tuning, # immutable; six strings stored low to high (6..1)
)
```

**Naming rule.** `NamedTuning.name` is the user-facing preset label the UI
shows. `Tuning.name` is the intrinsic/domain/debug label of the tuning value
itself and is not user-facing. The two may coincide (e.g. DADGAD) but serve
different roles; neither is removed. For example `STANDARD.name` stays
`"Standard (EADGBE)"` while the catalog's user-facing label is `"Standard"`.

The catalog lives in `core.instrument.tuning_presets` and mirrors the scale
formula catalog pattern: tuning mechanics (`Tuning`, `GuitarString`) know
nothing about preset IDs or names.

- `available_tunings()` — the catalog entries in stable enumeration order.
- `tuning_by_id(tuning_id)` — the entry with that ID, raising
  `UnknownTuningError` for unknown IDs.
- Each preset also has a module-level constant (`STANDARD_TUNING`, `DROP_D_TUNING`,
  `D_STANDARD_TUNING`, `EB_STANDARD_TUNING`, `DADGAD_TUNING`, `OPEN_D_TUNING`,
  `OPEN_E_TUNING`, `OPEN_G_TUNING`).

Preset IDs are intended to become **stable persistence/API identifiers**, so
they must not be renamed casually; the catalog order is likewise deterministic.

Built-in presets (open strings, low to high):

- Standard — `E2 A2 D3 G3 B3 E4` (reuses the canonical `STANDARD` instance)
- Drop D — `D2 A2 D3 G3 B3 E4`
- D Standard — `D2 G2 C3 F3 A3 D4`
- Eb Standard — `Eb2 Ab2 Db3 Gb3 Bb3 Eb4` (normalized to `D#/G#/C#/F#/A#`
  pitch classes, octave/register preserved)
- DADGAD — `D2 A2 D3 G3 A3 D4`
- Open D — `D2 A2 D3 F#3 A3 D4`
- Open E — `E2 B2 E3 G#3 B3 E4`
- Open G — `D2 G2 D3 G3 B3 D4`

All presets are six-string with string numbers `6..1` in stored (low-to-high)
order; `string 6` is always the lowest conventional guitar string.

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
- The mapping is exposed to the UI through `evaluate_intervals` (service),
  `IntervalLayer`, and the render-annotation projection
  (`ui.render_annotations`); it remains a pure fretboard domain function.

## TriadFretboardPosition, map_triad_to_fretboard

Triad-to-fretboard mapping is the chord-tone equivalent of the scale mapping,
again at the integration boundary between the theory domain and the fretboard
domain. It maps **individual triad tones** only: given a `Fretboard` and a
`Triad`, it returns every position whose pitch class belongs to the triad,
preserving chord-tone degree identity. It does **not** claim any three-note
combination is a playable voicing.

```python
from guitar_app.core.fretboard.triad_mapping import map_triad_to_fretboard
from guitar_app.core.theory.triad import Triad, TriadQuality

map_triad_to_fretboard(board, Triad(PitchClass.C, TriadQuality.MAJOR))
```

- `TriadFretboardPosition` preserves the string/fret location, the sounding
  `Pitch`, the chord-tone `ScaleDegree` (`1`, `b3`, `3`, `b5`, `5`, `#5`), and
  the root-relative `ChromaticInterval`, plus a `pitch_class` convenience
  property. It contains **no rendering or fingering data**.
- Matching emits **one result per matching `TriadTone`**, in triad formula
  order, so degree identities are never collapsed into a single pitch class
  (the four built-in qualities each resolve to distinct pitch classes, but the
  loop preserves formula order in general).
- `Triad` remains guitar-agnostic: mapping lives in `core.fretboard`, which
  imports the theory triad but never vice versa.
- Ordering is deterministic: fretboard iteration order (stored string order,
  lowest fret first), then formula/tone order for multiple matches at one
  position. `triad.tones` is cached before the position loop.
- This mapping only answers "which positions belong to the triad"; three-note
  voicing detection, inversions, string-set grouping, and span constraints are
  the job of `find_triad_voicings` below.

## TriadInversion, TriadVoicing, find_triad_voicings

The first guitar-specific voicing model: adjacent-string triad voicings. The
pipeline is:

```text
Triad
  ↓
map_triad_to_fretboard
  ↓
find_triad_voicings
```

`Triad` stays guitar-agnostic; tone mapping and voicing detection are separate
functions, and voicing detection never re-derives membership.

### TriadInversion

A pure-theory enum naming the three positions of a three-note voicing:
`ROOT_POSITION`, `FIRST_INVERSION`, `SECOND_INVERSION`. Classification uses the
preserved `ScaleDegree` of the lowest sounding chord tone, never raw pitch
classes and never physical string number:

- lowest degree `1` → root position
- lowest degree `3`/`b3` → first inversion
- lowest degree `5`/`b5`/`#5` → second inversion

`TriadInversion.from_lowest_degree(degree)` implements this and rejects
non-triad degrees. Because a custom tuning can make a nominally lower string
sound high, the bass is always `min(tone.pitch)` over the completed voicing.

### TriadVoicing

An immutable guitar-domain result: a string set, its three tones in
string-set order, and the classified inversion.

```python
TriadVoicing(
    string_set: tuple[int, int, int],      # ascending, e.g. (3, 4, 5)
    tones: tuple[TriadFretboardPosition, ...],  # one per string, string-set order
    inversion: TriadInversion,
)
```

Invariants enforced at construction: exactly three tones; exactly one position
per string in the declared string set; all three triad degree identities occur
exactly once. Tones belong to the same `Triad` by construction (from one
`map_triad_to_fretboard` call). Derived properties: `fret_span` (highest minus
lowest fret, open = 0) and `lowest_pitch` (the bass). No fingering or
finger-number data is stored.

### First-pass playability rule

A voicing counts as playable when all of these hold:

1. it uses exactly one note on each of three adjacent strings (all adjacent
   sets are derived from the instrument's string count; fewer than three
   strings yields no voicings, not an error);
2. all three triad tones are present exactly once;
3. the fret span between the highest and lowest fretted positions is at most
   `max_fret_span` (default `DEFAULT_MAX_FRET_SPAN = 4`); open strings count
   as fret 0.

This is deliberately a coarse geometric constraint, **not a complete
ergonomic model**: finger stretches, barre technique, hand size, and physical
impossibility beyond the span rule are not modeled, and no CAGED or
fingering classification is made. Negative span limits are rejected.

### Ordering

Results are deterministic: string sets in ascending tuple order, then lowest
fret ascending, then the fret tuple in string-set order, with the inversion
only as a final stable tie-breaker (unreachable in practice because the fret
tuple uniquely identifies a combination).

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

`TriadLayer` (`id="triad"`, `name="Triads"`) is the third layer. It is
stateless: the fretboard, triad, and optional `max_fret_span` are supplied at
evaluation time. It returns a `TriadLayerResult` — layer metadata plus both
`annotations` (`TriadFretboardPosition` per chord tone) and `voicings`
(`TriadVoicing` per detected adjacent-string voicing), delegating to
`map_triad_to_fretboard` and `find_triad_voicings`. The result is frozen and
contains no rendering fields. It intentionally does **not** satisfy the generic
`Layer` protocol because its payload is two heterogeneous tuples; see
`docs/architecture.md`.

## Planned concepts

The same style of typed value object will be used for:

- `ChordQuality` / `Chord`
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
- `UnknownTuningError` — a named tuning preset ID is not in the catalog.
- `InvalidVoicingError` — malformed triad voicings.

These are domain errors raised by the core engines; the application layer is
responsible for turning them into user-facing messages.
