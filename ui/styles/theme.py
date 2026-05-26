"""ui/styles/theme.py"""
from pathlib import Path
from PyQt6.QtCore    import QSettings
from PyQt6.QtWidgets import QApplication

ORG_NAME    = "Ares"
APP_NAME    = "AresMonitor"
THEME_KEY   = "appearance/theme"
THEME_LIGHT = "light"
THEME_DARK  = "dark"

_FILE = {
    THEME_LIGHT: "style_light.qss",
    THEME_DARK:  "style_dark.qss",
}


def _resources_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "resources"


def apply_theme(app: QApplication, theme: str) -> None:
    fname = _FILE.get(theme, "style_light.qss")
    path  = _resources_dir() / fname
    app.setStyleSheet(path.read_text(encoding="utf-8") if path.exists() else "")


def saved_theme() -> str:
    raw = QSettings(ORG_NAME, APP_NAME).value(THEME_KEY, THEME_LIGHT)   # light por defecto
    s   = raw if isinstance(raw, str) else str(raw)
    return s if s in (THEME_LIGHT, THEME_DARK) else THEME_LIGHT


def persist_theme(theme: str) -> None:
    QSettings(ORG_NAME, APP_NAME).setValue(THEME_KEY, theme)
