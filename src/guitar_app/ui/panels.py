"""Reusable layout panels for the main window's control column.

Each panel builds one logical section of the workspace controls (instrument,
musical context, layers, triads) and exposes its widgets as attributes. Panels
are presentation-only: they create and arrange widgets but own no state, run
no evaluation, and wire no signals — the :class:`MainWindow` keeps every
widget's state and connections, and aliases the widgets as its own attributes
so callers address ``window.tuning_selector`` etc. exactly as before.
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from guitar_app.ui.layer_controls import LAYER_CONTROLS
from guitar_app.ui.palette import (
    DEGREE_FILL,
    INTERVAL_FILL,
    TONIC_FILL,
    TRIAD_FILL,
)
from guitar_app.ui.tuning_editor import CustomTuningEditor


def _section_header(text: str) -> QLabel:
    """A bold header for one control section."""
    header = QLabel(text)
    header.setStyleSheet("font-weight: 600;")
    return header


class InstrumentPanel(QWidget):
    """Instrument section: tuning selector, readout, and the custom editor."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tuning_selector = QComboBox()
        self.tuning_label = QLabel()
        self.tuning_editor_button = QPushButton("Edit Tuning…")
        self.tuning_editor = CustomTuningEditor()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(_section_header("Instrument"))
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        form.addRow("Tuning:", self.tuning_selector)
        form.addRow("", self.tuning_label)
        form.addRow("", self.tuning_editor_button)
        layout.addLayout(form)
        self.tuning_editor.setVisible(False)
        layout.addWidget(self.tuning_editor)


class MusicalContextPanel(QWidget):
    """Musical-context section: root, scale, mode, view, and the readouts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.root_selector = QComboBox()
        self.scale_selector = QComboBox()
        self.mode_selector = QComboBox()
        self.view_selector = QComboBox()
        self.selection_label = QLabel()
        self.mode_label = QLabel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(_section_header("Musical Context"))
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        form.addRow("Root:", self.root_selector)
        form.addRow("Scale:", self.scale_selector)
        form.addRow("Mode:", self.mode_selector)
        form.addRow("View:", self.view_selector)
        layout.addLayout(form)
        self.selection_label.setWordWrap(True)
        self.mode_label.setWordWrap(True)
        layout.addWidget(self.selection_label)
        layout.addWidget(self.mode_label)


class LayerPanel(QWidget):
    """Layers section: one checkbox per layer-control definition."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layer_checkboxes: dict[str, QCheckBox] = {
            control.id: QCheckBox(control.name) for control in LAYER_CONTROLS
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(_section_header("Layers"))
        for control in LAYER_CONTROLS:
            layout.addWidget(self.layer_checkboxes[control.id])


class TriadPanel(QWidget):
    """Triads section: quality selector, voicing cycling, and the readout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.triad_quality_selector = QComboBox()
        self.previous_voicing_button = QPushButton("Prev")
        self.next_voicing_button = QPushButton("Next")
        self.voicing_label = QLabel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(_section_header("Triads"))
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        form.addRow("Quality:", self.triad_quality_selector)
        layout.addLayout(form)
        voicing_row = QHBoxLayout()
        voicing_row.setSpacing(6)
        voicing_row.addWidget(self.previous_voicing_button)
        voicing_row.addWidget(self.next_voicing_button)
        voicing_row.addStretch(1)
        layout.addLayout(voicing_row)
        self.voicing_label.setWordWrap(True)
        layout.addWidget(self.voicing_label)


class LegendWidget(QWidget):
    """A compact color legend for the fretboard's marker palette.

    The legend is built from the same shared :mod:`guitar_app.ui.palette`
    constants the fretboard paints with, so it can never drift from the board.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[tuple[str, QColor]] = [
            ("Root", TONIC_FILL),
            ("Scale tone", DEGREE_FILL),
            ("Interval", INTERVAL_FILL),
            ("Triad tone", TRIAD_FILL),
        ]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)
        for label, color in self._items:
            layout.addWidget(self._entry(label, color))
        layout.addStretch(1)

    @property
    def legend_items(self) -> tuple[tuple[str, str], ...]:
        """The legend's ``(label, color-hex)`` pairs in display order."""
        return tuple((label, color.name()) for label, color in self._items)

    def _entry(self, label: str, color: QColor) -> QWidget:
        entry = QWidget()
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 6px; border: 1px solid #8a8a8a;"
        )
        row.addWidget(dot)
        row.addWidget(QLabel(label))
        return entry


class WorkspaceHeader(QWidget):
    """The two-line summary above the fretboard: title and context details."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title_label = QLabel()
        self.context_label = QLabel()
        title_font = self.title_label.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        self.title_label.setFont(title_font)
        self.context_label.setStyleSheet("color: #666666;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(2)
        layout.addWidget(self.title_label)
        layout.addWidget(self.context_label)

    def set_title(self, text: str) -> None:
        """Set the large title line (e.g. ``"A Minor Pentatonic"``)."""
        self.title_label.setText(text)

    def set_context(self, text: str) -> None:
        """Set the smaller context line (tuning, fret count, parent major)."""
        self.context_label.setText(text)
