# Architecture

## Overview

Guitar Assist is organized as a small number of strictly separated subsystems.
The direction of dependency is:

```
UI / application      (PySide6, planned)
        |
        v
services              (application services, planned)
        |
        v
core engines          (theory, instrument, fretboard)
        |
        v
Python stdlib only
```

The core engines form the heart of the product. They are pure Python, depend
only on the standard library, and know nothing about windows, widgets, colors,
or audio devices.

## Major subsystems

### core.theory — music theory primitives

- `PitchClass` — a normalized chromatic identity (0–11), the canonical internal
  representation for all pitch-class math. It does not by itself choose an
  enharmonic spelling.
- `Pitch` — a pitch class plus a scientific-pitch octave. The `midi` property
  uses the standard convention (`middle C == Pitch(C, 4).midi == 60`) so that
  the standard guitar's low E is `Pitch(E, 2)`.
- `ChromaticInterval` — modulo-12 pitch-class displacement (0..11) used for
  root-relative fretboard analysis. It encodes distance only, not theoretical
  interval identity; member names are conventional labels for readability.
- A theoretical `Interval` type that distinguishes enharmonic spellings
  (diminished fifth vs augmented fourth, compound intervals, ...) is planned
  but intentionally not implemented yet.

No guitar or tuning concepts appear here.

**Enharmonic spelling is a theory concern.** `PitchClass` is normalized for
chromatic calculation, but choosing how a note is spelled (`F` vs `E#`, `Gb`
vs `F#`) can carry harmonic or scale-degree meaning and therefore belongs to
the theory/domain layer. The UI may choose how a spelling is presented
visually, but it must not invent theoretical spelling on its own. A
note-spelling engine is future work.

### core.instrument — instrument modeling

- `GuitarString` — a string identified by its conventional number, modeled as
  an open pitch; `pitch_at(fret)` implements `open pitch + fret semitones`.
- `Tuning` — an immutable, validated collection of strings. The standard EADGBE
  preset is exposed as `STANDARD`.

The model deliberately supports arbitrary tunings, string counts, and (later)
capo offsets. No fretboard geometry lives here.

### core.fretboard — fretboard analysis

- `Fretboard` — a tuning plus a fret count. Provides pitch lookup, pitch-class
  search, exact-pitch search, position iteration, and interval maps relative to
  a chosen root.
- `FretPosition` — a pure location (`string_number`, `fret`).
- `FretboardPosition` — a location enriched with its pitch and optional interval
  from a root.
- `ScaleFretboardPosition` / `map_scale_to_fretboard` — projects a `Scale`
  (theory domain) onto a fretboard: every position belonging to the scale, with
  its `ScaleDegree` and root-relative `ChromaticInterval`. This is the
  integration boundary between theory and fretboard; `Scale` never imports
  guitar/fretboard modules.

This module answers *musical* questions ("which positions sound C? what interval
is this position from the root? which positions belong to this scale?") and
never rendering questions ("which color should this position be?").

### cli (temporary)

A development-only command-line harness that prints the fretboard and its
interval map. It exists to verify the engine without a GUI and will be replaced
by the PySide6 application.

### Planned subsystems

- **core.layers** — a `Layer` abstraction: a layer evaluates a musical context
  and produces structured annotations attached to fretboard positions. Layers
  never touch UI components. The first layers (notes, intervals, scale, chord
  tones) will be added incrementally.
- **core.progression** — progressions and voice-leading analysis (later).
- **core.audio** — pitch/onset detection, tuning, and note tracking (later).
  Must remain independent of the theory engine and the UI; DSP code may use
  NumPy or native libraries only once profiling justifies it.
- **ui** — the PySide6 desktop application, including a custom fretboard
  widget that consumes structured domain data and owns all rendering.
- **services** — application-level services that orchestrate the core engines
  on behalf of the UI.

## Domain boundaries

| Concept                | Lives in             | Knows about             |
| ---------------------- | -------------------- | ----------------------- |
| Pitch, PitchClass      | core.theory          | nothing guitar-specific |
| ChromaticInterval      | core.theory          | nothing guitar-specific |
| GuitarString, Tuning   | core.instrument      | core.theory             |
| Fretboard, positions   | core.fretboard       | core.theory, core.instrument |
| Scale↔fretboard mapping| core.fretboard       | core.theory, core.instrument |
| Layers (planned)       | core.layers          | theory, instrument, fretboard |
| Progression (planned)  | core.progression     | theory, fretboard       |
| Audio (planned)        | core.audio           | core.theory (for pitch names) |
| UI (planned)           | ui                   | everything above, via services |

Hard rules:

- `core.*` never imports `guitar_app.ui` or any GUI library.
- `core.fretboard` returns domain objects; it contains no drawing code.
- Domain errors are raised as domain exceptions (`InvalidPitchError`,
  `InvalidTuningError`, `InvalidPositionError`) and translated into
  user-facing messages only in the application layer.

## How fretboard layers work

The central product concept: **the fretboard is the workspace; musical concepts
are toggleable layers projected onto it.**

Planned shape (not yet implemented):

```
class Layer(Protocol):
    name: str
    def evaluate(self, context: LayerContext) -> LayerResult:
        """Map a musical context to structured annotations per position."""
```

- A `LayerContext` carries whatever the layer needs: a fretboard, a root, a
  scale, a chord, etc.
- A `LayerResult` is a set of structured annotations — for example
  `(position, interval, scale_degree, chord_function, member_of_...?)` — never
  colors or shapes.
- The UI takes a `LayerResult` and decides how to draw it. This keeps every
  layer individually testable without a GUI and lets several layers be combined
  on one fretboard.

Example: an *IntervalLayer* evaluated with root A returns, for every position,
the chromatic displacement from A. A *ChordToneLayer* for Am returns which
positions belong to the Am triad. Both can be displayed at once, and re-rooting
to G updates both automatically because each layer computes from the same
shared context.

## Major architectural decisions

Recorded as lightweight ADRs in `docs/adr/`:

1. **Python + PySide6** — Python as the implementation language; PySide6/Qt as
   the desktop UI framework. (`0001-python-and-pyside6.md`)
2. **Theory separated from UI** — the core engines never depend on PySide6 and
   never produce rendering instructions. (`0002-separate-theory-from-ui.md`)
3. **Strongly typed domain model** — musical concepts are value objects/enums,
   not raw strings. (`0003-value-object-domain-model.md`)
