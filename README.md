# Guitar Assist

A modular desktop guitar-theory toolkit that treats the fretboard as the primary
workspace. Musical concepts are independent, toggleable **layers** projected
onto the fretboard so a guitarist can see how notes, intervals, scales, chords,
and progressions relate to one another everywhere on the neck.

## Project purpose

Built for an experienced self-taught guitarist: you already know the practical
patterns and shapes, and this software helps make the *relationships* between
them visually and structurally clear — rather than acting as another library of
named shapes to memorize.

The long-term goal is one integrated application (or a family of specialized
tools) built on a shared, strictly separated core: music theory, instrument
modeling, fretboard analysis, and visualization each live in their own layer of
the architecture.

## Current status

**Milestone 1 — mathematical core model + multi-layer GUI vertical slice.** The
domain model for pitch classes, pitches, intervals, guitar strings, tunings,
and a configurable fretboard is implemented and unit tested, along with scales,
triads, scale/triad-to-fretboard mapping, interval-to-fretboard mapping,
adjacent-string triad voicings with inversions, fretboard layers, and an
application service layer. A PySide6 desktop window lets you pick a tuning
preset, a root pitch class, a named scale, and a triad quality, toggle the
Scale, Intervals, and Triads layers, edit a custom tuning from its string
pitches, and see the enabled overlays rendered together across the active
instrument's fretboard — including cycling through detected triad voicings.

Implemented:

- Pitch classes (normalized 0–11 chromatic identity) with enharmonic name parsing
- Pitches (pitch class + octave) with MIDI numbers and semitone transposition
- ChromaticInterval: modulo-12 pitch-class displacement (0–11) for
  root-relative fretboard analysis
- Guitar string model: `pitch at fret = open pitch + fret semitones`
- Tunings with validation (string numbers exactly `1..N`) and a built-in
  catalog of named presets (Standard, Drop D, D Standard, Eb Standard, DADGAD,
  Open D/E/G)
- Configurable fretboard (arbitrary tuning, string count, fret count)
- Instrument state service (`InstrumentState`) carrying the active tuning and
  fret count, with `DEFAULT_INSTRUMENT_STATE` (Standard, 22 frets)
- Pitch lookup, pitch-class search, exact-pitch search, and displacement maps
  relative to a chosen root
- Scales (`Scale`, `ScaleTone`) and a catalog of named formulas (major, minor,
  pentatonics, modes) via the application service `evaluate_scale`
- Triads (`Triad`, `TriadTone`, `TriadQuality`) with major, minor, diminished,
  and augmented qualities via the application service `evaluate_triad`
- Adjacent-string triad voicings (`find_triad_voicings`) with inversion
  classification (root, first, second) and a configurable fret span
- Fretboard layers (`Layer`, `LayerResult`, `ScaleLayer`, `IntervalLayer`,
  `TriadLayer`) and per-layer application services (`evaluate_scale`,
  `evaluate_intervals`, `evaluate_triad`)
- PySide6 desktop window: tuning/root/scale/triad-quality selectors,
  Scale/Intervals/Triads layer checkboxes, Prev/Next voicing controls, a live
  tuning/selection/voicing label, and a fretboard widget that renders the
  enabled layers for the active instrument state (first enabled annotation
  centered, additional ones as secondary badges, active triad voicing as an
  overlay); switching tuning presets re-evaluates every enabled layer against
  the newly derived fretboard while preserving the fret count and selections
- Custom tunings: build any tuning from explicit low→high open-string pitches
  (`tuning_from_low_to_high` in `core.instrument`,
  `instrument_from_string_pitches` in `services.instrument_state`), and a
  compact **Edit Tuning…** editor in the main window that edits the 6th/lowest
  string, previews edits as a pending custom tuning, and applies it as a new
  instrument state with no preset identity (the tuning selector moves to a
  `Custom` item)

Not yet implemented (see `docs/architecture.md` for the roadmap):

- Additional layer types (extended chords, progressions, ...) and voicing
  filtering/ranking
- Chord and progression analysis
- Audio capture and pitch detection
- Circle-of-fifths and other exploratory tools
- Fret-count controls in the UI (custom tunings are supported)

## Development setup

Requirements: Python 3.11+ (developed on 3.13). [uv](https://docs.astral.sh/uv/)
is the recommended toolchain manager, but plain `pip` works too.

```console
# Create a virtual environment and install the package + dev tools
uv sync --extra dev
```

Without uv:

```console
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
```

## How to run

Launch the desktop application (requires a display):

```console
uv run guitar-app             # or: python -m guitar_app.app
```

This opens a window with tuning, root, scale, and triad-quality selectors plus
Scale/Intervals/Triads layer checkboxes. The default view (Standard tuning, A
Minor Pentatonic) is shown on the fretboard; changing a selector or toggling a
layer updates it, and picking a different tuning preset re-evaluates every
enabled layer against the new tuning. The **Edit Tuning…** button opens a
compact custom-tuning editor: change a string's open pitch, preview the result,
and press **Apply Tuning** to switch the workspace to a `Custom` tuning. With
the Triads layer enabled, the Prev/Next buttons step through the detected
voicings of the selected triad.

To inspect the fretboard model from the command line instead:

```console
uv run guitar-app-cli         # or: python -m guitar_app.cli
```

This prints the standard 12-fret pitch-class grid, the chromatic-displacement
map relative to root A, and all locations of a chosen pitch class.

## How to run tests and quality tools

```console
uv run pytest          # run the test suite
uv run ruff format .   # format code
uv run ruff check .    # lint
uv run mypy .          # static type check
```

## High-level architecture

```
src/guitar_app/
    core/            # UI-agnostic engines
        theory/      # PitchClass, Pitch, ChromaticInterval, Scale, ScaleDegree,
                     #   Triad, TriadQuality, TriadTone, TriadInversion
        instrument/  # GuitarString, Tuning, tuning presets, standard preset
        fretboard/   # Fretboard, FretPosition, scale & interval & triad mappings,
                     #   triad voicing detection
        layers/      # Layer contract, LayerResult, ScaleLayer, IntervalLayer,
                     #   TriadLayer, TriadLayerResult
    services/        # application services orchestrating the core (Qt-free),
                     #   plus InstrumentState (active-instrument config)
    ui/              # PySide6 app: layer controls, render annotations,
                     #   main window, tuning editor, fretboard widget
    cli.py           # development-only CLI harness
    app.py           # desktop application entry point
```

Design rules:

- **The core never imports PySide6 or any rendering code.**
- **The fretboard engine returns structured domain data** (string, fret, pitch,
  pitch class, interval) — never drawing instructions.
- **Services orchestrate the core for the UI** and never import PySide6.
- **Rendering decisions belong exclusively to the UI layer.**
- Audio processing will be a separate subsystem, decoupled from both the core
  and the UI.

See `docs/architecture.md`, `docs/domain-model.md`, and the ADRs in
`docs/adr/` for details.

## Known limitations

- Context-aware note spelling (e.g. `Eb` in a flat key, or `F` vs `E#` where it
  carries harmonic meaning) is a future theory/domain feature; display is
  currently normalized to sharps.
- No theoretical interval type yet: `ChromaticInterval` encodes distance only
  (six semitones could be `#4` or `b5`).
- No capo support yet (planned).
- The GUI slice ships with built-in tuning presets (Standard through Drop D /
  open tunings) and a compact custom-tuning editor for the lowest string, but
  no fret-count control yet; the default window shows a 22-fret Standard
  board.
- Triad voicings are limited to adjacent-string sets within the default fret
  span; voicing filtering/ranking is future work.
- No extended chords, progressions, or audio yet.

## License

Not yet decided.
