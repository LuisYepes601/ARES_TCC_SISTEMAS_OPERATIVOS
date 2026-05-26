"""
ui/tabs/performance_tab.py
Pestaña de Rendimiento v3 — tema claro, fuentes grandes, todos los gráficos visibles.
"""
from __future__ import annotations
from collections import deque

import pyqtgraph as pg
from PyQt6.QtCore  import Qt, pyqtSlot
from PyQt6.QtGui   import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QProgressBar, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from core.services.system_service import get_cpu_count_logical, get_disk_mount_choices
from ui.styles.performance_palette import (
    COLOR_CPU, COLOR_MEM, COLOR_DISK, COLOR_WIFI, COLOR_GPU,
    palette_for_theme,
)
from ui.styles.theme import saved_theme, THEME_LIGHT, THEME_DARK

pg.setConfigOptions(antialias=True, useOpenGL=False)
MAX_PTS = 90


# ── Chart panel ──────────────────────────────────────────────────────

class ChartPanel(QFrame):
    def __init__(self, title: str, color: str, unit: str = "%", parent=None):
        super().__init__(parent)
        self.setObjectName("ChartCard")
        self._color = color
        self._data  = deque(maxlen=MAX_PTS)
        self._unit  = unit

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(6)

        # header row
        hr = QHBoxLayout()
        self._title_lbl = QLabel(title.upper())
        self._title_lbl.setStyleSheet(
            "font-size:8.5pt;font-weight:700;letter-spacing:1.2px;"
            "color:#9ca3af;text-transform:uppercase;"
        )
        self._pct_lbl = QLabel("—")
        self._pct_lbl.setStyleSheet(
            f"font-size:22pt;font-weight:800;color:{color};"
            "font-family:'Segoe UI','SF Pro Display',system-ui;"
        )
        self._pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hr.addWidget(self._title_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        hr.addStretch()
        hr.addWidget(self._pct_lbl)
        lay.addLayout(hr)

        # sub-label
        self._sub_lbl = QLabel("—")
        self._sub_lbl.setStyleSheet(
            "color:#9ca3af;font-size:8.5pt;"
            "font-family:'Consolas','SF Mono',monospace;"
        )
        lay.addWidget(self._sub_lbl)

        # mini progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setFixedHeight(5)
        self._bar.setTextVisible(False)
        self._bar.setObjectName("UsageBar")
        self._bar.setStyleSheet(
            f"QProgressBar#UsageBar::chunk{{background:{color};border-radius:2px;}}"
        )
        lay.addWidget(self._bar)

        # graph
        self._plot = pg.PlotWidget()
        self._plot.setBackground("#ffffff")
        self._plot.setMinimumHeight(80)
        self._plot.setMaximumHeight(110)
        self._plot.setMouseEnabled(False, False)
        self._plot.getViewBox().setBorder(None)
        self._plot.setYRange(0, 100)
        self._plot.showGrid(x=False, y=True, alpha=0.08)
        for ax in ("bottom", "left"):
            self._plot.getAxis(ax).setStyle(showValues=False)
            self._plot.getAxis(ax).setPen(pg.mkPen("#f3f4f6"))

        pen = pg.mkPen(color, width=2)
        self._curve = self._plot.plot(
            pen=pen, fillLevel=0,
            fillBrush=pg.mkBrush(color + "22"),
        )
        lay.addWidget(self._plot)

    def push(self, value: float, big_text: str, sub_text: str = "") -> None:
        v = max(0.0, min(100.0, value))
        self._data.append(v)
        data = list(self._data)
        self._curve.setData(range(len(data)), data)
        self._pct_lbl.setText(big_text)
        self._bar.setValue(int(v))
        if sub_text:
            self._sub_lbl.setText(sub_text)


# ── Core bars ────────────────────────────────────────────────────────

class CoreStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars: list[QProgressBar] = []
        self._lbls: list[QLabel]       = []
        self._vals: list[QLabel]       = []
        self._lay  = QGridLayout(self)
        self._lay.setContentsMargins(4, 4, 4, 4)
        self._lay.setSpacing(6)
        self.setStyleSheet("background:transparent;")
        self._init(get_cpu_count_logical() or 4)

    def _init(self, n: int) -> None:
        cols = min(n, 8)
        for i in range(n):
            r, c = divmod(i, cols)
            cell = QWidget(); cell.setStyleSheet("background:transparent;")
            cl   = QVBoxLayout(cell); cl.setContentsMargins(0,0,0,0); cl.setSpacing(2)

            top = QHBoxLayout(); top.setContentsMargins(0,0,0,0)
            lbl = QLabel(f"C{i}")
            lbl.setStyleSheet("color:#9ca3af;font-size:8pt;font-family:Consolas;")
            val = QLabel("0%")
            val.setStyleSheet("color:#6366f1;font-size:8pt;font-family:Consolas;font-weight:700;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            top.addWidget(lbl); top.addStretch(); top.addWidget(val)

            bar = QProgressBar()
            bar.setRange(0, 100); bar.setFixedHeight(6)
            bar.setTextVisible(False); bar.setObjectName("CoreBar")
            cl.addLayout(top); cl.addWidget(bar)
            self._lay.addWidget(cell, r, c)
            self._lbls.append(lbl); self._bars.append(bar); self._vals.append(val)

    def update_cores(self, cores: list[float]) -> None:
        for i, (bar, val_lbl) in enumerate(zip(self._bars, self._vals)):
            v = int(cores[i]) if i < len(cores) else 0
            bar.setValue(v)
            val_lbl.setText(f"{v}%")
            if v >= 85:   c = "#dc2626"
            elif v >= 60: c = "#d97706"
            elif v >= 30: c = "#6366f1"
            else:          c = "#a5b4fc"
            bar.setStyleSheet(
                f"QProgressBar#CoreBar{{background:#f3f4f6;border:none;border-radius:3px;}}"
                f"QProgressBar#CoreBar::chunk{{background:{c};border-radius:3px;}}"
            )
            val_lbl.setStyleSheet(f"color:{c};font-size:8pt;font-family:Consolas;font-weight:700;")


# ── Health bar ───────────────────────────────────────────────────────

class HealthWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(10)

        lbl = QLabel("HEALTH")
        lbl.setStyleSheet(
            "color:#9ca3af;font-size:8.5pt;font-weight:700;letter-spacing:1px;"
        )
        self._bar  = QProgressBar()
        self._bar.setRange(0,100)
        self._bar.setObjectName("HealthBar")
        self._bar.setFixedHeight(10)

        self._score = QLabel("—")
        self._score.setStyleSheet(
            "color:#374151;font-size:10pt;font-weight:700;"
            "font-family:'Consolas','SF Mono',monospace;"
        )
        self._desc  = QLabel("—")
        self._desc.setStyleSheet("color:#9ca3af;font-size:9pt;")

        lay.addWidget(lbl)
        lay.addWidget(self._bar, stretch=1)
        lay.addWidget(self._score)
        lay.addWidget(self._desc)

    def update(self, score: float, desc: str) -> None:
        self._bar.setValue(int(score))
        self._score.setText(f"{score:.0f}/100")
        self._desc.setText(desc)
        if score >= 70:   c = "#16a34a"
        elif score >= 50: c = "#d97706"
        else:              c = "#dc2626"
        self._bar.setStyleSheet(
            f"QProgressBar#HealthBar{{background:#e5e7eb;border:none;border-radius:5px;}}"
            f"QProgressBar#HealthBar::chunk{{background:{c};border-radius:5px;}}"
        )
        self._score.setStyleSheet(
            f"color:{c};font-size:10pt;font-weight:700;"
            "font-family:'Consolas','SF Mono',monospace;"
        )


# ── IO stats strip ───────────────────────────────────────────────────

class IOStats(QWidget):
    """Muestra métricas de I/O de disco y red en tiempo real."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(20)
        self._lbls: dict[str, QLabel] = {}
        for key, icon, label in [
            ("disk_r",  "💾", "Disk read"),
            ("disk_w",  "💾", "Disk write"),
            ("net_up",  "🌐", "Net up"),
            ("net_dn",  "🌐", "Net down"),
            ("procs",   "⚡", "Processes"),
        ]:
            col = QVBoxLayout(); col.setSpacing(1)
            k = QLabel(f"{icon} {label}")
            k.setStyleSheet("color:#9ca3af;font-size:8pt;font-weight:600;letter-spacing:0.5px;")
            v = QLabel("—")
            v.setStyleSheet(
                "color:#374151;font-size:10pt;font-weight:700;"
                "font-family:'Consolas','SF Mono',monospace;"
            )
            col.addWidget(k); col.addWidget(v)
            lay.addLayout(col)
            self._lbls[key] = v
        lay.addStretch()

    def update(self, d: dict) -> None:
        from core.utils.formatters import bytes_per_sec_human
        disk_io = d.get("disk_io", {})
        self._lbls["disk_r"].setText(bytes_per_sec_human(disk_io.get("read_bytes", 0) or 0))
        self._lbls["disk_w"].setText(bytes_per_sec_human(disk_io.get("write_bytes", 0) or 0))
        self._lbls["net_up"].setText(bytes_per_sec_human(d.get("net_sent_r", 0)))
        self._lbls["net_dn"].setText(bytes_per_sec_human(d.get("net_recv_r", 0)))
        self._lbls["procs"].setText(str(d.get("proc_count", "—")))


# ── Main tab ─────────────────────────────────────────────────────────

class PerformanceTab(QWidget):
    def __init__(self, worker=None, parent=None):
        super().__init__(parent)
        self._worker = worker
        self._build_ui()
        if worker:
            worker.system_ready.connect(self._on_data)

    def set_app_theme(self, theme: str) -> None:
        pass   # light-only for now

    def pause_updates(self, p: bool) -> None:
        pass   # data-driven, no timer

    # ─────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────
        hdr = QWidget(); hdr.setObjectName("TabHeader"); hdr.setFixedHeight(52)
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(18, 0, 18, 0); hl.setSpacing(16)
        t   = QLabel("Performance"); t.setObjectName("PanelTitle")
        self._health = HealthWidget()
        hl.addWidget(t)
        hl.addSpacing(20)
        hl.addWidget(self._health, stretch=1)
        root.addWidget(hdr)

        # ── IO stats strip ───────────────────────────────────────────
        io_bar = QWidget()
        io_bar.setStyleSheet("background:#f9fafb;border-bottom:1px solid #e5e7eb;")
        io_bar.setFixedHeight(52)
        ibl = QHBoxLayout(io_bar); ibl.setContentsMargins(18, 6, 18, 6)
        self._io_stats = IOStats()
        ibl.addWidget(self._io_stats)
        root.addWidget(io_bar)

        # ── Options bar ──────────────────────────────────────────────
        opts = QWidget()
        opts.setStyleSheet("background:#ffffff;border-bottom:1px solid #e5e7eb;")
        opts.setFixedHeight(40)
        ol = QHBoxLayout(opts); ol.setContentsMargins(14, 0, 14, 0); ol.setSpacing(12)

        ol.addWidget(QLabel("Disk:"))
        self._disk_cb = QComboBox(); self._disk_cb.setFixedWidth(110)
        for d in get_disk_mount_choices():
            self._disk_cb.addItem(d)
        ol.addWidget(self._disk_cb)

        ol.addSpacing(16)
        ol.addWidget(QLabel("Network max:"))
        self._net_cb = QComboBox(); self._net_cb.setFixedWidth(110)
        for v in ["50", "100", "300", "600", "1000"]:
            self._net_cb.addItem(f"{v} Mbps", float(v))
        self._net_cb.setCurrentIndex(1)
        ol.addWidget(self._net_cb)
        ol.addStretch()

        self._proc_lbl = QLabel("—")
        self._proc_lbl.setStyleSheet(
            "color:#9ca3af;font-size:9pt;font-family:'Consolas','SF Mono',monospace;"
        )
        ol.addWidget(self._proc_lbl)

        if self._worker:
            self._disk_cb.currentTextChanged.connect(self._worker.set_disk_path)
            self._net_cb.currentIndexChanged.connect(
                lambda i: self._worker.set_wifi_max(self._net_cb.itemData(i) or 100.0)
            )
        root.addWidget(opts)

        # ── Charts grid ──────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:#f5f6fa;")

        container = QWidget()
        container.setStyleSheet("background:#f5f6fa;")
        grid = QGridLayout(container)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setSpacing(12)

        self._p_cpu  = ChartPanel("CPU",     COLOR_CPU,  "%")
        self._p_mem  = ChartPanel("Memory",  COLOR_MEM,  "%")
        self._p_disk = ChartPanel("Disk",    COLOR_DISK, "%")
        self._p_net  = ChartPanel("Network", COLOR_WIFI, "Mbps")
        self._p_gpu  = ChartPanel("GPU",     COLOR_GPU,  "%")

        grid.addWidget(self._p_cpu,  0, 0)
        grid.addWidget(self._p_mem,  0, 1)
        grid.addWidget(self._p_disk, 1, 0)
        grid.addWidget(self._p_net,  1, 1)
        grid.addWidget(self._p_gpu,  2, 0)

        # CPU cores panel
        cores_card = QFrame(); cores_card.setObjectName("ChartCard")
        ccl = QVBoxLayout(cores_card); ccl.setContentsMargins(14, 12, 14, 12); ccl.setSpacing(8)
        ch = QLabel("CPU CORES")
        ch.setStyleSheet(
            "font-size:8.5pt;font-weight:700;letter-spacing:1.2px;color:#9ca3af;"
        )
        ccl.addWidget(ch)
        self._cores = CoreStrip()
        ccl.addWidget(self._cores)
        grid.addWidget(cores_card, 2, 1)

        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

    # ─────────────────────────────────────────────────────────────────
    @pyqtSlot(dict)
    def _on_data(self, d: dict) -> None:
        cpu   = d.get("cpu", 0)
        mem   = d.get("mem_pct", 0)
        disk  = d.get("disk_pct", 0)
        net   = d.get("net_pct", 0)
        gpu_v = d.get("gpu_pct") or 0.0
        freq  = d.get("freq")
        mdet  = d.get("mem_det", {})
        mbps  = d.get("net_mbps", 0)
        sent  = d.get("net_sent_r", 0)
        recv  = d.get("net_recv_r", 0)
        h     = d.get("health", 0)
        hd    = d.get("health_desc", "—")

        freq_s = f"{freq[0]/1000:.2f} GHz" if freq and freq[0] else "—"

        self._p_cpu.push(
            cpu, f"{cpu:.1f}%",
            f"{freq_s}  ·  {len(d.get('cores',[]))} cores"
        )
        self._p_mem.push(
            mem, f"{mem:.1f}%",
            f"{mdet.get('used_gb',0):.1f} / {mdet.get('total_gb',0):.1f} GB"
            f"  ·  swap {mdet.get('swap_percent',0):.0f}%"
        )
        self._p_disk.push(
            disk, f"{disk:.1f}%",
            f"{d.get('disk_used',0):.1f} / {d.get('disk_total',0):.1f} GB"
            f"  {d.get('disk_path','')}"
        )
        self._p_net.push(
            net, f"{mbps:.1f} Mbps",
            f"↑ {sent/1024:.0f} KB/s  ·  ↓ {recv/1024:.0f} KB/s"
        )

        if d.get("gpu_pct") is not None:
            self._p_gpu.push(gpu_v, f"{gpu_v:.1f}%", d.get("gpu_name", "GPU"))
        else:
            self._p_gpu.push(0, "N/A", d.get("gpu_name", "No GPU detected"))

        self._cores.update_cores(d.get("cores", []))
        self._health.update(h, hd)
        self._io_stats.update(d)
        self._proc_lbl.setText(f"{d.get('proc_count','—')} processes")
