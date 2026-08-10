# ADR 0003: Strongly typed domain model

- Status: Accepted
- Date: 2026-08-10

## Context

Music is full of strings like `"C#"`, `"maj7"`, and `"dorian"`. Passing such
strings through the API invites typos, ambiguous meaning, and impossible states
(e.g. a scale degree of 9 in a 7-note scale). The application must also remain
correct when the same pitch class is spelled enharmonically.

## Decision

Model musical concepts with enums and immutable value objects rather than raw
strings:

- `PitchClass` — an `IntEnum` normalized to 0–11; all calculations use this
  representation. Enharmonic input (`C#` / `Db`) is parsed to the same member.
- `Pitch` — an immutable `PitchClass` + octave value object with MIDI
  transposition.
- `Interval` — an `IntEnum` whose value is the semitone size.
- `GuitarString`, `Tuning`, `FretPosition`, `FretboardPosition`, `Fretboard` —
  immutable value objects with validation in `__post_init__`.

Public APIs are fully type-hinted. Invalid musical states are hard to express:
invalid note names raise `InvalidPitchError`, malformed tunings raise
`InvalidTuningError`, out-of-range positions raise `InvalidPositionError`.

## Consequences

- mypy can statically catch misuse that strings would hide.
- Future scale/chord/progression concepts follow the same pattern.
- Context-aware spelling remains possible: display spelling is layered on top of
  the same normalized pitch-class value, so a future `Eb`-spelling mode is a
  rendering concern, not a data-model change.
