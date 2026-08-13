"""A compact per-string pitch editor for building custom tunings."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from guitar_app.core.theory.pitch import Pitch, PitchClass

#: Scientific-pitch octave range offered by the editor.
OCTAVE_MIN = 0
OCTAVE_MAX = 8


class CustomTuningEditor(QWidget):
    """A compact editor for the open-string pitches of a custom tuning.

    Each existing string gets a row with its conventional number, a pitch-class
    selector, and an octave selector — never raw MIDI numbers. Rows run top to
    bottom from the conventional lowest string (string ``N``) to the highest
    (string 1); pitches are exposed low → high, matching
    :func:`guitar_app.services.instrument_state.instrument_from_string_pitches`.

    Editing is pending by design: the editor only reports changes and never
    builds an :class:`InstrumentState` itself. The owning window reads the
    pitches on ``apply_requested`` and applies the resulting custom tuning.
    """

    edited = Signal()
    apply_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[tuple[int, QLabel, QComboBox, QSpinBox]] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(QLabel("Custom tuning — edit open-string pitches (low → high)"))
        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(6)
        layout.addLayout(self._grid)
        self.apply_button = QPushButton("Apply Tuning")
        self.apply_button.clicked.connect(self.apply_requested)
        layout.addWidget(self.apply_button)

    def string_numbers(self) -> tuple[int, ...]:
        """The string number of each row, top to bottom (``N`` … ``1``)."""
        return tuple(number for number, _, _, _ in self._rows)

    @property
    def pitch_class_combos(self) -> tuple[QComboBox, ...]:
        """The pitch-class selector of each row, top to bottom."""
        return tuple(combo for _, _, combo, _ in self._rows)

    @property
    def octave_spins(self) -> tuple[QSpinBox, ...]:
        """The octave selector of each row, top to bottom."""
        return tuple(spin for _, _, _, spin in self._rows)

    def set_pitches(self, pitches: tuple[Pitch, ...]) -> None:
        """Replace every row's values from low-to-high ``pitches``.

        Rebuilds the rows when the string count changes. No ``edited`` signal
        is emitted, so programmatic syncing never marks a pending edit.
        """
        count = len(pitches)
        if count != len(self._rows):
            self._rebuild_rows(count)
        for (_, _, combo, spin), pitch in zip(self._rows, pitches, strict=True):
            with QSignalBlocker(combo):
                combo.setCurrentIndex(combo.findData(int(pitch.pitch_class)))
            with QSignalBlocker(spin):
                spin.setValue(pitch.octave)

    def read_pitches(self) -> tuple[Pitch, ...]:
        """Return the current per-string pitches, ordered low → high."""
        return tuple(
            Pitch(PitchClass(combo.currentData()), spin.value()) for _, _, combo, spin in self._rows
        )

    def set_string_pitch(self, string_number: int, pitch: Pitch) -> None:
        """Set one string's pitch and emit ``edited`` (a user-style edit)."""
        combo, spin = self._controls_for(string_number)
        with QSignalBlocker(combo):
            combo.setCurrentIndex(combo.findData(int(pitch.pitch_class)))
        with QSignalBlocker(spin):
            spin.setValue(pitch.octave)
        self.edited.emit()

    def pitch_for_string(self, string_number: int) -> Pitch:
        """Return the current pitch of one string."""
        combo, spin = self._controls_for(string_number)
        return Pitch(PitchClass(combo.currentData()), spin.value())

    def _controls_for(self, string_number: int) -> tuple[QComboBox, QSpinBox]:
        for number, _, combo, spin in self._rows:
            if number == string_number:
                return combo, spin
        raise ValueError(f"no editor row for string {string_number}")

    def _rebuild_rows(self, count: int) -> None:
        for _, label, combo, spin in self._rows:
            for widget in (label, combo, spin):
                self._grid.removeWidget(widget)
                widget.deleteLater()
        self._rows.clear()
        for index, number in enumerate(range(count, 0, -1)):
            label = QLabel(f"String {number}")
            combo = QComboBox()
            for pitch_class in PitchClass:
                combo.addItem(pitch_class.spelling(), int(pitch_class))
            spin = QSpinBox()
            spin.setRange(OCTAVE_MIN, OCTAVE_MAX)
            combo.currentIndexChanged.connect(self._emit_edited)
            spin.valueChanged.connect(self._emit_edited)
            self._grid.addWidget(label, index, 0)
            self._grid.addWidget(combo, index, 1)
            self._grid.addWidget(spin, index, 2)
            self._rows.append((number, label, combo, spin))

    def _emit_edited(self, *_args: object) -> None:
        self.edited.emit()
