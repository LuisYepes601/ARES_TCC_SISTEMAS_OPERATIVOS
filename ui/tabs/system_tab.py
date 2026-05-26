"""ui/tabs/system_tab.py — Sistema v3 tema claro."""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar,
    QScrollArea, QVBoxLayout, QWidget,
)
from core.services.system_service import (
    get_architecture, get_boot_time, get_cpu_count_logical,
    get_cpu_count_physical, get_cpu_freq, get_cpu_freq_per_core,
    get_cpu_name, get_disks, get_hostname, get_memory_details,
    get_os_info, get_ram_total_gb, get_uptime_str,
)

MONO = "font-family:'Consolas','SF Mono',monospace;font-size:10pt;"


def _section_header(text: str) -> QWidget:
    w  = QWidget(); w.setStyleSheet("background:transparent;")
    l  = QVBoxLayout(w); l.setContentsMargins(0,16,0,4); l.setSpacing(2)
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color:#6b7280;font-size:8.5pt;font-weight:700;"
        "letter-spacing:1.2px;text-transform:uppercase;"
    )
    sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color:#e5e7eb;margin:0;")
    l.addWidget(lbl); l.addWidget(sep)
    return w


def _info_row(key: str, value: str, mono: bool = True) -> QWidget:
    w  = QWidget(); w.setStyleSheet("background:transparent;")
    l  = QHBoxLayout(w); l.setContentsMargins(4, 4, 4, 4); l.setSpacing(0)
    lk = QLabel(key); lk.setFixedWidth(200)
    lk.setStyleSheet("color:#9ca3af;font-size:10pt;")
    lv = QLabel(value)
    lv.setStyleSheet(
        (MONO if mono else "") + "color:#1f2937;font-weight:600;"
    )
    lv.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    lv.setWordWrap(True)
    l.addWidget(lk); l.addWidget(lv, stretch=1)
    return w


def _disk_row(disk: dict) -> QWidget:
    w  = QWidget(); w.setStyleSheet("background:transparent;")
    l  = QVBoxLayout(w); l.setContentsMargins(4, 6, 4, 6); l.setSpacing(4)

    top = QHBoxLayout(); top.setContentsMargins(0,0,0,0)
    mp  = QLabel(disk["mountpoint"])
    mp.setStyleSheet(MONO + "color:#1f2937;font-weight:700;font-size:11pt;")
    used_s = f"{disk['used_gb']:.1f} GB  /  {disk['total_gb']:.1f} GB"
    pct_s  = f"{disk['percent']:.0f}%"
    info   = QLabel(f"{used_s}   ·   {disk['fstype']}")
    info.setStyleSheet("color:#6b7280;font-size:9.5pt;font-family:Consolas;")
    pct_lbl = QLabel(pct_s)
    pct     = disk["percent"]
    c = "#dc2626" if pct > 90 else "#d97706" if pct > 75 else "#4f46e5"
    pct_lbl.setStyleSheet(
        f"color:{c};font-size:11pt;font-weight:700;font-family:Consolas;"
    )
    top.addWidget(mp); top.addStretch(); top.addWidget(info); top.addSpacing(12); top.addWidget(pct_lbl)
    l.addLayout(top)

    bar = QProgressBar()
    bar.setRange(0,100); bar.setValue(int(pct))
    bar.setFixedHeight(8); bar.setTextVisible(False)
    bar.setStyleSheet(
        f"QProgressBar{{background:#e5e7eb;border:none;border-radius:4px;}}"
        f"QProgressBar::chunk{{background:{c};border-radius:4px;}}"
    )
    l.addWidget(bar)
    return w


class SystemTab(QWidget):
    def __init__(self):
        super().__init__()
        scroll  = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:#f5f6fa;")

        content = QWidget()
        content.setStyleSheet("background:#ffffff;")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 8, 24, 24)
        lay.setSpacing(0)

        # ── System ──────────────────────────────────────────────────
        lay.addWidget(_section_header("System"))
        lay.addWidget(_info_row("Hostname",         get_hostname(), mono=False))
        lay.addWidget(_info_row("Operating system", get_os_info(),  mono=False))
        lay.addWidget(_info_row("Architecture",     get_architecture()))
        lay.addWidget(_info_row("Uptime",           get_uptime_str()))
        boot = get_boot_time()
        lay.addWidget(_info_row("Boot time",
            boot.strftime("%Y-%m-%d  %H:%M:%S") if boot else "—"))

        # ── Processor ───────────────────────────────────────────────
        lay.addWidget(_section_header("Processor"))
        lay.addWidget(_info_row("Model",            get_cpu_name(),               mono=False))
        lay.addWidget(_info_row("Physical cores",   str(get_cpu_count_physical())))
        lay.addWidget(_info_row("Logical cores",    str(get_cpu_count_logical())))
        freq = get_cpu_freq()
        if freq and freq[0]:
            lay.addWidget(_info_row("Base frequency",  f"{freq[0]/1000:.3f} GHz"))
        if freq and freq[2]:
            lay.addWidget(_info_row("Max frequency",   f"{freq[2]/1000:.3f} GHz"))
        per_core = get_cpu_freq_per_core()
        if per_core:
            parts = "  ".join(
                f"C{i}: {f[0]/1000:.2f}" for i, f in enumerate(per_core[:12]) if f
            )
            if parts:
                lay.addWidget(_info_row("Per-core GHz", parts))

        # ── Memory ──────────────────────────────────────────────────
        lay.addWidget(_section_header("Memory"))
        mem = get_memory_details()
        lay.addWidget(_info_row("Total RAM",    f"{mem.get('total_gb',0):.2f} GB"))
        lay.addWidget(_info_row("Available",    f"{mem.get('available_gb',0):.2f} GB"))
        lay.addWidget(_info_row("Used",
            f"{mem.get('used_gb',0):.2f} GB  ({mem.get('percent',0):.1f}%)"))
        if mem.get("cached_gb",0):
            lay.addWidget(_info_row("Cached",   f"{mem.get('cached_gb',0):.2f} GB"))
        if mem.get("buffers_gb",0):
            lay.addWidget(_info_row("Buffers",  f"{mem.get('buffers_gb',0):.2f} GB"))
        if mem.get("swap_total_gb",0):
            lay.addWidget(_info_row("Swap total",
                f"{mem.get('swap_total_gb',0):.2f} GB"))
            lay.addWidget(_info_row("Swap used",
                f"{mem.get('swap_used_gb',0):.2f} GB  ({mem.get('swap_percent',0):.1f}%)"))

        # memory bar
        mem_bar_w = QWidget(); mem_bar_w.setStyleSheet("background:transparent;")
        mbl = QVBoxLayout(mem_bar_w); mbl.setContentsMargins(4,4,4,8); mbl.setSpacing(2)
        mp  = mem.get("percent", 0)
        mc  = "#dc2626" if mp > 90 else "#d97706" if mp > 75 else "#4f46e5"
        mb  = QProgressBar(); mb.setRange(0,100); mb.setValue(int(mp))
        mb.setFixedHeight(10); mb.setTextVisible(False)
        mb.setStyleSheet(
            f"QProgressBar{{background:#e5e7eb;border:none;border-radius:5px;}}"
            f"QProgressBar::chunk{{background:{mc};border-radius:5px;}}"
        )
        mbl.addWidget(mb)
        lay.addWidget(mem_bar_w)

        # ── Storage ─────────────────────────────────────────────────
        lay.addWidget(_section_header("Storage"))
        disks = get_disks()
        if disks:
            for disk in disks:
                lay.addWidget(_disk_row(disk))
        else:
            lay.addWidget(QLabel("Could not retrieve disk information."))

        lay.addStretch()
        scroll.setWidget(content)

        main = QVBoxLayout(self)
        main.setContentsMargins(0,0,0,0)
        main.addWidget(scroll)
