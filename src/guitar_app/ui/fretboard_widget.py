"""Custom fretboard widget that renders render annotations.

The widget receives an already-projected, UI-only collection of
:class:`FretboardRenderAnnotation` (plus the :class:`Fretboard` used for
geometry). It knows nothing about scale- or interval-domain annotation types
and owns all painting; the core and services remain Qt-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.theory.triad import TriadInversion
from guitar_app.ui.geometry import FRET_MARKERS, FretboardGeometry, fretboard_geometry
from guitar_app.ui.render_annotations import (
    FretboardRenderAnnotation,
    RenderRole,
    TriadVoicingRenderGroup,
)

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
_INTERVAL_FILL = QColor("#f2e4d0")
_INTERVAL_TEXT = QColor("#5a4632")
_INTERVAL_OUTLINE = QColor("#b9a082")
_INTERVAL_ROOT_FILL = QColor("#b26a1f")
_INTERVAL_ROOT_TEXT = QColor("#ffffff")
_BADGE_FILL = QColor("#ffffff")
_BADGE_TEXT = QColor("#4a3f33")
_BADGE_OUTLINE = QColor("#8a7a6a")
_TRIAD_FILL = QColor("#7db87d")
_TRIAD_TEXT = QColor("#1d3a1d")
_TRIAD_ROOT_FILL = QColor("#2f7d32")
_TRIAD_ROOT_TEXT = QColor("#ffffff")
_VOICING_GROUP_PEN = QColor("#4d8f4d")
_VOICING_GROUP_FILL = QColor(70, 130, 70, 36)

#: Fraction of a primary marker radius used for the secondary badge radius.
_BADGE_SCALE = 0.55

#: Badge offsets around a primary marker: up-right, down-right, up-left, down-left.
_BADGE_OFFSETS: tuple[tuple[float, float], ...] = (
    (1.0, -1.0),
    (1.0, 1.0),
    (-1.0, -1.0),
    (-1.0, 1.0),
)

#: Compact inversion label drawn near an active voicing group.
_VOICING_INVERSION_LABELS = {
    TriadInversion.ROOT_POSITION: "R",
    TriadInversion.FIRST_INVERSION: "1st",
    TriadInversion.SECOND_INVERSION: "2nd",
}

_SCALE_ROLES = (RenderRole.SCALE_ROOT, RenderRole.SCALE_TONE)


@dataclass(frozen=True, slots=True)
class _PositionPlan:
    """How one fretboard location will be painted.

    ``primary`` is the centered marker (the first annotation at the position in
    deterministic layer order); every additional annotation is drawn as a small
    offset badge so shared positions keep all annotations visible.
    """

    position: FretPosition
    primary: FretboardRenderAnnotation
    badges: tuple[FretboardRenderAnnotation, ...]


class FretboardWidget(QWidget):
    """A fretboard canvas that paints UI render annotations.

    The widget receives already-projected render data (an immutable tuple of
    :class:`FretboardRenderAnnotation`) plus the :class:`Fretboard` used to
    establish geometry. It owns all painting; the core and services remain
    Qt-free and never produce rendering data.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fretboard: Fretboard | None = None
        self._annotations: tuple[FretboardRenderAnnotation, ...] = ()
        self._voicing_group: TriadVoicingRenderGroup | None = None
        self.setMinimumSize(200, 120)

    @property
    def fretboard(self) -> Fretboard | None:
        """The fretboard currently displayed, or None before data is set."""
        return self._fretboard

    @property
    def annotations(self) -> tuple[FretboardRenderAnnotation, ...]:
        """The render annotations currently displayed (empty before data is set)."""
        return self._annotations

    @property
    def voicing_group(self) -> TriadVoicingRenderGroup | None:
        """The active voicing group currently highlighted, or None."""
        return self._voicing_group

    def set_annotations(
        self,
        fretboard: Fretboard,
        annotations: tuple[FretboardRenderAnnotation, ...],
    ) -> None:
        """Display ``annotations`` on ``fretboard`` and schedule a repaint."""
        self._fretboard = fretboard
        self._annotations = annotations
        self.update()

    def set_voicing_group(self, group: TriadVoicingRenderGroup | None) -> None:
        """Highlight ``group``'s three positions as one connected unit.

        Only one voicing group is drawn at a time; pass ``None`` to draw no
        grouping. Point annotations remain unaffected.
        """
        self._voicing_group = group
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
        if self._voicing_group is not None:
            self._draw_voicing_group(painter, geometry, self._voicing_group)
        if self._annotations:
            self._draw_annotations(painter, geometry)
        painter.end()

    def _build_plan(self) -> tuple[_PositionPlan, ...]:
        """Group annotations by position into primary/badge paint plans.

        Annotations arrive in deterministic layer order (scale, then interval,
        then triad), so the first annotation at a position becomes the centered
        primary marker and every additional one becomes a smaller offset badge
        — no annotation is discarded, regardless of how many layers share a
        position.
        """
        by_position: dict[FretPosition, list[FretboardRenderAnnotation]] = {}
        for annotation in self._annotations:
            by_position.setdefault(annotation.position, []).append(annotation)

        plans: list[_PositionPlan] = []
        for position, position_annotations in by_position.items():
            primary = position_annotations[0]
            badges = tuple(position_annotations[1:])
            plans.append(_PositionPlan(position, primary, badges))
        return tuple(plans)

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

    def _draw_annotations(self, painter: QPainter, geometry: FretboardGeometry) -> None:
        radius = geometry.marker_radius()
        badge_radius = radius * _BADGE_SCALE
        font = painter.font()
        font.setPixelSize(max(7, int(radius * 1.1)))
        painter.setFont(font)
        plans = self._build_plan()
        for plan in plans:
            self._draw_primary(painter, geometry, plan.primary, radius)
        for plan in plans:
            for badge_index, badge in enumerate(plan.badges):
                self._draw_badge(painter, geometry, badge, badge_radius, radius, badge_index)

    def _draw_primary(
        self,
        painter: QPainter,
        geometry: FretboardGeometry,
        annotation: FretboardRenderAnnotation,
        radius: float,
    ) -> None:
        center = self._center(geometry, annotation.position)
        is_open = annotation.position.fret == 0
        if is_open:
            painter.setBrush(QBrush(_BACKGROUND_COLOR))
            outline = _OPEN_PEN if annotation.role in _SCALE_ROLES else _INTERVAL_OUTLINE
            painter.setPen(QPen(outline, 2.0))
            painter.drawEllipse(center, radius, radius)
            text_color = _DEGREE_TEXT if annotation.role in _SCALE_ROLES else _INTERVAL_TEXT
            painter.setPen(QPen(text_color))
        elif annotation.role is RenderRole.SCALE_ROOT:
            painter.setBrush(QBrush(_TONIC_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(_TONIC_TEXT))
        elif annotation.role is RenderRole.SCALE_TONE:
            painter.setBrush(QBrush(_DEGREE_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(_DEGREE_TEXT))
        elif annotation.role is RenderRole.INTERVAL_ROOT:
            painter.setBrush(QBrush(_INTERVAL_ROOT_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(_INTERVAL_ROOT_TEXT))
        elif annotation.role is RenderRole.TRIAD_ROOT:
            painter.setBrush(QBrush(_TRIAD_ROOT_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(_TRIAD_ROOT_TEXT))
        else:
            painter.setBrush(QBrush(_INTERVAL_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(_INTERVAL_TEXT))
        painter.drawText(
            QRectF(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
            ),
            int(Qt.AlignmentFlag.AlignCenter),
            annotation.label,
        )

    def _draw_badge(
        self,
        painter: QPainter,
        geometry: FretboardGeometry,
        annotation: FretboardRenderAnnotation,
        badge_radius: float,
        primary_radius: float,
        badge_index: int,
    ) -> None:
        center = self._center(geometry, annotation.position)
        offset = primary_radius * 0.35 + badge_radius * 0.5
        dx, dy = _BADGE_OFFSETS[badge_index % len(_BADGE_OFFSETS)]
        badge_center = center + QPointF(offset * dx, offset * dy)
        painter.setBrush(QBrush(_BADGE_FILL))
        painter.setPen(QPen(_BADGE_OUTLINE, 1.0))
        painter.drawEllipse(badge_center, badge_radius, badge_radius)
        font = painter.font()
        font.setPixelSize(max(6, int(badge_radius * 1.1)))
        painter.setFont(font)
        painter.setPen(QPen(_BADGE_TEXT))
        painter.drawText(
            QRectF(
                badge_center.x() - badge_radius,
                badge_center.y() - badge_radius,
                badge_radius * 2,
                badge_radius * 2,
            ),
            int(Qt.AlignmentFlag.AlignCenter),
            annotation.label,
        )

    def _draw_voicing_group(
        self,
        painter: QPainter,
        geometry: FretboardGeometry,
        group: TriadVoicingRenderGroup,
    ) -> None:
        """Draw the active voicing as a subtle triangle linking its three points.

        The connecting polygon is drawn before the point annotations and uses a
        translucent fill plus a thin outline, so it encloses the three
        positions without obscuring their labels. A small inversion label (R /
        1st / 2nd) sits at the triangle's centroid.
        """
        centers = [self._center(geometry, position) for position in group.positions]
        polygon = QPolygonF(centers)
        painter.save()
        painter.setPen(QPen(_VOICING_GROUP_PEN, 1.5))
        painter.setBrush(QBrush(_VOICING_GROUP_FILL))
        painter.drawPolygon(polygon)
        centroid = QPointF(
            sum(point.x() for point in centers) / len(centers),
            sum(point.y() for point in centers) / len(centers),
        )
        font = painter.font()
        font.setPixelSize(max(8, int(geometry.row_height * 0.4)))
        painter.setFont(font)
        painter.setPen(QPen(_VOICING_GROUP_PEN))
        painter.drawText(
            QRectF(
                centroid.x() - 24,
                centroid.y() - 10,
                48,
                20,
            ),
            int(Qt.AlignmentFlag.AlignCenter),
            _VOICING_INVERSION_LABELS[group.inversion],
        )
        painter.restore()

    def _center(self, geometry: FretboardGeometry, position: FretPosition) -> QPointF:
        return QPointF(
            geometry.x_for_fret(position.fret),
            geometry.y_for_string(position.string_number),
        )
