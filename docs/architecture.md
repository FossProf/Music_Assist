# Architecture

## Overview

Guitar Assist is organized as a small number of strictly separated subsystems.
The direction of dependency is:

```
UI / application      (PySide6, planned)
        |
        v
services              (application services)
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

### core.layers — fretboard overlay layers

- `Layer` (Protocol) — the minimal structural contract for an overlay: a stable
  `id`, a human-readable `name`, and an `evaluate` operation returning an
  immutable `LayerResult`.
- `LayerResult[T]` — layer metadata plus a tuple of layer-specific annotations.
  Every annotation identifies its fretboard location via `FretPosition`
  (`FretboardAnnotation`). There are no universal context or rendering fields.
- `ScaleLayer` (`id="scale"`, `name="Scale"`) — the first concrete layer; it
  delegates to `map_scale_to_fretboard`.

Each concrete layer owns the inputs it requires (no universal `LayerContext`).
Layers produce structured annotations only; rendering is always the UI's job.

### services — application services

Typed operations that orchestrate the core engines on behalf of the UI. The UI
does not search the catalog, construct `Scale`, or coordinate layers directly;
it calls a service and receives a ready-to-render `LayerResult`.

- `evaluate_scale(fretboard, root, scale_id)` — resolves the ID via
  `scale_formula_by_id`, builds `Scale(root, formula)`, and returns the
  evaluated `ScaleLayer` result. Unknown IDs propagate
  `UnknownScaleFormulaError` to the caller.
- `available_scale_formulas()` — the catalog's named formulas in stable order,
  for populating a scale selector.

Services depend on `core`; **`core` never imports `services`**.

### cli (temporary)

A development-only command-line harness that prints the fretboard and its
interval map. It exists to verify the engine without a GUI and will be replaced
by the PySide6 application.

### Planned subsystems

- **core.layers** — the fretboard layer contract (`Layer`, `LayerResult`,
  `FretboardAnnotation`) and concrete layers. `ScaleLayer` is implemented;
  interval, chord-tone, and audio layers will be added incrementally. Layers
  never touch UI components.
- **core.progression** — progressions and voice-leading analysis (later).
- **core.audio** — pitch/onset detection, tuning, and note tracking (later).
  Must remain independent of the theory engine and the UI; DSP code may use
  NumPy or native libraries only once profiling justifies it.
- **ui** — the PySide6 desktop application, including a custom fretboard
  widget that consumes structured domain data and owns all rendering.
- **services** — application-level services that orchestrate the core engines
  on behalf of the UI. `evaluate_scale` and `available_scale_formulas` are
  implemented; more operations (chord tones, progressions) will be added.

## Domain boundaries

| Concept                | Lives in             | Knows about             |
| ---------------------- | -------------------- | ----------------------- |
| Pitch, PitchClass      | core.theory          | nothing guitar-specific |
| ChromaticInterval      | core.theory          | nothing guitar-specific |
| GuitarString, Tuning   | core.instrument      | core.theory             |
| Fretboard, positions   | core.fretboard       | core.theory, core.instrument |
| Scale↔fretboard mapping| core.fretboard       | core.theory, core.instrument |
| Layers                 | core.layers          | theory, instrument, fretboard |
| Services               | services             | core engines (any)       |
| Progression (planned)  | core.progression     | theory, fretboard       |
| Audio (planned)        | core.audio           | core.theory (for pitch names) |
| UI (planned)           | ui                   | everything above, via services |

Hard rules:

- `core.*` never imports `guitar_app.ui` or any GUI library.
- `core.*` never imports `guitar_app.services`; dependency flows one way,
  UI → services → core.
- `core.fretboard` returns domain objects; it contains no drawing code.
- Domain errors are raised as domain exceptions (`InvalidPitchError`,
  `InvalidTuningError`, `InvalidPositionError`) and translated into
  user-facing messages only in the application layer.

## How fretboard layers work

The central product concept: **the fretboard is the workspace; musical concepts
are toggleable layers projected onto it.**

Implemented contract (`core.layers`):

```
P = ParamSpec("P")
T = TypeVar("T", bound=FretboardAnnotation)

class Layer(Protocol[P, T]):
    id: str
    name: str
    def evaluate(self, *args: P.args, **kwargs: P.kwargs) -> LayerResult[T]: ...
```

- A layer exposes a stable `id`, a human-readable `name`, and an `evaluate`
  operation that returns an immutable `LayerResult`. Each concrete layer
  declares its own `evaluate` signature and owns the inputs it actually
  requires — there is **no universal `LayerContext`** and no inherited state
  from other layers. The `ParamSpec` `P` keeps those heterogeneous signatures
  statically type-checked instead of collapsing them to `Any`.
- `LayerResult[T]` is layer metadata (`layer_id`, `layer_name`) plus a tuple of
  layer-specific annotations. Every annotation identifies its fretboard
  location via a `FretPosition` (`FretboardAnnotation`).
- Results are structured domain data — never colors, shapes, opacity, fonts, or
  pixel coordinates. The UI consumes a `LayerResult` and owns all rendering.
  This keeps every layer individually testable without a GUI and lets several
  layers be combined on one fretboard.
- First concrete layer: `ScaleLayer` (`id="scale"`, `name="Scale"`), which
  delegates to `map_scale_to_fretboard`.

Example: an *IntervalLayer* evaluated with root A returns, for every position,
the chromatic displacement from A. A *ChordToneLayer* for Am returns which
positions belong to the Am triad. Both can be displayed at once, and re-rooting
to G updates both automatically.

## Major architectural decisions

Recorded as lightweight ADRs in `docs/adr/`:

1. **Python + PySide6** — Python as the implementation language; PySide6/Qt as
   the desktop UI framework. (`0001-python-and-pyside6.md`)
2. **Theory separated from UI** — the core engines never depend on PySide6 and
   never produce rendering instructions. (`0002-separate-theory-from-ui.md`)
3. **Strongly typed domain model** — musical concepts are value objects/enums,
   not raw strings. (`0003-value-object-domain-model.md`)
