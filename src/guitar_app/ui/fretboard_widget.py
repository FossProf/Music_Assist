"""Custom fretboard widget that renders evaluated scale layer results."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QWidget

from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.fretboard.scale_mapping import ScaleFretboardPosition
from guitar_app.core.layers.base import LayerResult
from guitar_app.core.theory.scale_degree import ScaleDegree
from guitar_app.ui.geometry import FRET_MARKERS, FretboardGeometry, fretboard_geometry

#: The tonic scale degree, drawn with a distinct palette.
_TONIC = ScaleDegree(1)

_BACKGROUND_COLOR = QColor("#ffffff")
_NUT_COLOR = QColor("#2b2b2b")
_FRET_COLOR = QColor("#c9c9c9")
_STRING_COLOR = QColor("#8a8a8a")
_MARKER_COLOR = QColor("#d9d9d9")
_TONIC_FILL = QColor("#1f6fb2")
_TONIC_TEXT = QColor("#ffffff")
_DEGREE_FILL = QColor("#c5dcf0")
_DEGREE_TEXT = QColor("#1a3550")
_OPEN_PEN = QColor("#1f6fb2")


class FretboardWidget(QWidget):
    """A fretboard canvas that renders evaluated scale annotations.

    The widget receives already-evaluated domain data (a
    :class:`LayerResult[ScaleFretboardPosition]`) plus the :class:`Fretboard`
    used to establish geometry. It owns all painting; the core and services
    remain Qt-free and never produce rendering data.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fretboard: Fretboard | None = None
        self._result: LayerResult[ScaleFretboardPosition] | None = None
        self.setMinimumSize(200, 120)

    @property
    def fretboard(self) -> Fretboard | None:
        """The fretboard currently displayed, or None before data is set."""
        return self._fretboard

    @property
    def result(self) -> LayerResult[ScaleFretboardPosition] | None:
        """The evaluated layer result currently displayed, or None."""
        return self._result

    def set_fretboard_data(
        self,
        fretboard: Fretboard,
        result: LayerResult[ScaleFretboardPosition],
    ) -> None:
        """Display ``result`` on ``fretboard`` and schedule a repaint."""
        self._fretboard = fretboard
        self._result = result
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._fretboard is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), _BACKGROUND_COLOR)
        geometry = fretboard_geometry(self._fretboard, float(self.width()), float(self.height()))
        self._draw_fret_lines(painter, geometry)
        self._draw_strings(painter, geometry)
        self._draw_fret_markers(painter, geometry)
        if self._result is not None:
            self._draw_annotations(painter, geometry, self._result)
        painter.end()

    def _draw_fret_lines(self, painter: QPainter, geometry: FretboardGeometry) -> None:
        painter.save()
        for fret in range(geometry.fret_count + 1):
            x = geometry.x_for_fret_line(fret)
            if fret == 0:
                painter.setPen(QPen(_NUT_COLOR, 4.0))
            else:
                painter.setPen(QPen(_FRET_COLOR, 1.0))
            painter.drawLine(
                QPointF(x, geometry.top),
                QPointF(x, geometry.top + geometry.height),
            )
        painter.restore()

    def _draw_strings(self, painter: QPainter, geometry: FretboardGeometry) -> None:
        painter.save()
        painter.setPen(QPen(_STRING_COLOR, 1.0))
        for string_number in range(1, geometry.string_count + 1):
            y = geometry.y_for_string(string_number)
            painter.drawLine(
                QPointF(geometry.left, y),
                QPointF(geometry.left + geometry.width, y),
            )
        painter.restore()

    def _draw_fret_markers(self, painter: QPainter, geometry: FretboardGeometry) -> None:
        painter.save()
        painter.setBrush(QBrush(_MARKER_COLOR))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        radius = geometry.row_height * 0.18
        mid_y = geometry.top + geometry.height / 2
        for fret in FRET_MARKERS:
            if fret > geometry.fret_count:
                continue
            x = geometry.x_for_fret(fret)
            if fret == 12:
                offset = radius * 1.9
                painter.drawEllipse(QPointF(x, mid_y - offset), radius, radius)
                painter.drawEllipse(QPointF(x, mid_y + offset), radius, radius)
            else:
                painter.drawEllipse(QPointF(x, mid_y), radius, radius)
        painter.restore()

    def _draw_annotations(
        self,
        painter: QPainter,
        geometry: FretboardGeometry,
        result: LayerResult[ScaleFretboardPosition],
    ) -> None:
        painter.save()
        radius = geometry.marker_radius()
        font = painter.font()
        font.setPixelSize(max(7, int(radius * 1.1)))
        painter.setFont(font)
        for annotation in result.annotations:
            center = QPointF(
                geometry.x_for_fret(annotation.position.fret),
                geometry.y_for_string(annotation.position.string_number),
            )
            is_open = annotation.position.fret == 0
            is_tonic = annotation.degree == _TONIC
            if is_open:
                painter.setBrush(QBrush(_BACKGROUND_COLOR))
                painter.setPen(QPen(_OPEN_PEN, 2.0))
            elif is_tonic:
                painter.setBrush(QBrush(_TONIC_FILL))
                painter.setPen(QPen(Qt.PenStyle.NoPen))
            else:
                painter.setBrush(QBrush(_DEGREE_FILL))
                painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            if is_tonic and not is_open:
                painter.setPen(QPen(_TONIC_TEXT))
            else:
                painter.setPen(QPen(_DEGREE_TEXT))
            painter.drawText(
                QRectF(
                    center.x() - radius,
                    center.y() - radius,
                    radius * 2,
                    radius * 2,
                ),
                int(Qt.AlignmentFlag.AlignCenter),
                annotation.degree.label,
            )
        painter.restore()
