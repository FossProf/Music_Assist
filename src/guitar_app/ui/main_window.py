"""Main window: root/scale selectors, layer checkboxes, and the fretboard widget."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from guitar_app.core.errors import InvalidScaleDegreeError, UnknownScaleFormulaError
from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.instrument.tuning import STANDARD
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale_formulas import MINOR_PENTATONIC, NamedScaleFormula
from guitar_app.core.theory.triad import TriadQuality
from guitar_app.services.interval_service import evaluate_intervals
from guitar_app.services.scale_service import available_scale_formulas, evaluate_scale
from guitar_app.services.triad_service import available_triad_qualities, evaluate_triad
from guitar_app.ui.fretboard_widget import FretboardWidget
from guitar_app.ui.layer_controls import LAYER_CONTROLS
from guitar_app.ui.render_annotations import (
    FretboardRenderAnnotation,
    TriadVoicingRenderGroup,
    render_interval_result,
    render_scale_result,
    render_triad_result,
    render_triad_voicings,
)

#: The fixed fretboard shown in this first vertical slice.
STANDARD_BOARD = Fretboard(STANDARD, 12)


class MainWindow(QMainWindow):
    """The application's main window.

    Owns the root/scale/quality selectors, a checkbox per layer-control
    definition, Previous/Next voicing cycling, and the fretboard widget. On any
    selection or toggle change it evaluates only the enabled layers through
    their services, projects the results into render annotations in control
    order, and hands the combined immutable collection (plus the currently
    active voicing group) to the widget; it never constructs scale formulas or
    performs triad calculations itself.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Guitar Assist")
        self._pitch_classes: tuple[PitchClass, ...] = tuple(PitchClass)
        self._scale_formulas: tuple[NamedScaleFormula, ...] = available_scale_formulas()
        self._triad_qualities: tuple[TriadQuality, ...] = available_triad_qualities()

        self.root_selector = QComboBox()
        self.scale_selector = QComboBox()
        self.triad_quality_selector = QComboBox()
        self.layer_checkboxes: dict[str, QCheckBox] = {
            control.id: QCheckBox(control.name) for control in LAYER_CONTROLS
        }
        self.previous_voicing_button = QPushButton("Prev")
        self.next_voicing_button = QPushButton("Next")
        self.selection_label = QLabel()
        self.voicing_label = QLabel()
        self.fretboard_widget = FretboardWidget()

        self._triad_groups: tuple[TriadVoicingRenderGroup, ...] = ()
        self._active_voicing_index = 0

        self._build_selectors()
        self._build_layout()
        self._connect_selectors()
        self._update_fretboard()

    def _build_selectors(self) -> None:
        for pitch_class in self._pitch_classes:
            self.root_selector.addItem(pitch_class.spelling())
        for named in self._scale_formulas:
            self.scale_selector.addItem(named.name)
        for quality in self._triad_qualities:
            self.triad_quality_selector.addItem(quality.display_name)
        self.root_selector.setCurrentIndex(self._pitch_classes.index(PitchClass.A))
        self.scale_selector.setCurrentIndex(self._scale_formulas.index(MINOR_PENTATONIC))
        self.triad_quality_selector.setCurrentIndex(self._triad_qualities.index(TriadQuality.MAJOR))
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
        selectors_layout.addWidget(QLabel("Quality:"))
        selectors_layout.addWidget(self.triad_quality_selector)
        for control in LAYER_CONTROLS:
            selectors_layout.addWidget(self.layer_checkboxes[control.id])
        selectors_layout.addWidget(self.selection_label)
        selectors_layout.addWidget(self.previous_voicing_button)
        selectors_layout.addWidget(self.next_voicing_button)
        selectors_layout.addWidget(self.voicing_label)
        selectors_layout.addStretch(1)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(selectors)
        layout.addWidget(self.fretboard_widget, 1)
        self.setCentralWidget(central)
        self.resize(820, 420)

    def _connect_selectors(self) -> None:
        self.root_selector.currentIndexChanged.connect(self._update_fretboard)
        self.scale_selector.currentIndexChanged.connect(self._update_fretboard)
        self.triad_quality_selector.currentIndexChanged.connect(self._update_fretboard)
        for control in LAYER_CONTROLS:
            self.layer_checkboxes[control.id].toggled.connect(self._update_fretboard)
        self.previous_voicing_button.clicked.connect(self._previous_voicing)
        self.next_voicing_button.clicked.connect(self._next_voicing)

    def _update_fretboard(self, *_args: object) -> None:
        """Re-evaluate the enabled layers for the current selection and redraw."""
        if self.root_selector.currentIndex() < 0 or self.scale_selector.currentIndex() < 0:
            return
        named = self._scale_formulas[self.scale_selector.currentIndex()]
        root = self._pitch_classes[self.root_selector.currentIndex()]
        quality = self._triad_qualities[self.triad_quality_selector.currentIndex()]
        try:
            annotations, groups = self._enabled_layer_data(root, named, quality)
        except (UnknownScaleFormulaError, InvalidScaleDegreeError) as exc:
            self.statusBar().showMessage(
                f"Could not evaluate {root.spelling()} {named.name}: {exc}"
            )
            return
        self.statusBar().clearMessage()
        self.selection_label.setText(self._selection_label(root, named, quality))
        # Reset the active voicing only when the underlying triad result changed
        # (root, quality, or fretboard), so toggling unrelated layers preserves
        # the user's chosen voicing.
        if groups != self._triad_groups:
            self._triad_groups = groups
            self._active_voicing_index = 0
        self._apply_active_voicing()
        self.fretboard_widget.set_annotations(STANDARD_BOARD, annotations)

    def _selection_label(
        self, root: PitchClass, named: NamedScaleFormula, quality: TriadQuality
    ) -> str:
        """Describe the visible workspace: root, then the enabled layers.

        Root is always shown because it defines interval context. A layer is
        only named while it is enabled, so the label never describes hidden
        content.
        """
        root_spelling = root.spelling()
        parts: list[str] = []
        if self.layer_checkboxes["scale"].isChecked():
            parts.append(named.name)
        if self.layer_checkboxes["interval"].isChecked():
            parts.append("Intervals")
        if self.layer_checkboxes["triad"].isChecked():
            parts.append(f"{quality.display_name} Triads")
        if not parts:
            return f"{root_spelling} — No layers"
        return f"{root_spelling} {' · '.join(parts)}"

    def _enabled_layer_data(
        self,
        root: PitchClass,
        named: NamedScaleFormula,
        quality: TriadQuality,
    ) -> tuple[
        tuple[FretboardRenderAnnotation, ...],
        tuple[TriadVoicingRenderGroup, ...],
    ]:
        """Project only the enabled layers, combined in control order.

        A small explicit branch per known UI layer is intentional: there is no
        generic dispatcher, and each layer's service takes different inputs.
        The triad branch returns both its point annotations and its voicing
        groups from a single ``evaluate_triad`` call.
        """
        annotations: list[FretboardRenderAnnotation] = []
        groups: tuple[TriadVoicingRenderGroup, ...] = ()
        for control in LAYER_CONTROLS:
            if not self.layer_checkboxes[control.id].isChecked():
                continue
            if control.id == "scale":
                scale_result = evaluate_scale(STANDARD_BOARD, root, named.id)
                annotations.extend(render_scale_result(scale_result))
            elif control.id == "interval":
                interval_result = evaluate_intervals(STANDARD_BOARD, root)
                annotations.extend(render_interval_result(interval_result))
            elif control.id == "triad":
                triad_result = evaluate_triad(STANDARD_BOARD, root, quality)
                annotations.extend(render_triad_result(triad_result))
                groups = render_triad_voicings(triad_result)
        return tuple(annotations), groups

    def _previous_voicing(self) -> None:
        """Step to the previous voicing, wrapping modulo the group count."""
        if not self._triad_groups:
            return
        self._active_voicing_index = (self._active_voicing_index - 1) % len(self._triad_groups)
        self._apply_active_voicing()

    def _next_voicing(self) -> None:
        """Step to the next voicing, wrapping modulo the group count."""
        if not self._triad_groups:
            return
        self._active_voicing_index = (self._active_voicing_index + 1) % len(self._triad_groups)
        self._apply_active_voicing()

    def _apply_active_voicing(self) -> None:
        """Highlight the currently active voicing and describe it.

        Only one voicing group is drawn at a time. The index is clamped modulo
        the group count so it always refers to a valid group.
        """
        if not self.layer_checkboxes["triad"].isChecked():
            self.fretboard_widget.set_voicing_group(None)
            self.voicing_label.setText("")
            self.previous_voicing_button.setEnabled(False)
            self.next_voicing_button.setEnabled(False)
            return
        if not self._triad_groups:
            self.fretboard_widget.set_voicing_group(None)
            self.voicing_label.setText("No triad voicings")
            self.previous_voicing_button.setEnabled(False)
            self.next_voicing_button.setEnabled(False)
            return
        index = self._active_voicing_index % len(self._triad_groups)
        group = self._triad_groups[index]
        self.fretboard_widget.set_voicing_group(group)
        self.voicing_label.setText(
            f"Voicing {index + 1} / {len(self._triad_groups)} — "
            f"{group.inversion.display_name} — "
            f"strings {'-'.join(str(string) for string in group.string_set)}"
        )
        self.previous_voicing_button.setEnabled(True)
        self.next_voicing_button.setEnabled(True)
