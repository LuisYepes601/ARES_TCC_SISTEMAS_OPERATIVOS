"""ui/main_window.py — Ventana principal Ares v3 tema claro."""
from __future__ import annotations
import os
from PyQt6.QtCore  import Qt, QTimer
from PyQt6.QtGui   import QAction, QActionGroup, QFont
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFrame,
    QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from core.services.alerts_service import get_active_count
from core.services.system_service  import get_cpu_percent, get_disk_info, get_memory_info, get_system_health_score
from core.utils.formatters          import pct_to_status_color, health_color
from core.workers.data_worker       import DataWorker
from ui.styles.theme import THEME_DARK, THEME_LIGHT, apply_theme, persist_theme, saved_theme
from ui.tabs.processes_tab   import ProcessesTab
from ui.tabs.performance_tab import PerformanceTab
from ui.tabs.network_tab     import NetworkTab
from ui.tabs.system_tab      import SystemTab
from ui.tabs.alerts_tab      import AlertsTab


# ── Status bar ────────────────────────────────────────────────────────

class TopStatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(28)
        self._cpu  = self._lbl("CPU  —")
        self._mem  = self._lbl("MEM  —")
        self._disk = self._lbl("DISK  —")
        self._hlth = self._lbl("HEALTH  —", bold=True)
        self._uptime = self._lbl("—")
        for w in (self._cpu, self._mem, self._disk):
            lay.addWidget(w)
        lay.addStretch()
        lay.addWidget(self._uptime)
        lay.addWidget(self._hlth)

    def _lbl(self, t, bold=False):
        l = QLabel(t)
        l.setObjectName("StatusBarLabel")
        if bold:
            f = l.font(); f.setBold(True); l.setFont(f)
        return l

    def update(self, d: dict) -> None:
        def span(v, txt):
            c = pct_to_status_color(v)
            return (
                f'<span style="color:{c};font-family:Consolas,monospace;'
                f'font-weight:700;font-size:10pt">{txt}</span>'
            )
        cpu  = d.get("cpu", 0)
        mem  = d.get("mem_pct", 0)
        disk = d.get("disk_pct", 0)
        h    = d.get("health", 0)
        hc   = health_color(h)

        self._cpu.setText(f'CPU  {span(cpu,  f"{cpu:.0f}%")}')
        self._mem.setText(f'MEM  {span(mem,  f"{mem:.0f}%")}')
        self._disk.setText(f'DISK  {span(disk, f"{disk:.0f}%")}')
        self._uptime.setText(
            f'<span style="color:#9ca3af;font-family:Consolas;font-size:9.5pt">'
            f'{d.get("uptime","—")}</span>'
        )
        self._hlth.setText(
            f'HEALTH  <span style="color:{hc};font-family:Consolas;'
            f'font-weight:700;font-size:10pt">{h:.0f}<span style="color:#d1d5db">/100</span>'
            f'  {d.get("health_desc","—")}</span>'
        )
        for lbl in (self._cpu, self._mem, self._disk, self._uptime, self._hlth):
            lbl.setTextFormat(Qt.TextFormat.RichText)


# ── Nav button ─────────────────────────────────────────────────────────

class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._icon  = icon
        self._label = label
        self._badge = 0
        self._render()

    def set_badge(self, n: int) -> None:
        self._badge = n; self._render()

    def _render(self) -> None:
        badge = f"  ·  {self._badge}" if self._badge else ""
        self.setText(f"{self._icon}  {self._label}{badge}")


# ── Main window ───────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ares  ·  System Monitor")
        self.setMinimumSize(1060, 660)
        self.resize(1320, 780)

        self._worker = DataWorker(system_interval=1.0, process_interval=3.0)
        self._build_menu()
        self._build_ui()
        self._worker.system_ready.connect(self._on_system)

        self._worker.start()

        self._badge_timer = QTimer(self)
        self._badge_timer.timeout.connect(self._refresh_badge)
        self._badge_timer.start(2000)

    # ─────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        vlay = QVBoxLayout(root); vlay.setContentsMargins(0,0,0,0); vlay.setSpacing(0)

        # status bar
        self._sbar = TopStatusBar()
        self._sbar.setObjectName("TopStatusBar")
        vlay.addWidget(self._sbar)

        sep = QWidget(); sep.setFixedHeight(2); sep.setObjectName("StatusSeparator")
        vlay.addWidget(sep)

        # body
        body = QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)
        vlay.addLayout(body, stretch=1)

        # ── Sidebar ──────────────────────────────────────────────────
        sb = QWidget(); sb.setFixedWidth(190); sb.setObjectName("Sidebar")
        sl = QVBoxLayout(sb); sl.setContentsMargins(10,22,10,16); sl.setSpacing(3)

        title = QLabel("ARES")
        title.setObjectName("SidebarTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("v3.0  ·  System Monitor")
        sub.setObjectName("SidebarSubtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(title); sl.addWidget(sub); sl.addSpacing(20)

        nav_items = [
            ("⚡", "Processes"),
            ("📊", "Performance"),
            ("🌐", "Network"),
            ("🖥", "System"),
            ("🔔", "Alerts"),
        ]
        if os.name == "nt":
            nav_items.insert(4, ("⚙", "Services"))

        self._nav_btns: list[NavButton] = []
        for icon, label in nav_items:
            btn = NavButton(icon, label)
            btn.setObjectName("NavButton")
            btn.clicked.connect(lambda _, l=label: self._go(l))
            sl.addWidget(btn)
            self._nav_btns.append(btn)

        sl.addStretch()

        # uptime in sidebar
        self._up_lbl = QLabel("—")
        self._up_lbl.setObjectName("SidebarUptime")
        self._up_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(self._up_lbl)

        body.addWidget(sb)

        vsep = QFrame(); vsep.setObjectName("VSep"); vsep.setFixedWidth(1)
        body.addWidget(vsep)

        # Stack
        self._stack = QStackedWidget(); self._stack.setObjectName("ContentStack")
        body.addWidget(self._stack, stretch=1)

        self._pages: dict[str, QWidget] = {}
        self._perf_tab  = PerformanceTab(self._worker)
        self._procs_tab = ProcessesTab(self._worker)

        page_map = [
            ("Processes",   self._procs_tab),
            ("Performance", self._perf_tab),
            ("Network",     NetworkTab()),
            ("System",      SystemTab()),
            ("Alerts",      AlertsTab()),
        ]
        if os.name == "nt":
            from ui.tabs.services_tab import ServicesTab
            page_map.insert(4, ("Services", ServicesTab()))

        for name, widget in page_map:
            self._stack.addWidget(widget)
            self._pages[name] = widget

        self._go("Processes")

    # ─────────────────────────────────────────────────────────────────
    def _on_system(self, d: dict) -> None:
        self._sbar.update(d)
        self._up_lbl.setText(d.get("uptime", "—"))

    def _go(self, name: str) -> None:
        w = self._pages.get(name)
        if not w: return
        for pname, pw in self._pages.items():
            if hasattr(pw, "pause_updates"):
                pw.pause_updates(pname != name)
        self._stack.setCurrentWidget(w)
        for btn in self._nav_btns:
            btn.setChecked(btn._label == name)

    def _refresh_badge(self) -> None:
        n = get_active_count()
        for btn in self._nav_btns:
            if btn._label == "Alerts":
                btn.set_badge(n)

    # ─────────────────────────────────────────────────────────────────
    def _build_menu(self) -> None:
        mb  = self.menuBar()
        app = mb.addMenu("Ares")

        appear = app.addMenu("Appearance")
        grp    = QActionGroup(self); grp.setExclusive(True)
        self._a_light = QAction("☀  Light mode", self, checkable=True)
        self._a_dark  = QAction("🌙  Dark mode",  self, checkable=True)
        grp.addAction(self._a_light); grp.addAction(self._a_dark)
        appear.addAction(self._a_light); appear.addAction(self._a_dark)
        self._a_light.triggered.connect(lambda: self._set_theme(THEME_LIGHT))
        self._a_dark.triggered.connect(lambda:  self._set_theme(THEME_DARK))
        cur = saved_theme()
        self._a_light.setChecked(cur == THEME_LIGHT)
        self._a_dark.setChecked(cur  == THEME_DARK)

        app.addSeparator()
        ab = QAction("About Ares…", self)
        ab.triggered.connect(self._about)
        app.addAction(ab)

    def _set_theme(self, theme: str) -> None:
        a = QApplication.instance()
        if a: apply_theme(a, theme); persist_theme(theme)
        self._a_light.setChecked(theme == THEME_LIGHT)
        self._a_dark.setChecked(theme == THEME_DARK)

    def _about(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self, "Ares v3.0 — System Monitor",
            "<b>Ares v3.0</b><br><br>"
            "Professional system monitor — Windows &amp; macOS<br><br>"
            "• Non-blocking background data collection (1 Hz)<br>"
            "• Real-time graphs: CPU, Memory, Disk, Network, GPU<br>"
            "• Per-core CPU usage and frequency<br>"
            "• Full process management: kill, kill tree,<br>"
            "  &nbsp;&nbsp;suspend, resume, priority, details, CSV export<br>"
            "• Smart alert system with configurable thresholds<br>"
            "• Disk I/O and network per-interface stats<br><br>"
            "License: MIT"
        )

    def closeEvent(self, event) -> None:
        self._worker.stop()
        super().closeEvent(event)
