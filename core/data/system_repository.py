"""core/data/system_repository.py"""
import os, platform, socket, sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import psutil


def fetch_cpu_percent() -> float:          return psutil.cpu_percent(interval=None)
def fetch_cpu_percent_per_core() -> list:
    try:    return psutil.cpu_percent(interval=None, percpu=True) or []
    except: return []

def fetch_cpu_freq() -> Optional[tuple]:
    try:
        f = psutil.cpu_freq()
        return (f.current or 0, f.min or 0, f.max or 0) if f else None
    except: return None

def fetch_cpu_freq_per_core() -> list:
    try:
        freqs = psutil.cpu_freq(percpu=True)
        return [(f.current, f.min, f.max) for f in freqs] if freqs else []
    except: return []

def fetch_cpu_count_physical() -> int: return psutil.cpu_count(logical=False) or 0
def fetch_cpu_count_logical()  -> int: return psutil.cpu_count(logical=True) or 0
def fetch_cpu_name()           -> str:
    try:    return platform.processor() or "—"
    except: return "—"

def fetch_cpu_times() -> dict:
    try:
        t = psutil.cpu_times_percent(interval=None)
        return {"user": getattr(t,"user",0), "system": getattr(t,"system",0),
                "idle": getattr(t,"idle",0), "iowait": getattr(t,"iowait",0)}
    except: return {"user":0,"system":0,"idle":0,"iowait":0}


def fetch_memory() -> tuple:
    v = psutil.virtual_memory()
    return v.percent, v.used/(1024**3), v.total/(1024**3)

def fetch_memory_details() -> dict:
    v = psutil.virtual_memory()
    r = {"total_gb": v.total/(1024**3), "available_gb": v.available/(1024**3),
         "used_gb":  v.used/(1024**3),  "percent": v.percent,
         "cached_gb":  getattr(v,"cached",0)/(1024**3),
         "buffers_gb": getattr(v,"buffers",0)/(1024**3)}
    try:
        sw = psutil.swap_memory()
        r.update({"swap_total_gb": sw.total/(1024**3),
                  "swap_used_gb":  sw.used/(1024**3), "swap_percent": sw.percent})
    except: r.update({"swap_total_gb":0,"swap_used_gb":0,"swap_percent":0})
    return r

def fetch_ram_total_gb() -> float:
    try:    return psutil.virtual_memory().total/(1024**3)
    except: return 0.0


def fetch_disk(path=None) -> tuple:
    if path is None: path = "C:\\" if os.name=="nt" else "/"
    if os.name=="nt":
        drive, _ = os.path.splitdrive(path)
        path = f"{drive.upper()}\\" if drive else "C:\\"
    d = psutil.disk_usage(path)
    return d.percent, d.used/(1024**3), d.total/(1024**3)

def fetch_disk_io() -> dict:
    try:
        io = psutil.disk_io_counters()
        if io: return {"read_bytes":io.read_bytes,"write_bytes":io.write_bytes,
                       "read_count":io.read_count,"write_count":io.write_count}
    except: pass
    return {"read_bytes":0,"write_bytes":0,"read_count":0,"write_count":0}

def fetch_disk_mount_choices() -> list:
    if os.name=="nt":
        drives = []
        try:
            for part in psutil.disk_partitions(all=False):
                m = part.mountpoint
                if m and len(m)>=2 and m[1]==":":
                    drives.append(f"{m[0].upper()}:\\")
        except: pass
        return sorted(set(drives)) or ["C:\\"]
    if sys.platform=="darwin":
        paths = ["/"]
        try:
            vol = Path("/Volumes")
            if vol.is_dir():
                for child in sorted(vol.iterdir()):
                    if child.is_dir():
                        try: psutil.disk_usage(str(child)); paths.append(str(child))
                        except: pass
        except: pass
        return paths
    return ["/"]

def fetch_disks() -> list:
    result = []
    try:
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
                result.append({"mountpoint":part.mountpoint,"fstype":part.fstype or "",
                                "total_gb":u.total/(1024**3),"used_gb":u.used/(1024**3),
                                "free_gb":u.free/(1024**3),"percent":u.percent})
            except: continue
    except: pass
    return result


def fetch_network_io() -> tuple:
    try:
        io = psutil.net_io_counters()
        return io.bytes_sent, io.bytes_recv
    except: return 0, 0

def fetch_network_io_per_interface() -> dict:
    result = {}
    try:
        for iface, c in (psutil.net_io_counters(pernic=True) or {}).items():
            result[iface] = {"bytes_sent":c.bytes_sent,"bytes_recv":c.bytes_recv,
                             "packets_sent":c.packets_sent,"packets_recv":c.packets_recv,
                             "errin":c.errin,"errout":c.errout}
    except: pass
    return result

def fetch_connections(kind="inet") -> list:
    result = []
    try:
        for c in psutil.net_connections(kind=kind):
            laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "—"
            raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "—"
            result.append({"laddr":laddr,"raddr":raddr,"status":c.status or "—",
                           "pid":c.pid or "—",
                           "type":"IPv6" if ":"in(c.laddr.ip if c.laddr else "") else "IPv4"})
    except (psutil.AccessDenied, PermissionError): pass
    return result

def fetch_network_interfaces() -> list:
    try:    return list(psutil.net_io_counters(pernic=True).keys())
    except: return []


def fetch_hostname() -> str:
    try:    return platform.node() or socket.gethostname() or "—"
    except: return "—"

def fetch_os_info() -> str:
    try:    return f"{platform.system()} {platform.release()} ({platform.version()})"
    except: return "—"

def fetch_architecture() -> str: return platform.machine() or "—"

def fetch_boot_time() -> Optional[datetime]:
    try:    return datetime.fromtimestamp(psutil.boot_time())
    except: return None

def fetch_process_count() -> int:
    try:    return len(psutil.pids())
    except: return 0
