"""Custom fretboard widget that renders render annotations.

The widget receives an already-projected, UI-only collection of
:class:`FretboardRenderAnnotation` (plus the :class:`Fretboard` used for
geometry) and optionally one active :class:`TriadVoicingRenderGroup`. It knows
nothing about scale-, interval-, or triad-domain annotation types and owns all
painting; the core and services remain Qt-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from guitar_app.core.fretboard.fretboard import Fretboard, FretPosition
from guitar_app.core.theory.triad import TriadInversion
from guitar_app.ui.geometry import (
    FretboardGeometry,
    double_marker_frets,
    fret_markers,
    fretboard_geometry,
)
from guitar_app.ui.palette import (
    BACKGROUND_COLOR,
    BADGE_FILL,
    BADGE_OUTLINE,
    BADGE_TEXT,
    DEGREE_FILL,
    DEGREE_TEXT,
    FRET_COLOR,
    INTERVAL_FILL,
    INTERVAL_OUTLINE,
    INTERVAL_ROOT_FILL,
    INTERVAL_ROOT_TEXT,
    INTERVAL_TEXT,
    MARKER_COLOR,
    NUT_COLOR,
    OPEN_PEN,
    STRING_COLOR,
    TONIC_FILL,
    TONIC_TEXT,
    TRIAD_FILL,
    TRIAD_OUTLINE,
    TRIAD_ROOT_FILL,
    TRIAD_ROOT_TEXT,
    TRIAD_TEXT,
    VOICING_GROUP_FILL,
    VOICING_GROUP_PEN,
)
from guitar_app.ui.render_annotations import (
    FretboardRenderAnnotation,
    RenderRole,
    TriadVoicingRenderGroup,
)

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
_TRIAD_ROLES = (RenderRole.TRIAD_ROOT, RenderRole.TRIAD_TONE)


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
        painter.fillRect(self.rect(), BACKGROUND_COLOR)
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
                painter.setPen(QPen(NUT_COLOR, 4.0))
            else:
                painter.setPen(QPen(FRET_COLOR, 1.0))
            painter.drawLine(
                QPointF(x, geometry.top),
                QPointF(x, geometry.top + geometry.height),
            )
        painter.restore()

    def _draw_strings(self, painter: QPainter, geometry: FretboardGeometry) -> None:
        painter.save()
        painter.setPen(QPen(STRING_COLOR, 1.0))
        for string_number in range(1, geometry.string_count + 1):
            y = geometry.y_for_string(string_number)
            painter.drawLine(
                QPointF(geometry.left, y),
                QPointF(geometry.left + geometry.width, y),
            )
        painter.restore()

    def _draw_fret_markers(self, painter: QPainter, geometry: FretboardGeometry) -> None:
        painter.save()
        painter.setBrush(QBrush(MARKER_COLOR))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        radius = geometry.row_height * 0.18
        mid_y = geometry.top + geometry.height / 2
        for fret in fret_markers(geometry.fret_count):
            x = geometry.x_for_fret(fret)
            painter.drawEllipse(QPointF(x, mid_y), radius, radius)
        offset = radius * 1.9
        for fret in double_marker_frets(geometry.fret_count):
            x = geometry.x_for_fret(fret)
            painter.drawEllipse(QPointF(x, mid_y - offset), radius, radius)
            painter.drawEllipse(QPointF(x, mid_y + offset), radius, radius)
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
            painter.setBrush(QBrush(BACKGROUND_COLOR))
            if annotation.role in _SCALE_ROLES:
                outline, text_color = OPEN_PEN, DEGREE_TEXT
            elif annotation.role in _TRIAD_ROLES:
                outline, text_color = TRIAD_OUTLINE, TRIAD_TEXT
            else:
                outline, text_color = INTERVAL_OUTLINE, INTERVAL_TEXT
            painter.setPen(QPen(outline, 2.0))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(text_color))
        elif annotation.role is RenderRole.SCALE_ROOT:
            painter.setBrush(QBrush(TONIC_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(TONIC_TEXT))
        elif annotation.role is RenderRole.SCALE_TONE:
            painter.setBrush(QBrush(DEGREE_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(DEGREE_TEXT))
        elif annotation.role is RenderRole.INTERVAL_ROOT:
            painter.setBrush(QBrush(INTERVAL_ROOT_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(INTERVAL_ROOT_TEXT))
        elif annotation.role is RenderRole.TRIAD_ROOT:
            painter.setBrush(QBrush(TRIAD_ROOT_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(TRIAD_ROOT_TEXT))
        elif annotation.role is RenderRole.INTERVAL:
            painter.setBrush(QBrush(INTERVAL_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(INTERVAL_TEXT))
        else:
            painter.setBrush(QBrush(TRIAD_FILL))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(TRIAD_TEXT))
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
        painter.setBrush(QBrush(BADGE_FILL))
        painter.setPen(QPen(BADGE_OUTLINE, 1.0))
        painter.drawEllipse(badge_center, badge_radius, badge_radius)
        font = painter.font()
        font.setPixelSize(max(6, int(badge_radius * 1.1)))
        painter.setFont(font)
        painter.setPen(QPen(BADGE_TEXT))
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
        painter.setPen(QPen(VOICING_GROUP_PEN, 1.5))
        painter.setBrush(QBrush(VOICING_GROUP_FILL))
        painter.drawPolygon(polygon)
        centroid = QPointF(
            sum(point.x() for point in centers) / len(centers),
            sum(point.y() for point in centers) / len(centers),
        )
        font = painter.font()
        font.setPixelSize(max(8, int(geometry.row_height * 0.4)))
        painter.setFont(font)
        painter.setPen(QPen(VOICING_GROUP_PEN))
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
