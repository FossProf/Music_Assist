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

**Milestone 1 — mathematical core model (in progress).** The domain model for
pitch classes, pitches, intervals, guitar strings, tunings, and a configurable
fretboard is implemented and unit tested. There is no GUI yet; a small
command-line harness verifies the engine.

Implemented:

- Pitch classes (normalized 0–11 chromatic identity) with enharmonic name parsing
- Pitches (pitch class + octave) with MIDI numbers and semitone transposition
- ChromaticInterval: modulo-12 pitch-class displacement (0–11) for
  root-relative fretboard analysis
- Guitar string model: `pitch at fret = open pitch + fret semitones`
- Tunings with validation (string numbers exactly `1..N`), plus the standard
  EADGBE preset
- Configurable fretboard (arbitrary tuning, string count, fret count)
- Pitch lookup, pitch-class search, exact-pitch search, and displacement maps
  relative to a chosen root

Not yet implemented (see `docs/architecture.md` for the roadmap):

- PySide6 UI
- Fretboard layers (notes, intervals, scales, chords, progressions, ...)
- Scales, modes, chords, and progressions
- Audio capture and pitch detection
- Circle-of-fifths and other exploratory tools

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

There is no GUI yet. To inspect the fretboard model from the command line:

```console
uv run guitar-app             # or: python -m guitar_app.cli
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
        theory/      # PitchClass, Pitch, ChromaticInterval (no guitar concepts)
        instrument/  # GuitarString, Tuning, standard preset
        fretboard/   # Fretboard, FretPosition, FretboardPosition
    cli.py           # development harness (temporary stand-in for the UI)
    ui/              # PySide6 application (planned)
```

Design rules:

- **The core never imports PySide6 or any rendering code.**
- **The fretboard engine returns structured domain data** (string, fret, pitch,
  pitch class, interval) — never drawing instructions.
- Rendering decisions belong exclusively to the future UI layer.
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
- No scales, chords, progressions, layers, or audio yet.

## License

Not yet decided.
