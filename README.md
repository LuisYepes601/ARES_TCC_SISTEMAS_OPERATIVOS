# Ares v3.0 — System Monitor

High-performance desktop system monitor for **Windows** and **macOS**, built with Python + PyQt6.  
Redesigned from scratch for speed, clarity and a minimal dark UI.

---

## What's new in v3.0

| Feature | Detail |
|---|---|
| **Non-blocking data engine** | `DataWorker` QThread collects all metrics in background — UI never stalls |
| **Unified data bus** | Single worker feeds every tab via Qt signals; no redundant psutil calls |
| **All-at-once performance view** | All 5 resource graphs visible simultaneously (no card selection needed) |
| **Per-core CPU bars** | Real-time colour-coded usage for every logical core |
| **Rich process table** | ASCII CPU bar column, RSS memory in MB, incremental row updates |
| **Smarter process diff** | Only inserts/removes changed rows — no full table rebuilds each tick |
| **Faster refresh** | System metrics at 1 Hz; process list at 0.33 Hz — configurable |
| **Minimal dark UI** | Deep navy/indigo palette, monospaced numbers, hairline borders |
| **No AI dependency** | Removed Claude integration → no API key required, smaller footprint |

---

## Architecture

```
main.py
│
├── core/workers/data_worker.py   ← single background QThread
│       │  emits: system_ready(dict)  process_ready(list)
│       │
├── core/data/          ← raw psutil / OS calls
├── core/services/      ← business logic, caching, alerts
└── core/utils/         ← formatters

ui/
├── main_window.py      ← sidebar nav, status bar, theme
└── tabs/
    ├── processes_tab.py    ← incremental table, rich columns
    ├── performance_tab.py  ← 5 live charts + core strip
    ├── network_tab.py      ← connections + per-interface stats
    ├── system_tab.py       ← full hw / OS / memory / disk info
    ├── alerts_tab.py       ← threshold config + alert history
    └── services_tab.py     ← Windows services (admin)
```

**Dependency rule**: UI → services → data. Never skip layers.

---

## Quick start

### macOS / Linux
```bash
git clone <repo>
cd ares-v3
bash run.sh
```

### Windows
```bat
run.bat
```

### Manual
```bash
python -m venv venv && source venv/bin/activate   # or .\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Requirements

- Python 3.10+
- PyQt6 ≥ 6.4
- psutil ≥ 5.9
- pyqtgraph ≥ 0.13
- Windows 10+ or macOS 10.14+

---

## Tabs

### ⚡ Processes
- Live table with icon, PID, name, CPU %, ASCII bar, MEM %, RSS MB, threads, status
- Incremental updates — only changed rows are modified
- Filter by name, CPU threshold, MEM threshold, status
- Right-click: kill, kill tree, suspend, resume, set priority, open location, details
- Export to CSV

### 📊 Performance
- All resources visible at once: CPU, Memory, Disk, Network, GPU
- 90-point rolling waveform graphs
- Per-core CPU usage strip with colour coding
- System health score 0–100
- Disk selector + network max speed selector

### 🌐 Network
- Global bytes sent/received
- Per-interface breakdown (up to 8 interfaces)
- Active connection table: local/remote addr, status (colour-coded), type, PID
- Auto-refreshes every 3 s

### 🖥 System
- Full CPU info: model, cores (physical/logical), per-core frequencies
- Detailed memory: total, available, used, cached, swap
- Storage: all partitions with ASCII usage bar + fstype
- OS, hostname, architecture, boot time, uptime

### 🔔 Alerts
- Configurable thresholds: CPU, Memory, Disk, GPU (warning + critical)
- Deduplication — same alert fires at most once per minute
- Colour-coded history; dismiss individual or all; clear history

### ⚙ Services *(Windows only)*
- Full service list with status
- Start / Stop (requires admin)

---

## Performance notes

| Setting | Value | Why |
|---|---|---|
| System metric interval | 1.0 s | Smooth graphs without overloading |
| Process list interval | 3.0 s | psutil iteration is expensive |
| Chart history | 90 points | ~1.5 min of history at 1 Hz |
| Table update | Incremental diff | Avoids full repaint every tick |
| pyqtgraph OpenGL | Off | Better compatibility across systems |

---

## License

MIT — free to use, modify and distribute.
