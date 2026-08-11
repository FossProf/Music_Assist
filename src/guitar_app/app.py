"""Desktop application entry point (PySide6).

Run with ``python -m guitar_app.app`` or the ``guitar-app`` console script.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from guitar_app.ui.main_window import MainWindow


def main() -> int:
    """Launch the desktop application and return its exit code."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
