"""UI-only mapping from fretboard domain coordinates to widget geometry.

Deliberately free of PySide6 so the layout math can be unit tested without a
QApplication or a display. It maps domain (string number, fret) pairs to
pixel-style coordinates inside a widget drawing area; the core/domain objects
themselves never store coordinates.

The fretboard is laid out like a real neck:

- Strings run **string 1 (high E) at the top** down to the lowest string at the
  bottom, matching tab reading order.
- Fret lines follow the 12-tone equal temperament formula, so each fret space
  is ``2 ** (-1/12)`` of the one below it and the 12th fret line sits exactly
  halfway along the scale length.
- A gutter left of the nut holds the open-string (fret 0) markers.
- The neck tapers: it is ``_BODY_GROWTH`` times as tall at the last fret as at
  the nut.
- Proportions (scale length : neck height) are fixed, so the fretboard is
  letterboxed (scaled and centered) inside the widget instead of distorted.
"""

from __future__ import annotations

from dataclasses import dataclass

from guitar_app.core.fretboard.fretboard import Fretboard

#: Fret offsets within each twelve-fret span that receive a single inlaid dot.
_SINGLE_MARKER_OFFSETS: tuple[int, ...] = (3, 5, 7, 9)

#: Fraction of the smallest cell dimension used for a note marker's radius.
_MARKER_SCALE = 0.34

#: Gutter left of the nut, as a fraction of the scale length.
_OPEN_GUTTER_FRACTION = 0.08

#: Neck height at the nut per string, as a fraction of the scale length.
_NUT_HEIGHT_PER_STRING = 0.07

#: Ratio of the neck height at the last fret to the neck height at the nut.
_BODY_GROWTH = 1.15


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

    The drawing box spans ``left``..``left + width`` horizontally and includes
    the open-string gutter plus the fretted neck. ``left`` is the box's left
    edge, ``open_span`` the gutter reserved for open-string markers, and
    ``scale_length`` the horizontal span from the nut to the box's right edge
    (where the strings run toward the body). ``nut_x`` is the x of the nut.
    Vertically, ``top`` is the y of the neck's top edge at the nut;
    ``nut_height`` and ``body_height`` are the neck's height there and at the
    right edge. The neck tapers linearly between them about the constant
    centerline :meth:`mid_y`.

    String 1 (high E) is the topmost string, matching tab reading order.
    """

    string_count: int
    fret_count: int
    left: float
    open_span: float
    scale_length: float
    top: float
    nut_height: float
    body_height: float

    @property
    def nut_x(self) -> float:
        """The x of the nut (the last fret line, fret 0)."""
        return self.left + self.open_span

    @property
    def right(self) -> float:
        """The x of the drawing box's right edge, where the strings end."""
        return self.left + self.open_span + self.scale_length

    @property
    def width(self) -> float:
        """Width of the drawing box (gutter plus fretted span)."""
        return self.open_span + self.scale_length

    @property
    def height(self) -> float:
        """Tallest the fretboard gets (the neck height at the right edge)."""
        return max(self.nut_height, self.body_height)

    def x_for_fret(self, fret: int) -> float:
        """Return the marker x for ``fret`` (0..fret_count).

        Open-string positions sit in the gutter left of the nut; a fretted
        position is centered in the space between its fret line and the
        previous one.
        """
        self._validate_fret(fret)
        if fret == 0:
            return self.left + self.open_span / 2
        previous = self.x_for_fret_line(fret - 1)
        current = self.x_for_fret_line(fret)
        return previous + (current - previous) / 2

    def x_for_fret_line(self, fret: int) -> float:
        """Return the x of the fret line for ``fret`` (0 is the nut)."""
        self._validate_fret(fret)
        if fret == 0:
            return self.nut_x
        return self.nut_x + self.scale_length * (1 - 2 ** (-fret / 12))

    def y_for_string(self, string_number: int, x: float | None = None) -> float:
        """Return the center y of ``string_number`` (1..string_count) at ``x``.

        With no ``x`` the nut cross-section is used. String 1 (high E) is the
        topmost string; strings spread apart toward the body where the neck
        tapers.
        """
        self._validate_string(string_number)
        height = self._neck_height(self.nut_x if x is None else x)
        offset = (string_number - 0.5) / self.string_count
        return self.mid_y() - height / 2 + height * offset

    def mid_y(self) -> float:
        """Return the y of the neck's constant centerline."""
        return self.top + self.nut_height / 2

    def neck_top(self, x: float) -> float:
        """Return the y of the neck's top edge at ``x``."""
        return self.mid_y() - self._neck_height(x) / 2

    def neck_bottom(self, x: float) -> float:
        """Return the y of the neck's bottom edge at ``x``."""
        return self.mid_y() + self._neck_height(x) / 2

    def row_height(self) -> float:
        """Height of one string row at the nut."""
        return self.nut_height / self.string_count

    def marker_radius(self) -> float:
        """Radius used for note markers, derived from the neck proportions."""
        mean_cell = self.scale_length
        if self.fret_count >= 1:
            mean_cell = self.scale_length * (1 - 2 ** (-self.fret_count / 12)) / self.fret_count
        cell = min(self.row_height(), mean_cell, self.open_span * 0.5)
        return cell * _MARKER_SCALE

    def _neck_height(self, x: float) -> float:
        fraction = (x - self.nut_x) / self.scale_length if self.scale_length else 0.0
        fraction = min(max(fraction, 0.0), 1.0)
        return self.nut_height + (self.body_height - self.nut_height) * fraction

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
    """Compute geometry for ``fretboard`` letterboxed inside ``width`` x ``height``.

    The fretboard keeps fixed proportions (a tapered neck whose total width is
    ``1 + _OPEN_GUTTER_FRACTION`` times its tallest height), so it is scaled to
    fit the binding axis and centered, keeping ``margin`` even on every side.
    """
    available_width = max(width - 2 * margin, 1.0)
    available_height = max(height - 2 * margin, 1.0)

    string_count = fretboard.tuning.string_count
    gutter = _OPEN_GUTTER_FRACTION
    nut_height = _NUT_HEIGHT_PER_STRING * string_count
    body_height = nut_height * _BODY_GROWTH
    total_width = 1.0 + gutter
    max_height = max(nut_height, body_height)

    scale = min(available_width / total_width, available_height / max_height)

    return FretboardGeometry(
        string_count=string_count,
        fret_count=fretboard.fret_count,
        left=margin + (available_width - total_width * scale) / 2,
        open_span=gutter * scale,
        scale_length=scale,
        top=margin + (available_height - max_height * scale) / 2,
        nut_height=nut_height * scale,
        body_height=body_height * scale,
    )
