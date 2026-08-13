"""Shared UI color palette for fretboard painting and the legend.

The fretboard widget and the legend both need the exact marker colors, so the
constants live in one Qt-dependent module instead of being redefined. Like
``ui.fretboard_widget`` this module uses PySide6 colors and must never be
imported by the Qt-free theory, core, or services layers.
"""

from __future__ import annotations

from PySide6.QtGui import QColor

BACKGROUND_COLOR = QColor("#ffffff")
NUT_COLOR = QColor("#2b2b2b")
FRET_COLOR = QColor("#c9c9c9")
STRING_COLOR = QColor("#8a8a8a")
MARKER_COLOR = QColor("#d9d9d9")
TONIC_FILL = QColor("#1f6fb2")
TONIC_TEXT = QColor("#ffffff")
DEGREE_FILL = QColor("#c5dcf0")
DEGREE_TEXT = QColor("#1a3550")
OPEN_PEN = QColor("#1f6fb2")
INTERVAL_FILL = QColor("#f2e4d0")
INTERVAL_TEXT = QColor("#5a4632")
INTERVAL_OUTLINE = QColor("#b9a082")
INTERVAL_ROOT_FILL = QColor("#b26a1f")
INTERVAL_ROOT_TEXT = QColor("#ffffff")
BADGE_FILL = QColor("#ffffff")
BADGE_TEXT = QColor("#4a3f33")
BADGE_OUTLINE = QColor("#8a7a6a")
TRIAD_FILL = QColor("#7db87d")
TRIAD_TEXT = QColor("#1d3a1d")
TRIAD_OUTLINE = QColor("#5a8f5a")
TRIAD_ROOT_FILL = QColor("#2f7d32")
TRIAD_ROOT_TEXT = QColor("#ffffff")
VOICING_GROUP_PEN = QColor("#4d8f4d")
VOICING_GROUP_FILL = QColor(70, 130, 70, 36)
