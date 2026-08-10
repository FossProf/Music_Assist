"""Command-line harness for inspecting the fretboard model.

Development-only; the production UI will be a separate PySide6 application.
Run with ``python -m guitar_app.cli`` or the ``guitar-app`` console script.
"""

from __future__ import annotations

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.instrument.tuning import STANDARD
from guitar_app.core.theory.pitch import PitchClass

_CELL_WIDTH = 3


def _print_header(fret_count: int) -> None:
    frets = "".join(f"{fret:>{_CELL_WIDTH}}" for fret in range(fret_count + 1))
    print(f"       {frets}")


def _print_pitch_grid(board: Fretboard) -> None:
    print(f"{board.tuning.name} - {board.fret_count} frets - pitch classes")
    _print_header(board.fret_count)
    for string in board.tuning.strings:
        row = "".join(
            f"{board.pitch_class_at(string.number, fret).spelling():>{_CELL_WIDTH}}"
            for fret in range(board.fret_count + 1)
        )
        print(f"{string.number} ({string.open_pitch})  {row}")


def _print_interval_grid(board: Fretboard, root: PitchClass) -> None:
    print(f"Intervals relative to root {root.spelling()}")
    _print_header(board.fret_count)
    for string in board.tuning.strings:
        cells: list[str] = []
        for fret in range(board.fret_count + 1):
            position = board.position_at(string.number, fret, root=root)
            assert position.interval_from_root is not None
            cells.append(f"{position.interval_from_root.abbreviation:>{_CELL_WIDTH}}")
        print(f"{string.number} ({string.open_pitch})  {''.join(cells)}")


def main() -> int:
    """Print the standard 12-fret fretboard and its interval map from A."""
    board = Fretboard(STANDARD, 12)
    _print_pitch_grid(board)
    print()
    _print_interval_grid(board, PitchClass.A)
    print()
    c_locations = board.pitch_class_locations(PitchClass.C)
    shown = ", ".join(f"{p.string_number}.{p.fret}" for p in c_locations)
    print(f"All C's: {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
