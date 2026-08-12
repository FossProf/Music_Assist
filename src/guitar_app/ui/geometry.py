"""UI-only mapping from fretboard domain coordinates to widget geometry.

Deliberately free of PySide6 so the layout math can be unit tested without a
QApplication or a display. It maps domain (string number, fret) pairs to
pixel-style coordinates inside a widget drawing area; the core/domain objects
themselves never store coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.fretboard.fretboard import Fretboard

#: Fret offsets within each twelve-fret span that receive a single inlaid dot.
_SINGLE_MARKER_OFFSETS: tuple[int, ...] = (3, 5, 7, 9)

#: Fraction of the smallest cell dimension used for a note marker's radius.
_MARKER_SCALE = 0.34


def fret_markers(fret_count: int) -> tuple[int, ...]:
    """Return the single-marker fret numbers inlaid on a ``fret_count`` fretboard.

    Markers repeat every twelve frets (3/5/7/9, then 15/17/19/21, ...) so the
    neck stays readable past the 12th fret; frets above ``fret_count`` are
    omitted. The double octave markers (12, 24, ...) are reported separately by
    :func:`double_marker_frets`.
    """
    return tuple(fret for fret in range(1, fret_count + 1) if fret % 12 in _SINGLE_MARKER_OFFSETS)


def double_marker_frets(fret_count: int) -> tuple[int, ...]:
    """Return the double-marker fret numbers for a ``fret_count`` fretboard.

    The 12th fret and every subsequent multiple of 12 (24, ...) carry two
    stacked inlaid dots.
    """
    return tuple(range(12, fret_count + 1, 12))


@dataclass(frozen=True, slots=True)
class FretboardGeometry:
    """Layout of a fretboard inside a drawing area.

    The fretboard spans ``fret_count + 1`` uniform cells (fret 0 is the
    open-string area, frets 1..``fret_count`` follow), each ``cell_width``
    wide, and ``string_count`` horizontal rows each ``row_height`` tall.
    Strings are laid out low to high: the highest string number sits at the
    top, matching a player's view of the neck.
    """

    string_count: int
    fret_count: int
    cell_width: float
    row_height: float
    left: float
    top: float

    @property
    def width(self) -> float:
        """Width of the fretboard drawing area."""
        return (self.fret_count + 1) * self.cell_width

    @property
    def height(self) -> float:
        """Height of the fretboard drawing area."""
        return self.string_count * self.row_height

    def x_for_fret(self, fret: int) -> float:
        """Return the center x of the cell for ``fret`` (0..fret_count)."""
        self._validate_fret(fret)
        return self.left + (fret + 0.5) * self.cell_width

    def x_for_fret_line(self, fret: int) -> float:
        """Return the x of the fret line for ``fret`` (0 is the nut)."""
        self._validate_fret(fret)
        return self.left + (fret + 1) * self.cell_width

    def y_for_string(self, string_number: int) -> float:
        """Return the center y of ``string_number`` (1..string_count)."""
        self._validate_string(string_number)
        return self.top + (self.string_count - string_number + 0.5) * self.row_height

    def marker_radius(self) -> float:
        """Radius used for note markers, derived from the cell dimensions."""
        return min(self.cell_width, self.row_height) * _MARKER_SCALE

    def _validate_fret(self, fret: int) -> None:
        if fret < 0 or fret > self.fret_count:
            raise ValueError(f"fret {fret} out of range for a {self.fret_count}-fret fretboard")

    def _validate_string(self, string_number: int) -> None:
        if string_number < 1 or string_number > self.string_count:
            raise ValueError(
                f"string number {string_number} out of range for {self.string_count} strings"
            )


def fretboard_geometry(
    fretboard: Fretboard,
    width: float,
    height: float,
    *,
    margin: float = 8.0,
) -> FretboardGeometry:
    """Compute geometry for ``fretboard`` that fits inside ``width`` x ``height``.

    Cells are uniform and ``margin`` is kept even on all sides. The open-string
    cell is the same width as every fretted cell, so the nut sits exactly one
    cell from the left edge.
    """
    available_width = max(width - 2 * margin, 1.0)
    available_height = max(height - 2 * margin, 1.0)
    return FretboardGeometry(
        string_count=fretboard.tuning.string_count,
        fret_count=fretboard.fret_count,
        cell_width=available_width / (fretboard.fret_count + 1),
        row_height=available_height / fretboard.tuning.string_count,
        left=margin,
        top=margin,
    )
