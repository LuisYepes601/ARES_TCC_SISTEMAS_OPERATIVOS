"""
ui/tabs/processes_tab.py
Pestaña de Procesos v3 — gestor completo con todas las acciones.

Columnas: Icono | PID | Nombre | CPU% | ▬ barra | Mem% | RSS MB | Hilos | Estado | Prioridad
Acciones disponibles:
  • Finalizar (SIGTERM)          • Matar árbol completo (SIGKILL recursivo)
  • Suspender / Reanudar         • Cambiar prioridad (5 niveles)
  • Ver detalles completos        • Abrir ubicación del ejecutable
  • Exportar lista a CSV          • Buscar en Google (nombre del proceso)
  • Copiar PID / nombre al clipboard
"""
from __future__ import annotations
import os
import subprocess
import sys
import webbrowser
from datetime import datetime

from PyQt6.QtCore  import Qt, QTimer, pyqtSlot
from PyQt6.QtGui   import QColor, QFont, QFontMetrics, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFrame, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import QUrl

from core.services.process_service import (
    change_priority, export_processes_csv, get_priority_options,
    get_process_details, get_process_exe_path,
    kill_process, kill_process_and_children,
    open_process_folder, resume, suspend,
)
from core.services.alerts_service import add_process_alert
from core.utils.formatters import (
    PROCESS_FILTER_KEYS, nice_to_label,
    process_status_color, process_status_label,
    seconds_to_human, timestamp_str,
)
from ui.widgets.process_icon import icon_for_exe

MONO   = QFont("Consolas", 9)
MONO.setStyleHint(QFont.StyleHint.Monospace)
MONO_S = QFont("Consolas", 8)
MONO_S.setStyleHint(QFont.StyleHint.Monospace)


# ── helpers ──────────────────────────────────────────────────────────

def _cpu_bg(v: float) -> QColor:
    if v >= 80: return QColor("#fef2f2")
    if v >= 40: return QColor("#fffbeb")
    return QColor("transparent")

def _cpu_fg(v: float) -> QColor:
    if v >= 80: return QColor("#dc2626")
    if v >= 40: return QColor("#d97706")
    if v >= 10: return QColor("#4f46e5")
    return QColor("#9ca3af")

def _mem_fg(v: float) -> QColor:
    if v >= 20: return QColor("#7c3aed")
    if v >= 5:  return QColor("#6366f1")
    return QColor("#a5b4fc")

def _status_fg(raw: str) -> QColor:
    return QColor(process_status_color(raw))

def _ascii_bar(v: float, width: int = 12) -> str:
    filled = round(min(100, max(0, v)) / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ── Detail panel (side panel) ────────────────────────────────────────

class DetailPanel(QFrame):
    """Panel lateral que muestra detalles del proceso seleccionado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoCard")
        self.setMinimumWidth(240)
        self.setMaximumWidth(300)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        title_row = QHBoxLayout()
        self._title = QLabel("Select a process")
        self._title.setStyleSheet("font-size:11pt;font-weight:700;color:#111827;")
        self._title.setWordWrap(True)
        title_row.addWidget(self._title)
        lay.addLayout(title_row)

        self._pid_lbl = QLabel("")
        self._pid_lbl.setStyleSheet("color:#9ca3af;font-family:Consolas;font-size:9pt;")
        lay.addWidget(self._pid_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#e5e7eb;margin:4px 0;")
        lay.addWidget(sep)

        self._rows: dict[str, QLabel] = {}
        for key, label in [
            ("status",   "Status"),
            ("cpu",      "CPU"),
            ("mem_pct",  "Memory %"),
            ("mem_rss",  "RSS"),
            ("mem_vms",  "VMS"),
            ("threads",  "Threads"),
            ("children", "Children"),
            ("user",     "User"),
            ("nice",     "Priority"),
            ("uptime",   "Running for"),
            ("cmdline",  "Command"),
        ]:
            row = QWidget()
            row.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row); rl.setContentsMargins(0, 2, 0, 2); rl.setSpacing(6)
            lk = QLabel(label)
            lk.setFixedWidth(82)
            lk.setStyleSheet("color:#9ca3af;font-size:9pt;")
            lv = QLabel("—")
            lv.setStyleSheet("color:#374151;font-size:9.5pt;font-weight:600;font-family:Consolas;")
            lv.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lv.setWordWrap(True)
            rl.addWidget(lk); rl.addWidget(lv, stretch=1)
            lay.addWidget(row)
            self._rows[key] = lv

        lay.addStretch()

        # quick actions inside panel
        lay.addWidget(QLabel("Quick actions").setStyleSheet if False else QLabel(""))
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color:#e5e7eb;margin:2px 0;")
        lay.addWidget(sep2)

        for lbl, obj_name, tip in [
            ("⏸  Suspend",  "WarnButton",   "Pause process"),
            ("▶  Resume",   "InfoButton",   "Continue process"),
            ("✕  Kill",     "DangerButton", "Terminate (SIGTERM)"),
            ("✕✕ Kill Tree","DangerButton", "Kill process + all children"),
        ]:
            btn = QPushButton(lbl)
            btn.setObjectName(obj_name)
            btn.setToolTip(tip)
            btn.setFixedHeight(32)
            btn.setProperty("action", lbl.strip())
            lay.addWidget(btn)
            # store references
            setattr(self, f"_btn_{lbl.split()[0].strip('✕▶⏸').lower() or lbl[:4].strip()}", btn)

        self._btn_suspend = lay.itemAt(lay.count() - 4).widget()
        self._btn_resume  = lay.itemAt(lay.count() - 3).widget()
        self._btn_kill    = lay.itemAt(lay.count() - 2).widget()
        self._btn_ktree   = lay.itemAt(lay.count() - 1).widget()

    def update_info(self, p: dict | None, details: dict | None = None) -> None:
        if not p:
            self._title.setText("Select a process")
            self._pid_lbl.setText("")
            for v in self._rows.values(): v.setText("—")
            return

        self._title.setText(p.get("name", "?"))
        self._pid_lbl.setText(f"PID  {p.get('pid','?')}")

        cpu = p.get("cpu", 0)
        mem = p.get("memory", 0)
        self._rows["status"].setText(process_status_label(p.get("status","")))
        self._rows["cpu"].setText(f"{cpu:.1f}%")
        self._rows["cpu"].setStyleSheet(
            f"color:{_cpu_fg(cpu).name()};font-size:9.5pt;font-weight:700;font-family:Consolas;"
        )
        self._rows["mem_pct"].setText(f"{mem:.2f}%")
        self._rows["threads"].setText(str(p.get("threads", "—")))
        self._rows["nice"].setText(nice_to_label(p.get("nice", 0) or 0))

        if details:
            self._rows["mem_rss"].setText(f"{details.get('mem_rss_mb',0):.1f} MB")
            self._rows["mem_vms"].setText(f"{details.get('mem_vms_mb',0):.1f} MB")
            self._rows["children"].setText(str(len(details.get("children", []))))
            self._rows["user"].setText(str(details.get("username", "—")))
            cmdline = str(details.get("cmdline", "—"))
            self._rows["cmdline"].setText(cmdline[:60] + "…" if len(cmdline) > 60 else cmdline)
            import time
            ct = details.get("create_time")
            if ct:
                elapsed = time.time() - ct
                self._rows["uptime"].setText(seconds_to_human(elapsed))
        else:
            for k in ("mem_rss","mem_vms","children","user","cmdline","uptime"):
                self._rows[k].setText("—")


# ── Main processes tab ───────────────────────────────────────────────

class ProcessesTab(QWidget):
    def __init__(self, worker=None):
        super().__init__()
        self._worker  = worker
        self._cache   : dict[int, dict] = {}
        self._paused  = False
        self._selected_pid: int | None  = None

        self._build_ui()

        if worker:
            worker.process_ready.connect(self._on_processes)

    # ─────────────────────────────────────────────────────────────────
    def pause_updates(self, p: bool) -> None:
        self._paused = p
        self.table.setUpdatesEnabled(not p)

    # ─────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────
        hdr = QWidget(); hdr.setObjectName("TabHeader"); hdr.setFixedHeight(52)
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(18, 0, 18, 0); hl.setSpacing(12)

        t = QLabel("Processes"); t.setObjectName("PanelTitle")
        hl.addWidget(t)
        hl.addStretch()

        self._count_lbl = QLabel("—")
        self._count_lbl.setObjectName("ProcessCount")
        hl.addWidget(self._count_lbl)
        root.addWidget(hdr)

        # ── Filter bar ──────────────────────────────────────────────
        fbar = QWidget(); fbar.setObjectName("FilterBar"); fbar.setFixedHeight(48)
        fl   = QHBoxLayout(fbar); fl.setContentsMargins(14, 6, 14, 6); fl.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Filter by name…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(240)
        self.search.textChanged.connect(self._filter)

        self.cpu_spin = QSpinBox()
        self.cpu_spin.setRange(0, 100); self.cpu_spin.setSuffix("%")
        self.cpu_spin.setPrefix("CPU > "); self.cpu_spin.setFixedWidth(110)
        self.cpu_spin.valueChanged.connect(self._filter)

        self.mem_spin = QSpinBox()
        self.mem_spin.setRange(0, 100); self.mem_spin.setSuffix("%")
        self.mem_spin.setPrefix("Mem > "); self.mem_spin.setFixedWidth(110)
        self.mem_spin.valueChanged.connect(self._filter)

        self.status_cb = QComboBox()
        self.status_cb.setFixedWidth(130)
        self.status_cb.addItem("All states", None)
        for k in PROCESS_FILTER_KEYS:
            self.status_cb.addItem(process_status_label(k), k)
        self.status_cb.currentIndexChanged.connect(self._filter)

        fl.addWidget(self.search)
        fl.addWidget(self.cpu_spin)
        fl.addWidget(self.mem_spin)
        fl.addWidget(self.status_cb)
        fl.addStretch()
        root.addWidget(fbar)

        # ── Action bar ──────────────────────────────────────────────
        abar = QWidget(); abar.setObjectName("ActionBar"); abar.setFixedHeight(44)
        al   = QHBoxLayout(abar); al.setContentsMargins(14, 4, 14, 4); al.setSpacing(6)

        actions = [
            ("⏸  Suspend",    "WarnButton",   self._suspend,       "Suspend selected process"),
            ("▶  Resume",     "InfoButton",   self._resume,        "Resume suspended process"),
            ("✕  Kill",       "DangerButton", self._kill,          "Terminate process (SIGTERM)"),
            ("✕✕ Kill Tree",  "DangerButton", self._kill_tree,     "Kill process and all children"),
            ("↑  Priority",   "",             self._change_prio,   "Change process priority"),
            ("📁 Location",   "",             self._open_folder,   "Open executable location"),
            ("🔍 Details",    "",             self._details,       "View full process details"),
            ("⬇  Export CSV", "",             self._export,        "Export full process list to CSV"),
        ]
        self._action_btns: list[QPushButton] = []
        for lbl, obj, fn, tip in actions:
            btn = QPushButton(lbl)
            if obj: btn.setObjectName(obj)
            btn.setToolTip(tip)
            btn.setFixedHeight(30)
            btn.clicked.connect(fn)
            al.addWidget(btn)
            self._action_btns.append(btn)

        al.addStretch()

        # Sort selector
        al.addWidget(QLabel("Sort:"))
        self.sort_cb = QComboBox()
        self.sort_cb.setFixedWidth(110)
        for label, key in [("CPU %","cpu"),("Memory","memory"),("Name","name"),("PID","pid")]:
            self.sort_cb.addItem(label, key)
        self.sort_cb.currentIndexChanged.connect(self._on_sort_changed)
        al.addWidget(self.sort_cb)
        root.addWidget(abar)

        # ── Body: table + detail panel ───────────────────────────────
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setChildrenCollapsible(False)
        body.setHandleWidth(2)

        # table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "", "PID", "Name", "CPU %", "CPU ▬", "Mem %", "RSS MB", "Threads", "Status", "Priority"
        ])
        hh = self.table.horizontalHeader()
        self.table.setColumnWidth(0, 30)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(3, 65)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 70)
        self.table.setColumnWidth(6, 80)
        self.table.setColumnWidth(7, 68)
        self.table.setColumnWidth(8, 100)
        self.table.setColumnWidth(9, 100)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._ctx_menu)
        self.table.doubleClicked.connect(self._details)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.setStyleSheet(
            "QTableWidget { border-radius:0px; border:none; }"
        )

        # detail panel
        self._detail = DetailPanel()
        self._detail.setVisible(True)
        # connect quick action buttons
        self._detail._btn_suspend.clicked.connect(self._suspend)
        self._detail._btn_resume.clicked.connect(self._resume)
        self._detail._btn_kill.clicked.connect(self._kill)
        self._detail._btn_ktree.clicked.connect(self._kill_tree)

        body.addWidget(self.table)
        body.addWidget(self._detail)
        body.setSizes([820, 260])
        root.addWidget(body, stretch=1)

        # ── Status bar bottom ────────────────────────────────────────
        sbar = QWidget()
        sbar.setStyleSheet("background:#f9fafb;border-top:1px solid #e5e7eb;")
        sbar.setFixedHeight(28)
        sl   = QHBoxLayout(sbar); sl.setContentsMargins(14, 0, 14, 0)
        self._sbar_lbl = QLabel("Waiting for data…")
        self._sbar_lbl.setStyleSheet("color:#9ca3af;font-size:9pt;")
        sl.addWidget(self._sbar_lbl)
        sl.addStretch()
        self._paused_lbl = QLabel("")
        self._paused_lbl.setStyleSheet("color:#d97706;font-size:9pt;font-weight:600;")
        sl.addWidget(self._paused_lbl)
        root.addWidget(sbar)

    # ─────────────────────────────────────────────────────────────────
    @pyqtSlot(list)
    def _on_processes(self, procs: list[dict]) -> None:
        if self._paused:
            return

        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)

        new_pids = {p["pid"] for p in procs}

        # Remove gone rows
        rows_to_del = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item:
                try:
                    pid = int(item.data(Qt.ItemDataRole.DisplayRole))
                    if pid not in new_pids:
                        rows_to_del.append(row)
                except Exception:
                    pass
        for row in reversed(rows_to_del):
            self.table.removeRow(row)

        # Build pid→row map
        pid_row: dict[int, int] = {}
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item:
                try:
                    pid_row[int(item.data(Qt.ItemDataRole.DisplayRole))] = row
                except Exception:
                    pass

        # Upsert
        for p in procs:
            pid = p["pid"]
            if pid in pid_row:
                self._update_row(pid_row[pid], p)
            else:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setRowHeight(r, 26)
                self._fill_row(r, p)

        self._cache = {p["pid"]: p for p in procs}

        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)
        self._filter()

        total_cpu = sum(p["cpu"] for p in procs)
        self._sbar_lbl.setText(
            f"{len(procs)} processes  ·  Total CPU: {total_cpu:.1f}%"
        )

        # Refresh detail if a process is selected
        if self._selected_pid and self._selected_pid in self._cache:
            self._detail.update_info(self._cache[self._selected_pid])

    # ─────────────────────────────────────────────────────────────────
    def _fill_row(self, row: int, p: dict) -> None:
        # col 0: icon
        ico = QTableWidgetItem()
        ico.setIcon(icon_for_exe(p.get("exe_path")))
        ico.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.table.setItem(row, 0, ico)

        # col 1: PID
        pid_item = QTableWidgetItem()
        pid_item.setData(Qt.ItemDataRole.DisplayRole, p["pid"])
        pid_item.setFont(MONO_S)
        pid_item.setForeground(QColor("#9ca3af"))
        pid_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.table.setItem(row, 1, pid_item)

        # col 2: Name
        name_item = QTableWidgetItem(p["name"])
        name_item.setFont(QFont("Segoe UI", 9))
        self.table.setItem(row, 2, name_item)

        # cols 3-9 are filled by _update_row
        for c in range(3, 10):
            self.table.setItem(row, c, QTableWidgetItem())
        self._update_row(row, p)

    def _update_row(self, row: int, p: dict) -> None:
        cpu  = p["cpu"]
        mem  = p["memory"]
        raw  = (p.get("status") or "").strip()

        # col 3: CPU %
        ci = self.table.item(row, 3)
        if not ci: ci = QTableWidgetItem(); self.table.setItem(row, 3, ci)
        ci.setData(Qt.ItemDataRole.DisplayRole, round(cpu, 1))
        ci.setFont(MONO)
        ci.setForeground(_cpu_fg(cpu))
        ci.setBackground(_cpu_bg(cpu))

        # col 4: ASCII bar
        bi = self.table.item(row, 4)
        if not bi: bi = QTableWidgetItem(); self.table.setItem(row, 4, bi)
        bi.setText(_ascii_bar(cpu, 12))
        bi.setFont(QFont("Consolas", 7))
        bi.setForeground(_cpu_fg(cpu))

        # col 5: Mem %
        mi = self.table.item(row, 5)
        if not mi: mi = QTableWidgetItem(); self.table.setItem(row, 5, mi)
        mi.setData(Qt.ItemDataRole.DisplayRole, round(mem, 2))
        mi.setFont(MONO)
        mi.setForeground(_mem_fg(mem))

        # col 6: RSS MB
        import psutil
        rss = 0.0
        try: rss = psutil.Process(p["pid"]).memory_info().rss / 1e6
        except Exception: pass
        ri = self.table.item(row, 6)
        if not ri: ri = QTableWidgetItem(); self.table.setItem(row, 6, ri)
        ri.setData(Qt.ItemDataRole.DisplayRole, round(rss, 1))
        ri.setFont(MONO)
        ri.setForeground(_mem_fg(mem))

        # col 7: Threads
        ti = self.table.item(row, 7)
        if not ti: ti = QTableWidgetItem(); self.table.setItem(row, 7, ti)
        ti.setData(Qt.ItemDataRole.DisplayRole, p.get("threads", 0))
        ti.setFont(MONO_S)
        ti.setForeground(QColor("#6b7280"))

        # col 8: Status
        si = self.table.item(row, 8)
        if not si: si = QTableWidgetItem(); self.table.setItem(row, 8, si)
        si.setText(process_status_label(raw))
        si.setData(Qt.ItemDataRole.UserRole, raw.lower())
        si.setForeground(_status_fg(raw))
        si.setFont(QFont("Segoe UI", 9))

        # col 9: Priority
        pi = self.table.item(row, 9)
        if not pi: pi = QTableWidgetItem(); self.table.setItem(row, 9, pi)
        pi.setText(nice_to_label(p.get("nice", 0) or 0))
        pi.setForeground(QColor("#6b7280"))
        pi.setFont(QFont("Segoe UI", 9))

    # ─────────────────────────────────────────────────────────────────
    def _filter(self) -> None:
        text    = self.search.text().strip().lower()
        cpu_min = self.cpu_spin.value()
        mem_min = self.mem_spin.value()
        st_key  = self.status_cb.currentData()
        visible = 0

        for row in range(self.table.rowCount()):
            n2  = self.table.item(row, 2)
            c3  = self.table.item(row, 3)
            m5  = self.table.item(row, 5)
            s8  = self.table.item(row, 8)

            name = n2.text().lower()  if n2  else ""
            cpu  = float(c3.data(Qt.ItemDataRole.DisplayRole) or 0) if c3 else 0.0
            mem  = float(m5.data(Qt.ItemDataRole.DisplayRole) or 0) if m5 else 0.0
            st   = (s8.data(Qt.ItemDataRole.UserRole) or "") if s8 else ""

            show = (
                (not text    or text in name)
                and cpu >= cpu_min
                and mem >= mem_min
                and (st_key is None or st == st_key)
            )
            self.table.setRowHidden(row, not show)
            if show: visible += 1

        self._count_lbl.setText(f"{visible}  of  {self.table.rowCount()}")

    def _on_sort_changed(self) -> None:
        pass  # DataWorker already sorts; visual sort via header click is enough

    def _on_selection_changed(self) -> None:
        pid = self._selected_pid_now()
        self._selected_pid = pid
        if pid and pid in self._cache:
            from core.services.process_service import get_process_details
            details = get_process_details(pid)
            self._detail.update_info(self._cache[pid], details)
        else:
            self._detail.update_info(None)

    # ─────────────────────────────────────────────────────────────────
    def _ctx_menu(self, pos) -> None:
        pid = self._selected_pid_now()
        if pid is None: return

        menu = QMenu(self); menu.setObjectName("ContextMenu")
        a_kill      = menu.addAction("✕  Kill process  (SIGTERM)")
        a_kill_tree = menu.addAction("✕✕ Kill tree  (SIGKILL + children)")
        menu.addSeparator()
        a_suspend   = menu.addAction("⏸  Suspend")
        a_resume    = menu.addAction("▶  Resume")
        menu.addSeparator()

        prio_menu = menu.addMenu("↑  Set priority")
        for opt in get_priority_options():
            prio_menu.addAction(opt)

        menu.addSeparator()
        a_folder  = menu.addAction("📁  Open file location")
        a_details = menu.addAction("🔍  Full details…")
        menu.addSeparator()
        a_search  = menu.addAction("🌐  Search on Google")
        a_copy_pid = menu.addAction("📋  Copy PID")
        a_copy_name = menu.addAction("📋  Copy name")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if not action: return

        name = self._selected_name()
        if   action == a_kill:       self._kill()
        elif action == a_kill_tree:  self._kill_tree()
        elif action == a_suspend:    self._suspend()
        elif action == a_resume:     self._resume()
        elif action == a_folder:     self._open_folder()
        elif action == a_details:    self._details()
        elif action == a_search:
            webbrowser.open(f"https://www.google.com/search?q={name}+process")
        elif action == a_copy_pid:
            QApplication.clipboard().setText(str(pid))
        elif action == a_copy_name:
            QApplication.clipboard().setText(name)
        elif action.parent() == prio_menu:
            ok, msg = change_priority(pid, action.text())
            self._show(ok, msg, "Priority")

    # ─────────────────────────────────────────────────────────────────
    def _kill(self) -> None:
        pid, name = self._selected_pid_now(), self._selected_name()
        if pid is None:
            QMessageBox.warning(self, "Kill", "Select a process first."); return
        r = QMessageBox.question(
            self, "Confirm — Kill process",
            f'<b>Kill "{name}"</b>  (PID {pid})?<br><br>'
            f'The process will receive SIGTERM and may save its state before closing.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes: return
        ok, msg = kill_process(pid)
        if ok: add_process_alert(f"Process killed: {name}", f"PID {pid} terminated.")
        self._show(ok, msg, "Kill process")

    def _kill_tree(self) -> None:
        pid, name = self._selected_pid_now(), self._selected_name()
        if pid is None: return
        r = QMessageBox.question(
            self, "Confirm — Kill tree",
            f'<b>Kill "{name}"</b> AND all its children?<br><br>'
            f'This sends SIGKILL recursively. PID {pid}.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes: return
        ok, msg = kill_process_and_children(pid)
        if ok: add_process_alert(f"Tree killed: {name}", msg)
        self._show(ok, msg, "Kill tree")

    def _suspend(self) -> None:
        pid, name = self._selected_pid_now(), self._selected_name()
        if pid is None: QMessageBox.warning(self, "Suspend", "Select a process first."); return
        ok, msg = suspend(pid)
        if ok: add_process_alert(f"Suspended: {name}", f"PID {pid} suspended.", )
        self._show(ok, msg, "Suspend")

    def _resume(self) -> None:
        pid, name = self._selected_pid_now(), self._selected_name()
        if pid is None: QMessageBox.warning(self, "Resume", "Select a process first."); return
        ok, msg = resume(pid)
        if ok: add_process_alert(f"Resumed: {name}", f"PID {pid} resumed.")
        self._show(ok, msg, "Resume")

    def _change_prio(self) -> None:
        pid = self._selected_pid_now()
        if pid is None: QMessageBox.warning(self, "Priority", "Select a process first."); return

        menu = QMenu(self); menu.setObjectName("ContextMenu")
        for opt in get_priority_options():
            menu.addAction(opt)
        btn  = self._action_btns[4]   # the Priority button
        gpos = btn.mapToGlobal(btn.rect().bottomLeft())
        action = menu.exec(gpos)
        if not action: return
        ok, msg = change_priority(pid, action.text())
        self._show(ok, msg, "Priority")

    def _open_folder(self) -> None:
        pid = self._selected_pid_now()
        if pid is None: QMessageBox.warning(self, "Location", "Select a process first."); return
        path = get_process_exe_path(pid)
        if not path:
            QMessageBox.warning(self, "Location", "Executable path not available."); return
        ok, msg = open_process_folder(path)
        if not ok: QMessageBox.warning(self, "Location", msg)

    def _details(self) -> None:
        pid = self._selected_pid_now()
        if pid is None: QMessageBox.warning(self, "Details", "Select a process first."); return

        d = get_process_details(pid)
        if not d:
            QMessageBox.warning(self, "Details", f"PID {pid} not found or access denied."); return

        p = self._cache.get(pid, {})

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Details — {d.get('name','?')}  (PID {pid})")
        dlg.setMinimumSize(520, 460)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(0)

        # title
        th = QWidget(); th.setStyleSheet("background:#4f46e5;padding:0;")
        th.setFixedHeight(56)
        thl = QHBoxLayout(th); thl.setContentsMargins(18, 0, 18, 0)
        tn  = QLabel(d.get("name","?")); tn.setStyleSheet("color:#fff;font-size:14pt;font-weight:700;")
        tp  = QLabel(f"PID  {pid}");    tp.setStyleSheet("color:#c7d2fe;font-size:10pt;font-family:Consolas;")
        thl.addWidget(tn); thl.addStretch(); thl.addWidget(tp)
        lay.addWidget(th)

        # scroll content
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); content.setStyleSheet("background:#ffffff;")
        cl = QVBoxLayout(content); cl.setContentsMargins(20, 16, 20, 16); cl.setSpacing(4)

        import time
        uptime_s = (time.time() - d.get("create_time", time.time()))

        sections = {
            "Process": [
                ("Status",          process_status_label(d.get("status",""))),
                ("CPU usage",       f"{p.get('cpu',0):.2f}%"),
                ("Threads",         str(d.get("num_threads","—"))),
                ("Child processes", str(len(d.get("children",[])))),
                ("Children PIDs",   str(d.get("children","—"))),
                ("Running for",     seconds_to_human(uptime_s)),
                ("User",            str(d.get("username","—"))),
                ("Priority",        nice_to_label(p.get("nice",0) or 0)),
            ],
            "Memory": [
                ("RSS",             f"{d.get('mem_rss_mb',0):.2f} MB"),
                ("VMS",             f"{d.get('mem_vms_mb',0):.2f} MB"),
                ("Memory %",        f"{p.get('memory',0):.3f}%"),
            ],
            "Identification": [
                ("PID",             str(d.get("pid","—"))),
                ("Executable",      get_process_exe_path(pid) or "—"),
                ("Command line",    str(d.get("cmdline","—"))),
            ],
        }

        for section, rows in sections.items():
            sh = QLabel(section.upper())
            sh.setStyleSheet(
                "color:#9ca3af;font-size:8.5pt;font-weight:700;"
                "letter-spacing:1px;padding:10px 0 4px 0;"
            )
            cl.addWidget(sh)
            sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color:#f3f4f6;")
            cl.addWidget(sep)

            for key, val in rows:
                rw = QWidget(); rw.setStyleSheet("background:transparent;")
                rl = QHBoxLayout(rw); rl.setContentsMargins(0, 3, 0, 3); rl.setSpacing(8)
                lk = QLabel(key); lk.setFixedWidth(140)
                lk.setStyleSheet("color:#6b7280;font-size:9.5pt;")
                lv = QLabel(str(val))
                lv.setStyleSheet("color:#111827;font-size:9.5pt;font-weight:600;font-family:Consolas;")
                lv.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                lv.setWordWrap(True)
                rl.addWidget(lk); rl.addWidget(lv, stretch=1)
                cl.addWidget(rw)

        cl.addStretch()
        scroll.setWidget(content)
        lay.addWidget(scroll, stretch=1)

        # buttons
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.exec()

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export processes",
            f"processes_{datetime.now():%Y%m%d_%H%M}.csv", "CSV (*.csv)"
        )
        if not path: return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(export_processes_csv())
            QMessageBox.information(self, "Export", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export error", str(e))

    # ─────────────────────────────────────────────────────────────────
    def _selected_pid_now(self) -> int | None:
        row = self.table.currentRow()
        if row < 0: return None
        item = self.table.item(row, 1)
        if not item: return None
        try: return int(item.data(Qt.ItemDataRole.DisplayRole))
        except Exception: return None

    def _selected_name(self) -> str:
        row = self.table.currentRow()
        item = self.table.item(row, 2) if row >= 0 else None
        return item.text() if item else "?"

    def _show(self, ok: bool, msg: str, title: str) -> None:
        if ok: QMessageBox.information(self, title, msg)
        else:  QMessageBox.warning(self, f"Error — {title}", msg)
