# Architecture

## Overview

Guitar Assist is organized as a small number of strictly separated subsystems.
The direction of dependency is:

```
UI / application      (PySide6)
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
- `Triad`, `TriadQuality`, `TriadTone`, `TriadInversion` — the chord-tone
  model (root + quality formula → ordered chord tones). Purely theoretical:
  no register, string, or tuning data (see `core.fretboard` for the guitar-side
  voicing model).
- `Mode` — the seven modes of the major scale, bound to the existing named
  scale-formula catalog, plus the parallel/relative relationship helpers
  (`parallel_mode`, `relative_mode`, `parent_major_root_for`) and per-mode
  `altered_degrees_from_ionian` metadata. Purely theoretical: no fretboard,
  instrument, or UI concepts (see `services.mode_service` for the
  application-facing wrapper).
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
- `NamedTuning` + `tuning_presets` — the built-in catalog of named tunings
  (`available_tunings`, `tuning_by_id`) wrapping immutable `Tuning` objects with
  stable snake_case IDs. `NamedTuning.name` is the user-facing preset label;
  `Tuning.name` is the intrinsic/domain/debug label. Preset IDs are intended to
  become stable persistence/API identifiers.
- `tuning_from_low_to_high(name, pitches)` — builds a `Tuning` from explicit
  low→high open-string pitches; string numbers `N..1` are derived from the
  supplied order (matching conventional guitar numbering, string 1 highest)
  and validated by `Tuning`.

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
- `ScaleLayer` (`id="scale"`, `name="Scale"`) — projects a scale onto a
  fretboard; it delegates to `map_scale_to_fretboard`.
- `IntervalLayer` (`id="interval"`, `name="Intervals"`) — annotates every
  fretboard position with its root-relative chromatic interval; it delegates to
  `map_intervals_to_fretboard`.
- `TriadLayer` (`id="triad"`, `name="Triads"`) — exposes a concrete triad:
  every triad-tone position plus the detected adjacent-string voicings; it
  delegates to `map_triad_to_fretboard` and `find_triad_voicings`. It returns a
  richer `TriadLayerResult` (annotations **and** voicings) and therefore does
  **not** satisfy the `Layer` protocol; the generic abstraction is left
  unchanged (see "How fretboard layers work").

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
- `evaluate_intervals(fretboard, root)` — evaluates the `IntervalLayer` for the
  given root and returns the ready-to-render
  `LayerResult[IntervalFretboardPosition]`.
- `evaluate_triad(fretboard, root, quality, *, max_fret_span=...)` — builds
  `Triad(root, quality)` and evaluates the `TriadLayer`, returning the richer
  `TriadLayerResult` (every chord-tone position plus detected adjacent-string
  voicings). `max_fret_span` limits the voicings' fret span.
- `available_triad_qualities()` — the `TriadQuality` members in stable order
  (Major, Minor, Diminished, Augmented), for populating a quality selector.

Each concrete layer gets a dedicated service that matches its own evaluation
inputs (scale layer takes `root` + `scale_id`, interval layer takes `root`,
triad layer takes `root` + `quality`);
no generic multi-layer dispatcher exists yet, so UI composition decides which
service to call.

### services.instrument_state — active-instrument configuration

`InstrumentState` is the immutable application-level state for the active
fretboard — the source of the active `Fretboard` consumed by the main window,
and the future source for persistence and AI/API access. It bridges the tuning
preset catalog to the fretboard:

```
tuning preset catalog -> InstrumentState -> Fretboard -> services/layers
```

- `InstrumentState(tuning, fret_count, tuning_id=None, display_name=None)` —
  frozen; holds the active `Tuning`, the fret count, and optionally the preset
  identity (`tuning_id`) and a user-facing `display_name`. `fret_count` follows
  `Fretboard` semantics (>= 0, raising `InvalidPositionError`); no six-string
  requirement.
- `state.fretboard` — derives a fresh `Fretboard(state.tuning, state.fret_count)`
  on each access; nothing is cached so the state stays immutable.
- `instrument_from_tuning_id(tuning_id, *, fret_count=22)` — resolves the ID via
  `tuning_by_id` and preserves the preset ID and display name. Unknown IDs
  propagate `UnknownTuningError`.
- `instrument_from_string_pitches(pitches, *, fret_count=22, display_name="Custom")` —
  builds a custom `InstrumentState` from explicit low→high open-string pitches
  via `tuning_from_low_to_high`. The result carries no preset identity
  (`tuning_id=None`) and the caller-supplied display name (default `"Custom"`).
  Preset identity describes origin/selection, never inferred pitch equality, so
  a custom state is never silently identified as a built-in preset.
- `DEFAULT_INSTRUMENT_STATE` — the canonical application default: Standard
  tuning, 22 frets.
- Custom tunings are first-class: `InstrumentState(tuning=some_custom_tuning,
  fret_count=24)` needs no catalog registration, so `tuning_id`/`display_name`
  are optional.

`InstrumentState` is **not yet persistent** and **not UI state**. Existing
musical services keep accepting a `Fretboard` and never depend on it.

### services.mode_service — modal exploration

Resolves the musical modal context for the future Mode Explorer. It wraps the
pure-theory `core.theory.mode` relationships (`Mode`, `parallel_mode`,
`relative_mode`, `parent_major_root_for`) in a small immutable result and
deliberately resolves **no fretboard data** — the UI will drive the existing
musical services from `ModeSelection.modal_root` and the mode's stable scale
ID.

- `ModeView` — the application-facing view distinction, kept out of Qt.
  `PARALLEL` (label `"Parallel"`) and `RELATIVE` (label `"Relative"`), in that
  stable order via `available_mode_views()`.
- `ModeSelection` — frozen; `view`, `mode`, `input_root`, `modal_root`,
  `parent_major_root`, `scale`, and `altered_degrees_from_ionian` (passed
  through unchanged from the theory model).
- `evaluate_mode(root, mode, view)` — resolves one view of one mode from one
  input root. Root semantics are explicit and intentionally differ:

  ```
  Parallel: root selector = modal root     (e.g. A Dorian -> modal A, parent G)
  Relative: root selector = parent-major root (e.g. C Dorian -> modal D, parent C)
  ```

  The parallel view derives the parent-major root via `parent_major_root_for`;
  the relative view derives the modal root via `relative_mode`.
- `available_modes()` — the seven modes in canonical order, delegating to the
  theory catalog.

Services depend on `core`; **`core` never imports `services`**.

**Standing objective — AI/agent access.** User-facing musical operations are
exposed through UI-independent application services so the desktop UI and
future AI/agent adapters share the same deterministic core behavior. The
intended dependency direction is:

```
Desktop UI ─┐
            ├─> application services ─> core
AI adapter ─┘
```

No API/MCP server, networking, JSON schemas, or AI functionality is implemented
yet; this note only documents the contract that new user-facing operations
should be added as services rather than UI-only code.

### ui — PySide6 desktop application

The only Qt-aware subsystem. It owns all rendering, consumes structured domain
data and service results, and performs no theory calculations.

- `guitar_app.app` — the desktop entry point (`guitar-app` console script).
- `ui.layer_controls` — the UI model of which overlays are visible.
  `LayerControl(id, name, default_enabled)` plus `LAYER_CONTROLS`, the
  available overlays in deterministic order (`scale` enabled, `interval` and
  `triad` disabled). IDs match the corresponding core layer IDs. Deliberately
  free of PySide6 and carries no widgets, callbacks, services, or layer
  objects; the MainWindow derives its checkboxes from these definitions.
- `ui.main_window.MainWindow` — the main window: tuning, root, scale, and
  triad-quality selectors, one checkbox per `LAYER_CONTROLS` entry,
  Previous/Next voicing controls, a live tuning label (using the preset's
  display name) plus a current-selection label and a voicing label, an
  **Edit Tuning…** toggle for the compact custom-tuning editor, and the
  fretboard widget. It owns the active `services.instrument_state`
  `InstrumentState`; changing the tuning selector rebuilds it via
  `instrument_from_tuning_id` while preserving the fret count and all other
  selections. The tuning selector lists the built-in presets plus a
  non-catalog `Custom` item (selecting it without an applied custom tuning
  snaps back to the active preset); applying the string editor builds a custom
  state via `instrument_from_string_pitches` and moves the selector to
  `Custom`. On any selection/toggle change it derives the active fretboard
  from that state, evaluates **only the enabled** layers (an explicit branch
  per known UI layer — no generic dispatcher), projects each result into
  render annotations, combines them in control order, and hands the immutable
  collection plus the currently active voicing group to the widget; disabling
  every layer is a supported empty state, and service/domain errors are
  translated into a status-bar message. The active voicing index resets to the
  first voicing only when the triad result changes (root, quality, or
  fretboard/tuning), and wraps modulo the group count when cycling; toggling
  unrelated layers preserves it. The window is arranged as a two-column
  workspace: a fixed-width (340px) scrollable control column on the left holds
  the section panels, the fretboard dominates the right column beneath a
  workspace header (title = active scale/modal scale; context = parent-major
  root · tuning · frets), and a color legend bar spans the bottom. The
  triad-quality selector is disabled while the Triads layer is off, matching
  the Prev/Next voicing controls.
- `ui.panels` — presentation-only layout panels for the control column.
  `InstrumentPanel`, `MusicalContextPanel`, `LayerPanel`, and `TriadPanel`
  each build one section's widgets (selectors, checkboxes, readouts, voicing
  controls) and expose them as attributes; `LegendWidget` renders the marker
  color legend from the shared palette; `WorkspaceHeader` is the two-line
  title/context bar above the fretboard. Panels own no state and wire no
  signals — `MainWindow` aliases every widget as its own attribute and keeps
  all state and connections, so tests address `window.tuning_selector` etc.
  exactly as before.
- `ui.palette` — the shared Qt color constants used by both the fretboard
  widget's painting and the legend, so the legend can never drift from the
  board.
- `ui.tuning_editor.CustomTuningEditor` — a compact Qt widget for entering a
  custom tuning from its low→high open-string pitches: one row per string
  (conventional number + pitch-class selector + octave selector, never raw
  MIDI numbers), a live preview, and an Apply button. Editing is pending by
  design: the editor emits `edited` (surfaced as a status-bar message) and
  `apply_requested`, but performs no theory and never builds an
  `InstrumentState` — the owning window reads `read_pitches()` and applies the
  result. `set_pitches` re-syncs rows without emitting `edited`, so programmatic
  syncing never marks a pending change.
- `ui.render_annotations` — the UI projection boundary.
  `FretboardRenderAnnotation` (`position`, `label`, `role`) plus
  `render_scale_result`, `render_interval_result`, and `render_triad_result`
  that convert each concrete layer result into render annotations; and
  `TriadVoicingRenderGroup` (`positions`, `string_set`, `inversion`) plus
  `render_triad_voicings` that project detected voicings into UI-only grouping
  data. It is deliberately free of PySide6 so the projection rules are
  unit-testable without a display; it carries presentation roles but never
  colors, pixel coordinates, fonts, or painter objects.
- `ui.fretboard_widget.FretboardWidget` — a `QWidget` + `QPainter` canvas that
  paints a `tuple[FretboardRenderAnnotation, ...]` on a fretboard and
  optionally highlights one `TriadVoicingRenderGroup`; it knows nothing about
  scale-, interval-, or triad-domain annotation types. It draws strings, frets
  (with a distinct nut), fret-count-aware inlaid fret markers (single dots at
  3/5/7/9 and every twelve-fret span thereafter — 15/17/19/21 on the default
  22-fret board — plus double dots at 12 and each multiple of 12), and markers
  for the annotations; open-string (fret 0) markers are hollow rings to keep
  fret 0 unambiguous. When multiple annotations share a position, the first in
  layer order (scale, then interval, then triad) is the centered primary
  marker and every additional one is a smaller offset badge arranged around
  it, so no annotation is discarded. The active voicing group is drawn as a
  subtle translucent triangle linking its three positions (before the point
  labels, so they stay readable) with a compact inversion label (R/1st/2nd).
- `ui.geometry` — UI-only layout math mapping domain `(string_number, fret)`
  pairs to widget coordinates. It is deliberately free of PySide6 so the
  coordinate mapping is unit-testable without a display; pixel coordinates are
  never stored in core/domain objects. The fretboard is laid out like a real
  neck: string 1 (high E) at the top (tab reading order), fret lines placed by
  the 12-tone equal-temperament formula (the 12th fret is exactly half the
  scale length), an open-string gutter left of the nut, and a neck that tapers
  wider toward the body. Proportions are fixed, so the fretboard is letterboxed
  (scaled and centered) inside the widget rather than stretched to fill it.

The UI may import `core` domain types and `services`; **`core` and `services`
never import `ui` or PySide6**.

### cli (temporary)

A development-only command-line harness that prints the fretboard and its
interval map. It remains available as a secondary entry point
(`guitar-app-cli`) for verifying the engine without a GUI; the desktop
application is the primary entry point (`guitar-app`).

### Planned subsystems

- **core.layers** — the fretboard layer contract (`Layer`, `LayerResult`,
  `FretboardAnnotation`) and concrete layers. `ScaleLayer`, `IntervalLayer`,
  and `TriadLayer` are implemented; progression and audio layers will be added
  incrementally. Layers never touch UI components.
- **core.progression** — progressions and voice-leading analysis (later).
- **core.audio** — pitch/onset detection, tuning, and note tracking (later).
  Must remain independent of the theory engine and the UI; DSP code may use
  NumPy or native libraries only once profiling justifies it.
- **ui** — the PySide6 desktop application. The main window, tuning/root/scale
  selectors, layer checkboxes derived from `ui.layer_controls`, the compact
  custom-tuning editor (`ui.tuning_editor`), the UI render-annotation
  projection, and the fretboard widget are implemented;
  triad voicings are rendered as an active-shape overlay and audio
  visualization will be added incrementally.
- **services** — application-level services that orchestrate the core engines
  on behalf of the UI. `evaluate_scale`, `available_scale_formulas`,
  `evaluate_intervals`, `evaluate_triad`, `available_triad_qualities`,
  `instrument_from_tuning_id`, `instrument_from_string_pitches`,
  `InstrumentState`, and the modal-exploration service (`ModeView`,
  `ModeSelection`, `evaluate_mode`) are implemented; more operations
  (progressions) will be added.

## Domain boundaries

| Concept                | Lives in             | Knows about             |
| ---------------------- | -------------------- | ----------------------- |
| Pitch, PitchClass      | core.theory          | nothing guitar-specific |
| ChromaticInterval      | core.theory          | nothing guitar-specific |
| GuitarString, Tuning   | core.instrument      | core.theory             |
| NamedTuning, presets   | core.instrument      | core.theory             |
| Fretboard, positions   | core.fretboard       | core.theory, core.instrument |
| Scale↔fretboard mapping| core.fretboard       | core.theory, core.instrument |
| Interval↔fretboard map.| core.fretboard       | core.theory, core.instrument |
| Layers                 | core.layers          | theory, instrument, fretboard |
| Services               | services             | core engines (any)       |
| InstrumentState        | services             | core.instrument, core.fretboard |
| Mode, mode service     | core.theory, services | core.theory only        |
| Layer controls         | ui.layer_controls     | nothing (UI model)       |
| Render annotations     | ui.render_annotations | core.layers, core.fretboard |
| Rendering geometry     | ui.geometry          | core.fretboard (coords)  |
| Marker palette         | ui.palette           | nothing (Qt colors)      |
| Control panels/header  | ui.panels            | ui.palette, ui.tuning_editor |
| Fretboard widget       | ui                   | core.fretboard, ui.render_annotations |
| Progression (planned)  | core.progression     | theory, fretboard       |
| Audio (planned)        | core.audio           | core.theory (for pitch names) |
| UI                     | ui                   | everything above, via services |

Hard rules:

- `core.*` never imports `guitar_app.ui` or any GUI library.
- `core.*` never imports `guitar_app.services`; dependency flows one way,
  UI → services → core.
- `guitar_app.services` never imports PySide6 or `guitar_app.ui`; the UI is the
  only Qt-aware subsystem.
- `ui.geometry` is the only place that maps domain coordinates to widget
  coordinates; pixel coordinates are never stored in core objects.
- `ui.render_annotations` is the only place that converts layer results into
  render annotations; core layer results never contain render annotations.
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
  delegates to `map_scale_to_fretboard`. Second: `IntervalLayer`
  (`id="interval"`, `name="Intervals"`), which delegates to
  `map_intervals_to_fretboard` and annotates every fretboard position with its
  root-relative chromatic interval.
- `TriadLayer` (`id="triad"`, `name="Triads"`) deliberately returns a richer
  result: `TriadLayerResult` carries both `annotations`
  (`map_triad_to_fretboard` output) and `voicings`
  (`find_triad_voicings` output). Because the payload is two heterogeneous
  tuples, `TriadLayerResult` is **not** a `LayerResult[T]` and `TriadLayer`
  does **not** satisfy the `Layer` protocol. This is an intentional,
  documented divergence: the UI needs both datasets from one evaluation, and
  the generic `Layer` abstraction is left unchanged until a redesign is
  agreed on. UI code can branch on `layer_id == "triad"` to consume the
  richer result.

Example: the *IntervalLayer* evaluated with root A returns, for every position,
the chromatic displacement from A. The *TriadLayer* for Am returns which
positions belong to the Am triad plus its detected adjacent-string voicings.
The UI projects each enabled layer result into render annotations
(`ui.render_annotations`) and the widget paints them on one fretboard, so all
enabled layers display at once — the first enabled layer's annotation at a
position is centered, any additional annotations become small badges around it,
and the active triad voicing is drawn as an overlay; re-rooting updates all
layers automatically.

## Major architectural decisions

Recorded as lightweight ADRs in `docs/adr/`:

1. **Python + PySide6** — Python as the implementation language; PySide6/Qt as
   the desktop UI framework. (`0001-python-and-pyside6.md`)
2. **Theory separated from UI** — the core engines never depend on PySide6 and
   never produce rendering instructions. (`0002-separate-theory-from-ui.md`)
3. **Strongly typed domain model** — musical concepts are value objects/enums,
   not raw strings. (`0003-value-object-domain-model.md`)
