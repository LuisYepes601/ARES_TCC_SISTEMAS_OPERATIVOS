"""ui/tabs/services_tab.py — Servicios Windows v3 tema claro."""
import os
from PyQt6.QtGui   import QColor, QFont
from PyQt6.QtCore  import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from core.services.services_service import get_services, start_service, stop_service
from core.utils.formatters import service_status_label, service_status_color

MONO = QFont("Consolas", 9); MONO.setStyleHint(QFont.StyleHint.Monospace)


class ServicesTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)

        hdr = QWidget(); hdr.setObjectName("TabHeader"); hdr.setFixedHeight(52)
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(18,0,18,0); hl.setSpacing(10)
        t   = QLabel("Services"); t.setObjectName("PanelTitle")
        hl.addWidget(t); hl.addStretch()

        if os.name != "nt":
            info = QLabel("  Services management is available on Windows only.")
            info.setStyleSheet("color:#9ca3af;font-size:10pt;padding:24px;")
            lay.addWidget(hdr); lay.addWidget(info); return

        for lbl, fn in [
            ("↻  Refresh", self.refresh),
            ("▶  Start",   self._start),
            ("⏹  Stop",    self._stop),
        ]:
            btn = QPushButton(lbl); btn.clicked.connect(fn)
            hl.addWidget(btn)
        lay.addWidget(hdr)

        # action bar
        abar = QWidget(); abar.setObjectName("ActionBar"); abar.setFixedHeight(36)
        al   = QHBoxLayout(abar); al.setContentsMargins(14,4,14,4)
        note = QLabel("⚠  Requires Administrator privileges to start/stop services")
        note.setStyleSheet("color:#d97706;font-size:9pt;font-weight:500;")
        al.addWidget(note); al.addStretch()
        lay.addWidget(abar)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Service name", "Display name", "Status"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 220); self.table.setColumnWidth(2, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("QTableWidget{border:none;border-radius:0;}")
        lay.addWidget(self.table, stretch=1)
        self.refresh()

    def refresh(self) -> None:
        if os.name != "nt": return
        svcs = get_services()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(svcs))
        for row, s in enumerate(svcs):
            self.table.setRowHeight(row, 26)
            for col, text in enumerate([s["name"], s["display_name"], service_status_label(s["status"])]):
                item = QTableWidgetItem(text)
                item.setFont(MONO)
                if col == 2:
                    item.setForeground(QColor(service_status_color(s["status"])))
                    f = item.font(); f.setBold(True); item.setFont(f)
                elif col == 0:
                    item.setForeground(QColor("#374151"))
                else:
                    item.setForeground(QColor("#6b7280"))
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

    def _selected_name(self):
        row  = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.text().strip() if item else None

    def _start(self):
        name = self._selected_name()
        if not name: QMessageBox.warning(self, "Start", "Select a service first."); return
        ok, msg = start_service(name)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Start service", msg)
        if ok: self.refresh()

    def _stop(self):
        name = self._selected_name()
        if not name: QMessageBox.warning(self, "Stop", "Select a service first."); return
        r = QMessageBox.question(self, "Confirm", f'Stop service "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes: return
        ok, msg = stop_service(name)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Stop service", msg)
        if ok: self.refresh()
