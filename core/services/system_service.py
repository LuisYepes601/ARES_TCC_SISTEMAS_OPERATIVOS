"""core/services/system_service.py"""
import time
from datetime import datetime
from typing import Optional
from core.data.system_repository import *

_CACHE: dict = {}
_TTL = 0.4

def _cached(key, fn, *args):
    now = time.time()
    if key in _CACHE:
        v, ts = _CACHE[key]
        if now - ts < _TTL: return v
    v = fn(*args); _CACHE[key] = (v, now); return v

def get_cpu_percent()           -> float:        return _cached("cpu_pct",    fetch_cpu_percent)
def get_cpu_percent_per_core()  -> list:         return _cached("cpu_cores",  fetch_cpu_percent_per_core)
def get_cpu_freq()                              : return _cached("cpu_freq",   fetch_cpu_freq)
def get_cpu_freq_per_core()     -> list:         return _cached("cpu_freq_pc", fetch_cpu_freq_per_core)
def get_cpu_count_physical()    -> int:          return fetch_cpu_count_physical()
def get_cpu_count_logical()     -> int:          return fetch_cpu_count_logical()
def get_cpu_name()              -> str:          return fetch_cpu_name()
def get_cpu_times()             -> dict:         return _cached("cpu_times",  fetch_cpu_times)

def get_memory_info()           -> tuple:        return _cached("mem_info",   fetch_memory)
def get_memory_details()        -> dict:         return _cached("mem_det",    fetch_memory_details)
def get_ram_total_gb()          -> float:        return fetch_ram_total_gb()

def get_disk_info(path=None)    -> tuple:        return fetch_disk(path)
def get_disk_io()               -> dict:         return _cached("disk_io",    fetch_disk_io)
def get_disk_mount_choices()    -> list:         return fetch_disk_mount_choices()
def get_disks()                 -> list:         return _cached("disks",      fetch_disks)

def get_network_io()            -> tuple:        return _cached("net_io",     fetch_network_io)
def get_network_io_per_interface() -> dict:      return _cached("net_ifaces", fetch_network_io_per_interface)
def get_network_interfaces()    -> list:         return fetch_network_interfaces()
def get_connections(kind="inet")-> list:         return fetch_connections(kind)

def get_hostname()              -> str:          return fetch_hostname()
def get_os_info()               -> str:          return fetch_os_info()
def get_architecture()          -> str:          return fetch_architecture()
def get_boot_time()                            : return fetch_boot_time()
def get_uptime_seconds()        -> float:
    boot = fetch_boot_time()
    if not boot: return 0.0
    return (datetime.now() - boot).total_seconds()

def get_uptime_str() -> str:
    s = get_uptime_seconds()
    if s <= 0: return "—"
    d = int(s // 86400); h = int((s%86400)//3600); m = int((s%3600)//60)
    return f"{d}d {h:02d}:{m:02d}" if d else f"{h:02d}:{m:02d}"

def get_process_count() -> int: return fetch_process_count()

def get_system_health_score(cpu, mem, disk) -> tuple[float, str]:
    cpu_s  = max(0.0, 100.0 - max(0.0, cpu  - 30.0) * 1.5)
    mem_s  = max(0.0, 100.0 - max(0.0, mem  - 40.0) * 1.5)
    disk_s = max(0.0, 100.0 - max(0.0, disk - 60.0) * 2.0)
    score  = max(0.0, min(100.0, cpu_s*0.4 + mem_s*0.4 + disk_s*0.2))
    desc   = ("Excellent" if score>=85 else "Good" if score>=70 else
              "Fair" if score>=50 else "Elevated" if score>=30 else "Critical")
    return score, desc

def compute_network_rates(prev_io, prev_time, wifi_max_mbps=100.0):
    sent, recv = fetch_network_io()
    now = time.perf_counter()
    if prev_time and now > prev_time:
        dt = now - prev_time
        sr = (sent - prev_io[0]) / dt; rr = (recv - prev_io[1]) / dt
        mbps = (sr + rr) / (1024*1024) * 8
        pct  = min(100.0, mbps / (wifi_max_mbps or 100) * 100)
    else:
        sr = rr = mbps = pct = 0.0
    return sr, rr, mbps, pct
