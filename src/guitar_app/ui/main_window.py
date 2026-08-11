"""Main window: root/scale selectors, layer checkboxes, and the fretboard widget."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
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
from guitar_app.services.interval_service import evaluate_intervals
from guitar_app.services.scale_service import available_scale_formulas, evaluate_scale
from guitar_app.ui.fretboard_widget import FretboardWidget
from guitar_app.ui.layer_controls import LAYER_CONTROLS
from guitar_app.ui.render_annotations import (
    FretboardRenderAnnotation,
    render_interval_result,
    render_scale_result,
)

#: The fixed fretboard shown in this first vertical slice.
STANDARD_BOARD = Fretboard(STANDARD, 12)


class MainWindow(QMainWindow):
    """The application's main window.

    Owns the root/scale selectors, a checkbox per layer-control definition,
    and the fretboard widget. On any selection or toggle change it evaluates
    only the enabled layers through their services, projects the results into
    render annotations in control order, and hands the combined immutable
    collection to the widget; it never constructs scale formulas or performs
    interval calculations itself.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Guitar Assist")
        self._pitch_classes: tuple[PitchClass, ...] = tuple(PitchClass)
        self._scale_formulas: tuple[NamedScaleFormula, ...] = available_scale_formulas()

        self.root_selector = QComboBox()
        self.scale_selector = QComboBox()
        self.layer_checkboxes: dict[str, QCheckBox] = {
            control.id: QCheckBox(control.name) for control in LAYER_CONTROLS
        }
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
        for control in LAYER_CONTROLS:
            self.layer_checkboxes[control.id].setChecked(control.default_enabled)

    def _build_layout(self) -> None:
        selectors = QWidget()
        selectors_layout = QHBoxLayout(selectors)
        selectors_layout.setContentsMargins(8, 8, 8, 8)
        selectors_layout.setSpacing(6)
        selectors_layout.addWidget(QLabel("Root:"))
        selectors_layout.addWidget(self.root_selector)
        selectors_layout.addWidget(QLabel("Scale:"))
        selectors_layout.addWidget(self.scale_selector)
        for control in LAYER_CONTROLS:
            selectors_layout.addWidget(self.layer_checkboxes[control.id])
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
        for control in LAYER_CONTROLS:
            self.layer_checkboxes[control.id].toggled.connect(self._update_fretboard)

    def _update_fretboard(self, *_args: object) -> None:
        """Re-evaluate the enabled layers for the current selection and redraw."""
        if self.root_selector.currentIndex() < 0 or self.scale_selector.currentIndex() < 0:
            return
        named = self._scale_formulas[self.scale_selector.currentIndex()]
        root = self._pitch_classes[self.root_selector.currentIndex()]
        try:
            annotations = self._enabled_annotations(root, named)
        except (UnknownScaleFormulaError, InvalidScaleDegreeError) as exc:
            self.statusBar().showMessage(
                f"Could not evaluate {root.spelling()} {named.name}: {exc}"
            )
            return
        self.statusBar().clearMessage()
        self.selection_label.setText(self._selection_label(root, named))
        self.fretboard_widget.set_annotations(STANDARD_BOARD, annotations)

    def _selection_label(self, root: PitchClass, named: NamedScaleFormula) -> str:
        """Describe the visible workspace: root, then the enabled layers.

        Root is always shown because it defines interval context. The scale is
        only named while the Scale layer is enabled, so the label never
        describes hidden content.
        """
        root_spelling = root.spelling()
        if self.layer_checkboxes["scale"].isChecked():
            return f"{root_spelling} {named.name}"
        if self.layer_checkboxes["interval"].isChecked():
            return f"{root_spelling} Intervals"
        return f"{root_spelling} — No layers"

    def _enabled_annotations(
        self,
        root: PitchClass,
        named: NamedScaleFormula,
    ) -> tuple[FretboardRenderAnnotation, ...]:
        """Project only the enabled layers, combined in control order.

        A small explicit branch per known UI layer is intentional: there is no
        generic dispatcher, and the scale layer's ``evaluate_scale`` needs the
        selected scale id while the interval layer only needs the root.
        """
        annotations: list[FretboardRenderAnnotation] = []
        for control in LAYER_CONTROLS:
            if not self.layer_checkboxes[control.id].isChecked():
                continue
            if control.id == "scale":
                scale_result = evaluate_scale(STANDARD_BOARD, root, named.id)
                annotations.extend(render_scale_result(scale_result))
            elif control.id == "interval":
                interval_result = evaluate_intervals(STANDARD_BOARD, root)
                annotations.extend(render_interval_result(interval_result))
        return tuple(annotations)
