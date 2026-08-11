"""Main window: root and scale selectors plus the fretboard widget."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from guitar_app.core.errors import InvalidScaleDegreeError, UnknownScaleFormulaError
from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.instrument.tuning import STANDARD
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale_formulas import MINOR_PENTATONIC, NamedScaleFormula
from guitar_app.services.scale_service import available_scale_formulas, evaluate_scale
from guitar_app.ui.fretboard_widget import FretboardWidget

#: The fixed fretboard shown in this first vertical slice.
STANDARD_BOARD = Fretboard(STANDARD, 12)


class MainWindow(QMainWindow):
    """The application's main window.

    Owns the root/scale selectors and the fretboard widget. It calls the scale
    service and hands the evaluated ``LayerResult`` to the widget; it never
    constructs scale formulas or performs interval calculations itself.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Guitar Assist")
        self._pitch_classes: tuple[PitchClass, ...] = tuple(PitchClass)
        self._scale_formulas: tuple[NamedScaleFormula, ...] = available_scale_formulas()

        self.root_selector = QComboBox()
        self.scale_selector = QComboBox()
        self.selection_label = QLabel()
        self.fretboard_widget = FretboardWidget()

        self._build_selectors()
        self._build_layout()
        self._connect_selectors()
        self._update_fretboard()

    def _build_selectors(self) -> None:
        for pitch_class in self._pitch_classes:
            self.root_selector.addItem(pitch_class.spelling())
        for named in self._scale_formulas:
            self.scale_selector.addItem(named.name)
        self.root_selector.setCurrentIndex(self._pitch_classes.index(PitchClass.A))
        self.scale_selector.setCurrentIndex(self._scale_formulas.index(MINOR_PENTATONIC))

    def _build_layout(self) -> None:
        selectors = QWidget()
        selectors_layout = QHBoxLayout(selectors)
        selectors_layout.setContentsMargins(8, 8, 8, 8)
        selectors_layout.setSpacing(6)
        selectors_layout.addWidget(QLabel("Root:"))
        selectors_layout.addWidget(self.root_selector)
        selectors_layout.addWidget(QLabel("Scale:"))
        selectors_layout.addWidget(self.scale_selector)
        selectors_layout.addWidget(self.selection_label)
        selectors_layout.addStretch(1)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(selectors)
        layout.addWidget(self.fretboard_widget, 1)
        self.setCentralWidget(central)
        self.resize(760, 420)

    def _connect_selectors(self) -> None:
        self.root_selector.currentIndexChanged.connect(self._update_fretboard)
        self.scale_selector.currentIndexChanged.connect(self._update_fretboard)

    def _update_fretboard(self, *_args: object) -> None:
        """Re-evaluate the scale service for the current selection and redraw."""
        if self.root_selector.currentIndex() < 0 or self.scale_selector.currentIndex() < 0:
            return
        named = self._scale_formulas[self.scale_selector.currentIndex()]
        root = self._pitch_classes[self.root_selector.currentIndex()]
        try:
            result = evaluate_scale(STANDARD_BOARD, root, named.id)
        except (UnknownScaleFormulaError, InvalidScaleDegreeError) as exc:
            self.statusBar().showMessage(
                f"Could not evaluate {root.spelling()} {named.name}: {exc}"
            )
            return
        self.statusBar().clearMessage()
        self.selection_label.setText(f"{root.spelling()} {named.name}")
        self.fretboard_widget.set_fretboard_data(STANDARD_BOARD, result)
