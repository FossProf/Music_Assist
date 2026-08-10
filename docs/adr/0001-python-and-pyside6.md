# ADR 0001: Python and PySide6

- Status: Accepted
- Date: 2026-08-10

## Context

Guitar Assist is a desktop application for guitar theory exploration. The
implementation language and GUI framework were not dictated by the initial
brief, only guided: Python "unless a strong technical reason emerges" and
PySide6/Qt as the expected desktop UI framework.

## Decision

- **Python** is the primary implementation language (targeting Python 3.11+,
  developed on 3.13).
- **PySide6 / Qt** is the desktop UI framework.
- NumPy, SciPy, librosa, aubio, and music21 are **not** added yet; each is
  adopted only when it provides clear value over direct implementation.

## Consequences

- Fast iteration and strong typing via `dataclasses`/`enum` plus `mypy`.
- PySide6 gives a capable custom-painting canvas (QGraphicsScene) for the
  fretboard workspace without fighting the toolkit.
- If future audio DSP profiling demands native speed, the DSP layer may use
  NumPy/native libraries in isolation (see ADR 0002) without touching theory or
  UI code.
