"""
Ares v3.0 — System Monitor
Entry point.
"""
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.styles.theme import apply_theme, saved_theme


def main():
    if sys.platform not in ("win32", "darwin"):
        print("Warning: Ares is optimised for Windows and macOS.", file=sys.stderr)

    app = QApplication(sys.argv)
    app.setApplicationName("Ares System Monitor")
    app.setApplicationVersion("3.0.0")
    app.setOrganizationName("Ares")

    apply_theme(app, saved_theme())

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
