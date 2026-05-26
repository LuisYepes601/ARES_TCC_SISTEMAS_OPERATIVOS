"""ui/tabs/network_tab.py — Red v3 tema claro."""
from __future__ import annotations
from PyQt6.QtCore  import Qt, QTimer
from PyQt6.QtGui   import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from core.services.system_service import (
    get_connections, get_network_io, get_network_io_per_interface,
)
from core.utils.formatters import bytes_to_mb, bytes_per_sec_human, connection_status_label

MONO = QFont("Consolas", 9); MONO.setStyleHint(QFont.StyleHint.Monospace)

_STATUS_COLOR = {
    "ESTABLISHED": "#16a34a", "LISTEN": "#2563eb", "LISTENING": "#2563eb",
    "TIME_WAIT": "#d97706",   "CLOSE_WAIT": "#dc2626", "SYN_SENT": "#7c3aed",
}


class NetworkTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(3000)
        self.refresh()

    def pause_updates(self, p: bool) -> None:
        if p: self._timer.stop()
        elif not self._timer.isActive(): self._timer.start(3000)

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        # header
        hdr = QWidget(); hdr.setObjectName("TabHeader"); hdr.setFixedHeight(52)
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(18,0,18,0); hl.setSpacing(12)
        t   = QLabel("Network"); t.setObjectName("PanelTitle")
        self._io_lbl = QLabel("—")
        self._io_lbl.setStyleSheet(
            "color:#6b7280;font-size:10pt;font-family:Consolas;font-weight:600;"
        )
        btn = QPushButton("↻  Refresh"); btn.clicked.connect(self.refresh)
        hl.addWidget(t); hl.addStretch(); hl.addWidget(self._io_lbl); hl.addSpacing(12); hl.addWidget(btn)
        lay.addWidget(hdr)

        # per-interface strip
        iface_container = QWidget()
        iface_container.setStyleSheet(
            "background:#f9fafb;border-bottom:1px solid #e5e7eb;"
        )
        iface_container.setFixedHeight(62)
        self._iface_lay = QHBoxLayout(iface_container)
        self._iface_lay.setContentsMargins(16,8,16,8)
        self._iface_lay.setSpacing(24)
        lay.addWidget(iface_container)

        # section header
        sh = QLabel("  ACTIVE CONNECTIONS  (IPv4)")
        sh.setStyleSheet(
            "color:#9ca3af;font-size:8.5pt;font-weight:700;letter-spacing:1px;"
            "background:#fafafa;border-bottom:1px solid #e5e7eb;padding:6px 14px;"
        )
        lay.addWidget(sh)

        # table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Local address", "Remote address", "Status", "Type", "PID"]
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(2, 140); self.table.setColumnWidth(3, 64); self.table.setColumnWidth(4, 64)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("QTableWidget{border:none;border-radius:0;}")
        lay.addWidget(self.table, stretch=1)

    def refresh(self) -> None:
        sent, recv = get_network_io()
        self._io_lbl.setText(f"Total  ↑ {bytes_to_mb(sent)}   ↓ {bytes_to_mb(recv)}")

        # per-interface
        ifaces = get_network_io_per_interface()
        while self._iface_lay.count():
            item = self._iface_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for name, ctr in list(ifaces.items())[:10]:
            w  = QWidget(); w.setStyleSheet("background:transparent;")
            wl = QVBoxLayout(w); wl.setContentsMargins(0,0,0,0); wl.setSpacing(1)
            n  = QLabel(name)
            n.setStyleSheet("color:#6b7280;font-size:8pt;font-weight:700;letter-spacing:0.5px;")
            vs = bytes_to_mb(ctr["bytes_sent"]); vr = bytes_to_mb(ctr["bytes_recv"])
            v  = QLabel(f"↑{vs}  ↓{vr}")
            v.setStyleSheet(
                "color:#374151;font-size:9pt;font-family:Consolas;font-weight:600;"
            )
            wl.addWidget(n); wl.addWidget(v)
            self._iface_lay.addWidget(w)
        self._iface_lay.addStretch()

        # connections
        try:
            conns = get_connections("inet")
            self.table.setSortingEnabled(False)
            self.table.setRowCount(len(conns))
            for row, c in enumerate(conns):
                self.table.setRowHeight(row, 26)
                raw = str(c["status"]).upper().replace("—","")
                col = _STATUS_COLOR.get(raw, "#6b7280")
                for ci, text in enumerate([
                    c["laddr"], c["raddr"],
                    connection_status_label(str(c["status"])),
                    c.get("type","IPv4"), str(c["pid"]),
                ]):
                    item = QTableWidgetItem(str(text))
                    item.setFont(MONO)
                    if ci == 2:
                        item.setForeground(QColor(col))
                        f = item.font(); f.setBold(True); item.setFont(f)
                    elif ci in (0,1):
                        item.setForeground(QColor("#374151"))
                    else:
                        item.setForeground(QColor("#9ca3af"))
                    self.table.setItem(row, ci, item)
            self.table.setSortingEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, "Network", f"Could not load connections:\n{e}")
