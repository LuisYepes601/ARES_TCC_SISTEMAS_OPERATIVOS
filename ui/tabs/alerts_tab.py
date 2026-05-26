"""ui/tabs/alerts_tab.py — Alertas v3 tema claro."""
from __future__ import annotations
from PyQt6.QtCore  import Qt, QTimer
from PyQt6.QtGui   import QColor
from PyQt6.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)
from core.data.alerts_repository import Alert, AlertLevel
from core.services.alerts_service import (
    clear_alerts, dismiss_all_alerts, get_alerts, get_thresholds, update_thresholds,
)
from core.utils.formatters import timestamp_str

_LEVEL = {
    AlertLevel.INFO:     ("#2563eb", "#eff6ff", "#bfdbfe"),
    AlertLevel.WARNING:  ("#d97706", "#fffbeb", "#fde68a"),
    AlertLevel.CRITICAL: ("#dc2626", "#fef2f2", "#fecaca"),
}


class _AlertRow(QFrame):
    def __init__(self, alert: Alert, parent=None):
        super().__init__(parent)
        fg, bg, border = _LEVEL.get(alert.level, ("#6b7280","#f9fafb","#e5e7eb"))
        self.setStyleSheet(
            f"QFrame{{background:{bg};border:1.5px solid {border};"
            f"border-left:4px solid {fg};border-radius:8px;margin:2px 0;}}"
        )
        lay = QHBoxLayout(self); lay.setContentsMargins(14, 10, 14, 10)
        left = QVBoxLayout(); left.setSpacing(2)

        t = QLabel(alert.title)
        t.setStyleSheet(f"color:{fg};font-weight:700;font-size:10.5pt;")
        m = QLabel(alert.message)
        m.setStyleSheet("color:#374151;font-size:9.5pt;font-family:Consolas;")
        m.setWordWrap(True)
        ts = QLabel(timestamp_str(alert.timestamp))
        ts.setStyleSheet("color:#9ca3af;font-size:8.5pt;font-family:Consolas;")

        left.addWidget(t); left.addWidget(m); left.addWidget(ts)
        lay.addLayout(left, stretch=1)

        cat = QLabel(alert.category.upper())
        cat.setStyleSheet(
            f"color:{fg};background:{bg};border:1.5px solid {border};"
            f"border-radius:6px;padding:3px 10px;font-size:8.5pt;font-weight:700;"
        )
        lay.addWidget(cat)


class AlertsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2000)
        self.refresh()

    def pause_updates(self, p: bool) -> None:
        if p: self._timer.stop()
        elif not self._timer.isActive(): self._timer.start(2000)

    def _build_ui(self) -> None:
        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        spl  = QSplitter(Qt.Orientation.Horizontal)
        spl.setStyleSheet("QSplitter::handle{background:#e5e7eb;}")
        root.addWidget(spl)

        # ── Left: alert list ────────────────────────────────────────
        left = QWidget(); left.setStyleSheet("background:#f5f6fa;")
        ll   = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        hdr = QWidget(); hdr.setObjectName("TabHeader"); hdr.setFixedHeight(52)
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(18,0,18,0)
        t   = QLabel("Alerts"); t.setObjectName("PanelTitle")
        self._cnt = QLabel("—"); self._cnt.setObjectName("AlertCount")
        hl.addWidget(t); hl.addStretch(); hl.addWidget(self._cnt)
        ll.addWidget(hdr)

        abar = QWidget(); abar.setObjectName("ActionBar"); abar.setFixedHeight(44)
        al   = QHBoxLayout(abar); al.setContentsMargins(14,6,14,6); al.setSpacing(8)
        d_btn = QPushButton("✓  Dismiss all")
        d_btn.clicked.connect(self._dismiss)
        c_btn = QPushButton("🗑  Clear history")
        c_btn.clicked.connect(self._clear)
        al.addWidget(d_btn); al.addWidget(c_btn); al.addStretch()
        ll.addWidget(abar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background:#f5f6fa;")
        self._cont = QWidget(); self._cont.setStyleSheet("background:#f5f6fa;")
        self._cly  = QVBoxLayout(self._cont)
        self._cly.setContentsMargins(14,10,14,10); self._cly.setSpacing(6)
        self._cly.addStretch()
        self._scroll.setWidget(self._cont)
        ll.addWidget(self._scroll, stretch=1)
        spl.addWidget(left)

        # ── Right: thresholds ────────────────────────────────────────
        right = QWidget(); right.setStyleSheet("background:#ffffff;")
        rl    = QVBoxLayout(right); rl.setContentsMargins(16,16,16,16); rl.setSpacing(12)

        th = QLabel("Alert Thresholds"); th.setObjectName("PanelTitle")
        rl.addWidget(th)

        grp = QGroupBox("Configure thresholds")
        frm = QFormLayout(grp); frm.setSpacing(10); frm.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        t   = get_thresholds()
        self._spins: dict[str, QDoubleSpinBox] = {}
        for key, label, default in [
            ("cpu_warning",     "CPU — Warning (%)",      t.cpu_warning),
            ("cpu_critical",    "CPU — Critical (%)",     t.cpu_critical),
            ("memory_warning",  "Memory — Warning (%)",   t.memory_warning),
            ("memory_critical", "Memory — Critical (%)",  t.memory_critical),
            ("disk_warning",    "Disk — Warning (%)",     t.disk_warning),
            ("disk_critical",   "Disk — Critical (%)",    t.disk_critical),
            ("gpu_warning",     "GPU — Warning (%)",      t.gpu_warning),
            ("gpu_critical",    "GPU — Critical (%)",     t.gpu_critical),
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(1, 100); spin.setSingleStep(5)
            spin.setSuffix(" %"); spin.setValue(default)
            spin.setFixedHeight(32)
            self._spins[key] = spin
            frm.addRow(label, spin)
        rl.addWidget(grp)

        ap = QPushButton("✅  Apply thresholds")
        ap.setObjectName("ApplyButton"); ap.setFixedHeight(36)
        ap.clicked.connect(self._apply)
        rl.addWidget(ap)

        # legend
        leg = QGroupBox("Legend")
        leg_lay = QVBoxLayout(leg); leg_lay.setSpacing(8)
        for fg, bg, border, text in [
            ("#2563eb","#eff6ff","#bfdbfe","Information"),
            ("#d97706","#fffbeb","#fde68a","Warning"),
            ("#dc2626","#fef2f2","#fecaca","Critical"),
        ]:
            rw = QWidget()
            rl2 = QHBoxLayout(rw); rl2.setContentsMargins(0,0,0,0); rl2.setSpacing(8)
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{fg};font-size:14pt;")
            lbl = QLabel(text)
            lbl.setStyleSheet("color:#374151;font-size:10pt;font-weight:500;")
            rl2.addWidget(dot); rl2.addWidget(lbl); rl2.addStretch()
            leg_lay.addWidget(rw)
        rl.addWidget(leg)
        rl.addStretch()
        spl.addWidget(right)
        spl.setSizes([680, 320])

    def refresh(self) -> None:
        alerts = get_alerts()
        self._cnt.setText(f"{len(alerts)} active")
        while self._cly.count() > 1:
            item = self._cly.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        if not alerts:
            e = QLabel("  ✅  No active alerts — system is running normally")
            e.setObjectName("EmptyAlertsLabel")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cly.insertWidget(0, e)
        else:
            for a in alerts:
                self._cly.insertWidget(self._cly.count()-1, _AlertRow(a))

    def _dismiss(self): dismiss_all_alerts(); self.refresh()
    def _clear(self):   clear_alerts();       self.refresh()
    def _apply(self):   update_thresholds(**{k: w.value() for k,w in self._spins.items()})
