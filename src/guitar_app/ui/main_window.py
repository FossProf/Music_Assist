"""Main window: tuning/root/scale selectors, layer checkboxes, and the fretboard widget."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker
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

from guitar_app.core.errors import (
    InvalidPositionError,
    InvalidScaleDegreeError,
    InvalidTuningError,
    UnknownScaleFormulaError,
)
from guitar_app.core.fretboard.fretboard import Fretboard
from guitar_app.core.instrument.tuning_presets import (
    STANDARD_TUNING,
    NamedTuning,
    available_tunings,
)
from guitar_app.core.theory.mode import Mode, available_modes
from guitar_app.core.theory.pitch import PitchClass
from guitar_app.core.theory.scale_formulas import MINOR_PENTATONIC, NamedScaleFormula
from guitar_app.core.theory.triad import TriadQuality
from guitar_app.services.instrument_state import (
    DEFAULT_INSTRUMENT_STATE,
    InstrumentState,
    instrument_from_string_pitches,
    instrument_from_tuning_id,
)
from guitar_app.services.interval_service import evaluate_intervals
from guitar_app.services.mode_service import (
    ModeSelection,
    ModeView,
    available_mode_views,
    evaluate_mode,
)
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
from guitar_app.ui.tuning_editor import CustomTuningEditor


class MainWindow(QMainWindow):
    """The application's main window.

    Owns the active :class:`InstrumentState`, the tuning/root/scale/quality
    selectors, a checkbox per layer-control definition, Previous/Next voicing
    cycling, a compact custom-tuning editor, and the fretboard widget. The
    tuning selector lists the built-in presets plus a non-catalog ``Custom``
    item; applying the string editor builds a custom :class:`InstrumentState`
    (``tuning_id=None``, ``display_name="Custom"``) and switches the selector
    to ``Custom``. On any selection or toggle change it re-derives the active
    fretboard from the instrument state, evaluates only the enabled layers
    through their services, projects the results into render annotations in
    control order, and hands the combined immutable collection (plus the
    currently active voicing group) to the widget; it never constructs scale
    formulas or performs triad calculations itself.

    A Mode selector (Ionian..Locrian) and a View selector (Parallel/Relative)
    sit beside the existing controls. The default Ionian/Parallel selection is
    the identity: the root and scale selectors drive evaluation exactly as
    before. Selecting any other mode activates modal context: the scale
    selector mirrors the mode's formula, and in the Relative view the effective
    root becomes the derived modal root (the input root is treated as the
    parent-major root). The compact :attr:`mode_label` readout then shows the
    modal root, its parent-major root, and the characteristic alterations from
    Ionian. Leaving modal context restores the previously selected scale;
    changing the scale while a mode is active drops back out of modal context.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Guitar Assist")
        self._pitch_classes: tuple[PitchClass, ...] = tuple(PitchClass)
        self._scale_formulas: tuple[NamedScaleFormula, ...] = available_scale_formulas()
        self._triad_qualities: tuple[TriadQuality, ...] = available_triad_qualities()
        self._tunings: tuple[NamedTuning, ...] = available_tunings()
        self._modes: tuple[Mode, ...] = available_modes()
        self._mode_views: tuple[ModeView, ...] = available_mode_views()
        self._instrument_state: InstrumentState = DEFAULT_INSTRUMENT_STATE

        self.tuning_selector = QComboBox()
        self.root_selector = QComboBox()
        self.scale_selector = QComboBox()
        self.triad_quality_selector = QComboBox()
        self.mode_selector = QComboBox()
        self.view_selector = QComboBox()
        self.layer_checkboxes: dict[str, QCheckBox] = {
            control.id: QCheckBox(control.name) for control in LAYER_CONTROLS
        }
        self.previous_voicing_button = QPushButton("Prev")
        self.next_voicing_button = QPushButton("Next")
        self.tuning_label = QLabel()
        self.selection_label = QLabel()
        self.mode_label = QLabel()
        self.voicing_label = QLabel()
        self.tuning_editor = CustomTuningEditor()
        self.tuning_editor_button = QPushButton("Edit Tuning…")
        self.fretboard_widget = FretboardWidget()

        self._triad_groups: tuple[TriadVoicingRenderGroup, ...] = ()
        self._active_voicing_index = 0
        self._editor_synced_index = -1
        self._scale_index_before_mode: int | None = None
        self._tuning_editor_open = False

        self._build_selectors()
        self._build_layout()
        self._connect_selectors()
        self._update_fretboard()

    def _build_selectors(self) -> None:
        for tuning in self._tunings:
            self.tuning_selector.addItem(tuning.name, tuning.id)
        self.tuning_selector.addItem("Custom", None)
        self._custom_tuning_index = self.tuning_selector.count() - 1
        for pitch_class in self._pitch_classes:
            self.root_selector.addItem(pitch_class.spelling())
        for named in self._scale_formulas:
            self.scale_selector.addItem(named.name)
        for quality in self._triad_qualities:
            self.triad_quality_selector.addItem(quality.display_name)
        for mode in self._modes:
            self.mode_selector.addItem(mode.display_name, mode)
        for view in self._mode_views:
            self.view_selector.addItem(view.display_name, view)
        self.tuning_selector.setCurrentIndex(self._tunings.index(STANDARD_TUNING))
        self.root_selector.setCurrentIndex(self._pitch_classes.index(PitchClass.A))
        self.scale_selector.setCurrentIndex(self._scale_formulas.index(MINOR_PENTATONIC))
        self.triad_quality_selector.setCurrentIndex(self._triad_qualities.index(TriadQuality.MAJOR))
        self.mode_selector.setCurrentIndex(self._modes.index(Mode.IONIAN))
        self.view_selector.setCurrentIndex(self._mode_views.index(ModeView.PARALLEL))
        for control in LAYER_CONTROLS:
            self.layer_checkboxes[control.id].setChecked(control.default_enabled)
        self._update_view_enabled()

    def _build_layout(self) -> None:
        selectors = QWidget()
        selectors_layout = QHBoxLayout(selectors)
        selectors_layout.setContentsMargins(8, 8, 8, 8)
        selectors_layout.setSpacing(6)
        selectors_layout.addWidget(QLabel("Tuning:"))
        selectors_layout.addWidget(self.tuning_selector)
        selectors_layout.addWidget(QLabel("Root:"))
        selectors_layout.addWidget(self.root_selector)
        selectors_layout.addWidget(QLabel("Scale:"))
        selectors_layout.addWidget(self.scale_selector)
        selectors_layout.addWidget(QLabel("Quality:"))
        selectors_layout.addWidget(self.triad_quality_selector)
        selectors_layout.addWidget(QLabel("Mode:"))
        selectors_layout.addWidget(self.mode_selector)
        selectors_layout.addWidget(QLabel("View:"))
        selectors_layout.addWidget(self.view_selector)
        for control in LAYER_CONTROLS:
            selectors_layout.addWidget(self.layer_checkboxes[control.id])
        selectors_layout.addWidget(self.tuning_label)
        selectors_layout.addWidget(self.selection_label)
        selectors_layout.addWidget(self.mode_label)
        selectors_layout.addWidget(self.tuning_editor_button)
        selectors_layout.addWidget(self.previous_voicing_button)
        selectors_layout.addWidget(self.next_voicing_button)
        selectors_layout.addWidget(self.voicing_label)
        selectors_layout.addStretch(1)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(selectors)
        layout.addWidget(self.tuning_editor)
        layout.addWidget(self.fretboard_widget, 1)
        self.setCentralWidget(central)
        self.tuning_editor.setVisible(False)
        self.resize(900, 420)

    def _connect_selectors(self) -> None:
        self.tuning_selector.currentIndexChanged.connect(self._update_fretboard)
        self.root_selector.currentIndexChanged.connect(self._update_fretboard)
        self.scale_selector.currentIndexChanged.connect(self._update_fretboard)
        self.triad_quality_selector.currentIndexChanged.connect(self._update_fretboard)
        self.mode_selector.currentIndexChanged.connect(self._on_mode_changed)
        self.view_selector.currentIndexChanged.connect(self._update_fretboard)
        for control in LAYER_CONTROLS:
            self.layer_checkboxes[control.id].toggled.connect(self._update_fretboard)
        self.tuning_editor_button.clicked.connect(self._toggle_tuning_editor)
        self.tuning_editor.edited.connect(self._on_tuning_edited)
        self.tuning_editor.apply_requested.connect(self._apply_custom_tuning)
        self.previous_voicing_button.clicked.connect(self._previous_voicing)
        self.next_voicing_button.clicked.connect(self._next_voicing)

    def _update_fretboard(self, *_args: object) -> None:
        """Re-evaluate the enabled layers for the current selection and redraw."""
        if self.root_selector.currentIndex() < 0 or self.scale_selector.currentIndex() < 0:
            return
        selected_id = self.tuning_selector.currentData()
        if selected_id is None and self._instrument_state.tuning_id is not None:
            self._snap_tuning_selector_to_preset()
            return
        if selected_id is not None and selected_id != self._instrument_state.tuning_id:
            self._instrument_state = instrument_from_tuning_id(
                selected_id,
                fret_count=self._instrument_state.fret_count,
            )
        self._sync_tuning_editor()
        fretboard = self._instrument_state.fretboard
        root = self._pitch_classes[self.root_selector.currentIndex()]
        named = self._scale_formulas[self.scale_selector.currentIndex()]
        quality = self._triad_qualities[self.triad_quality_selector.currentIndex()]
        mode = self._active_mode()
        if mode is not None and named.id != mode.id:
            # The scale changed away from the active mode's formula: the user
            # left modal context, so snap the mode/view selectors back to their
            # identity defaults and keep their newly chosen scale.
            self._leave_modal_context(keep_scale=True)
            mode = self._active_mode()
            named = self._scale_formulas[self.scale_selector.currentIndex()]
        effective_root = root
        modal_context: str | None = None
        selection: ModeSelection | None = None
        if mode is not None:
            view = self.view_selector.currentData() or ModeView.PARALLEL
            selection = evaluate_mode(root, mode, view)
            effective_root = selection.modal_root
            modal_context = self._modal_context_label(selection)
        try:
            annotations, groups = self._enabled_layer_data(
                fretboard, effective_root, named, quality
            )
        except (UnknownScaleFormulaError, InvalidScaleDegreeError) as exc:
            self.statusBar().showMessage(
                f"Could not evaluate {effective_root.spelling()} {named.name}: {exc}"
            )
            return
        self.statusBar().clearMessage()
        self.tuning_label.setText(
            f"Tuning: {self._instrument_state.display_name or self._instrument_state.tuning.name}"
        )
        self.selection_label.setText(
            self._selection_label(effective_root, named, quality, modal_context)
        )
        self.mode_label.setText(self._mode_readout(selection) if selection is not None else "")
        # Reset the active voicing only when the underlying triad result changed
        # (root, quality, or fretboard), so toggling layers preserves the user's
        # chosen voicing. While the triad layer is unchecked its result is not
        # evaluated, so keep the last evaluated groups rather than clobbering
        # them with the empty tuple.
        if self.layer_checkboxes["triad"].isChecked() and groups != self._triad_groups:
            self._triad_groups = groups
            self._active_voicing_index = 0
        self._apply_active_voicing()
        self.fretboard_widget.set_annotations(fretboard, annotations)

    def _toggle_tuning_editor(self) -> None:
        """Show or hide the compact custom-tuning editor."""
        self._tuning_editor_open = not self._tuning_editor_open
        self.tuning_editor.setVisible(self._tuning_editor_open)
        self.tuning_editor_button.setText(
            "Hide Tuning Editor" if self._tuning_editor_open else "Edit Tuning…"
        )

    def _snap_tuning_selector_to_preset(self) -> None:
        """Revert the selector to the active preset when Custom was picked idly.

        The ``Custom`` item only represents an applied custom tuning; selecting
        it without one would show a misleading selector state, so the selector
        snaps back to the active built-in preset.
        """
        assert self._instrument_state.tuning_id is not None
        preset_index = next(
            i
            for i, named in enumerate(self._tunings)
            if named.id == self._instrument_state.tuning_id
        )
        with QSignalBlocker(self.tuning_selector):
            self.tuning_selector.setCurrentIndex(preset_index)

    def _sync_tuning_editor(self) -> None:
        """Repopulate the editor when the tuning selector's item changes.

        Syncing is keyed to the selector item, so unrelated re-evaluations
        (root, scale, quality, layer toggles) never clobber in-progress edits.
        The ``Custom`` item leaves the editor untouched: it already reflects the
        active custom tuning.
        """
        index = self.tuning_selector.currentIndex()
        if index == self._editor_synced_index:
            return
        self._editor_synced_index = index
        if index == self._custom_tuning_index:
            return
        self._populate_string_editor()

    def _populate_string_editor(self) -> None:
        """Fill the editor from the active instrument's open-string pitches."""
        strings = sorted(self._instrument_state.tuning.strings, key=lambda string: -string.number)
        self.tuning_editor.set_pitches(tuple(string.open_pitch for string in strings))

    def _on_tuning_edited(self) -> None:
        """Report that the editor now holds a pending custom tuning."""
        self.statusBar().showMessage("Custom tuning edited — press Apply Tuning to use it")

    def _apply_custom_tuning(self) -> None:
        """Build a custom instrument state from the editor and activate it.

        On success the active state is replaced (``tuning_id=None``,
        ``display_name="Custom"``) while the fret count and every other
        selection are preserved, and the selector moves to the ``Custom`` item.
        The previous valid state stays active on any construction error.
        """
        try:
            state = instrument_from_string_pitches(
                self.tuning_editor.read_pitches(),
                fret_count=self._instrument_state.fret_count,
            )
        except (InvalidTuningError, InvalidPositionError) as exc:
            self.statusBar().showMessage(f"Could not apply tuning: {exc}")
            return
        self._instrument_state = state
        if self.tuning_selector.currentIndex() != self._custom_tuning_index:
            self.tuning_selector.setCurrentIndex(self._custom_tuning_index)
        else:
            self._update_fretboard()

    def _selection_label(
        self,
        root: PitchClass,
        named: NamedScaleFormula,
        quality: TriadQuality,
        modal_context: str | None,
    ) -> str:
        """Describe the visible workspace: root, then the enabled layers.

        ``root`` is the effective root (the modal root while a mode is active,
        otherwise the selector's root), because it defines the interval
        context for everything on the board. ``modal_context`` (e.g. ``"Dorian
        of C Major"``) replaces the plain scale name in the scale layer slot
        when a mode is active. A layer is only named while it is enabled,
        so the label never describes hidden content.
        """
        root_spelling = root.spelling()
        parts: list[str] = []
        if self.layer_checkboxes["scale"].isChecked():
            parts.append(modal_context if modal_context is not None else named.name)
        if self.layer_checkboxes["interval"].isChecked():
            parts.append("Intervals")
        if self.layer_checkboxes["triad"].isChecked():
            parts.append(f"{quality.display_name} Triads")
        if not parts:
            return f"{root_spelling} — No layers"
        return f"{root_spelling} {' · '.join(parts)}"

    def _active_mode(self) -> Mode | None:
        """The active mode, or ``None`` for the identity Ionian selection.

        Ionian is the inert default: it keeps the scale selector fully in
        charge, which is what preserves the pre-mode behavior.
        """
        mode = self.mode_selector.currentData()
        return None if mode is Mode.IONIAN else mode

    def _modal_context_label(self, selection: ModeSelection) -> str:
        """Describe the modal scale for the label's scale slot.

        The label prefix already carries the modal root, so the context starts
        at the mode name. Parallel: ``"Dorian"``. Relative: ``"Dorian of C
        Major"`` (the input root is the parent-major root).
        """
        if selection.view is ModeView.RELATIVE:
            return (
                f"{selection.mode.display_name} of "
                f"{selection.parent_major_root.spelling()} Major"
            )
        return selection.mode.display_name

    def _mode_readout(self, selection: ModeSelection) -> str:
        """The compact mode-information readout shown in :attr:`mode_label`.

        Surfaces the modal root, the parent-major root, and the
        characteristic alterations from Ionian, e.g.
        ``"D Dorian · Parent Major: C · Altered from Ionian: b3, b7"``.
        """
        altered = ", ".join(degree.label for degree in selection.altered_degrees_from_ionian)
        return (
            f"{selection.modal_root.spelling()} {selection.mode.display_name} · "
            f"Parent Major: {selection.parent_major_root.spelling()} · "
            f"Altered from Ionian: {altered}"
        )

    def _on_mode_changed(self, *_args: object) -> None:
        """Enter or leave modal context in response to the Mode selector.

        Selecting a non-Ionian mode mirrors its formula into the scale
        selector; returning to Ionian restores the previously selected scale
        and resets the view to Parallel.
        """
        mode = self.mode_selector.currentData()
        if mode is Mode.IONIAN:
            self._leave_modal_context(keep_scale=False)
        else:
            self._enter_modal_context(mode)
        self._update_fretboard()

    def _enter_modal_context(self, mode: Mode) -> None:
        """Activate ``mode``, mirroring its formula into the scale selector."""
        if self._scale_index_before_mode is None:
            self._scale_index_before_mode = self.scale_selector.currentIndex()
        formula_index = next(
            i for i, named in enumerate(self._scale_formulas) if named.id == mode.id
        )
        with QSignalBlocker(self.scale_selector):
            self.scale_selector.setCurrentIndex(formula_index)
        self._update_view_enabled()

    def _leave_modal_context(self, keep_scale: bool) -> None:
        """Deactivate modal context, snapping selectors to their defaults.

        With ``keep_scale=False`` the scale selector is restored to the
        selection it had before the mode was entered; with ``keep_scale=True``
        (the user changed the scale themselves) the user's scale is kept. The
        Mode selector returns to Ionian and the View selector to Parallel.
        """
        if not keep_scale and self._scale_index_before_mode is not None:
            with QSignalBlocker(self.scale_selector):
                self.scale_selector.setCurrentIndex(self._scale_index_before_mode)
        self._scale_index_before_mode = None
        with QSignalBlocker(self.mode_selector):
            self.mode_selector.setCurrentIndex(self._modes.index(Mode.IONIAN))
        with QSignalBlocker(self.view_selector):
            self.view_selector.setCurrentIndex(self._mode_views.index(ModeView.PARALLEL))
        self._update_view_enabled()

    def _update_view_enabled(self) -> None:
        """The View selector only applies while a non-Ionian mode is active."""
        self.view_selector.setEnabled(self._active_mode() is not None)

    def _enabled_layer_data(
        self,
        fretboard: Fretboard,
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
                scale_result = evaluate_scale(fretboard, root, named.id)
                annotations.extend(render_scale_result(scale_result))
            elif control.id == "interval":
                interval_result = evaluate_intervals(fretboard, root)
                annotations.extend(render_interval_result(interval_result))
            elif control.id == "triad":
                triad_result = evaluate_triad(fretboard, root, quality)
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
