"""core/services/alerts_service.py"""
from __future__ import annotations
from dataclasses import dataclass
from core.data.alerts_repository import (
    Alert, AlertLevel, add_alert, count_active, dismiss_alert,
    dismiss_all, clear_all, fetch_alerts,
)


@dataclass
class AlertThresholds:
    cpu_warning:     float = 75.0
    cpu_critical:    float = 90.0
    memory_warning:  float = 80.0
    memory_critical: float = 92.0
    disk_warning:    float = 85.0
    disk_critical:   float = 95.0
    gpu_warning:     float = 80.0
    gpu_critical:    float = 95.0


_thresholds = AlertThresholds()
_last_alert_key: dict[str, float] = {}
_DEDUP_SECONDS = 60.0


def get_thresholds() -> AlertThresholds: return _thresholds

def update_thresholds(**kwargs) -> None:
    for k, v in kwargs.items():
        if hasattr(_thresholds, k): setattr(_thresholds, k, float(v))

def check_cpu(cpu_pct: float)              -> Alert | None: return _check("cpu",    cpu_pct, "CPU",    "% CPU usage")
def check_memory(mem_pct: float)           -> Alert | None: return _check("memory", mem_pct, "Memory", "% RAM usage")
def check_disk(disk_pct: float, mp="/")    -> Alert | None: return _check(f"disk:{mp}", disk_pct, f"Disk ({mp})", f"% disk {mp}")
def check_gpu(gpu_pct: float | None)       -> Alert | None:
    if gpu_pct is None: return None
    return _check("gpu", gpu_pct, "GPU", "% GPU usage")

def check_all(cpu, mem, disk, gpu=None, disk_mp="/") -> list[Alert]:
    return [a for a in [check_cpu(cpu), check_memory(mem), check_disk(disk, disk_mp), check_gpu(gpu)] if a]

def add_process_alert(title: str, message: str, level=AlertLevel.INFO) -> Alert:
    return add_alert(level, "process", title, message)

def get_alerts(*, include_dismissed=False) -> list[Alert]: return fetch_alerts(include_dismissed=include_dismissed)
def get_active_count() -> int:   return count_active()
def get_critical_count() -> int: return count_active(AlertLevel.CRITICAL)
def dismiss(alert: Alert)  -> None: dismiss_alert(alert)
def dismiss_all_alerts()   -> None: dismiss_all()
def clear_alerts()         -> None: clear_all()


def _check(category, value, resource_name, value_label) -> Alert | None:
    import time
    t = _thresholds; base = category.split(":")[0]
    warn = getattr(t, f"{base}_warning",  75.0)
    crit = getattr(t, f"{base}_critical", 90.0)
    if value >= crit:
        level = AlertLevel.CRITICAL; title = f"🔴 {resource_name} critical"
    elif value >= warn:
        level = AlertLevel.WARNING;  title = f"🟡 {resource_name} high"
    else:
        _last_alert_key.pop(f"{category}:{AlertLevel.WARNING}",  None)
        _last_alert_key.pop(f"{category}:{AlertLevel.CRITICAL}", None)
        return None
    key  = f"{category}:{level}"
    now  = time.monotonic()
    if now - _last_alert_key.get(key, 0) < _DEDUP_SECONDS: return None
    _last_alert_key[key] = now
    msg = f"{value_label}: {value:.1f}% (threshold {crit if level==AlertLevel.CRITICAL else warn:.0f}%)"
    return add_alert(level, base, title, msg)
