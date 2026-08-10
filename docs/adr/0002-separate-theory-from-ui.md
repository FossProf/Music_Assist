# ADR 0002: Separate theory from UI

- Status: Accepted
- Date: 2026-08-10

## Context

The product's core idea is a fretboard workspace onto which musical concepts are
projected as toggleable layers. If theory calculations and rendering are
interleaved, layers cannot be combined, tested, or reused, and the engine
becomes coupled to a single GUI.

## Decision

Strictly separate: music theory, instrument modeling, fretboard analysis,
visualization/UI, application logic, and audio processing.

- `core.*` engines are pure Python with no dependency on PySide6.
- The fretboard engine returns **structured domain information** (string number,
  fret, pitch, pitch class, interval, scale degree, chord function, layer
  membership) and never rendering instructions (colors, shapes, labels).
- Rendering decisions belong exclusively to the `ui` layer.
- Audio processing is a separate subsystem, decoupled from both core and UI.
- Domain errors are raised in the core; the application layer converts them to
  user-facing messages.

## Consequences

- The theory/fretboard engines are unit-testable without a GUI and remain
  reusable by any future tool built on the same core.
- The UI is a consumer of structured domain data, which keeps it thinner and
  makes visual changes cheap.
- A layer is defined by what it computes, not how it draws, enabling arbitrary
  layer combinations on one fretboard.
