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

- `PitchClass` — an `IntEnum` normalized to 0–11, a chromatic identity; all
  calculations use this representation. Enharmonic input (`C#` / `Db`) is
  parsed to the same member.
- `Pitch` — an immutable `PitchClass` + octave value object with MIDI
  transposition.
- `ChromaticInterval` — an `IntEnum` whose value is the modulo-12 pitch-class
  displacement (0..11). It encodes distance only, not enharmonic or theoretical
  spelling (six semitones may be `#4` or `b5`). A theoretical interval type
  that distinguishes such spellings is deferred.
- `GuitarString`, `Tuning`, `FretPosition`, `FretboardPosition`, `Fretboard` —
  immutable value objects with validation in `__post_init__`. A tuning must
  contain exactly the string numbers `1..N`.

Public APIs are fully type-hinted. Invalid musical states are hard to express:
invalid note names raise `InvalidPitchError`, malformed tunings raise
`InvalidTuningError`, out-of-range positions raise `InvalidPositionError`.

## Consequences

- mypy can statically catch misuse that strings would hide.
- Future scale/chord/progression concepts follow the same pattern.
- Context-aware spelling is a **theory/domain concern**, not purely a rendering
  one: spellings such as `F` vs `E#` or `Gb` vs `F#` can carry harmonic or
  scale-degree meaning, so the domain model will own spelling choices and the
  UI will only present them.
- Separating chromatic distance (`ChromaticInterval`) from a future theoretical
  interval type keeps root-relative fretboard analysis simple while leaving
  room for interval-quality modeling (diminished fifth vs augmented fourth,
  compound intervals).
