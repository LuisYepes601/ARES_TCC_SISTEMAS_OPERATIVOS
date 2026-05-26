"""core/utils/formatters.py"""
from datetime import datetime


def bytes_to_mb(b: int) -> str:   return f"{b/(1024**2):.1f} MB"
def bytes_to_gb(b: int) -> str:   return f"{b/(1024**3):.2f} GB"
def bytes_per_sec_human(bps: float) -> str:
    if bps < 1024:       return f"{bps:.0f} B/s"
    if bps < 1024**2:    return f"{bps/1024:.1f} KB/s"
    if bps < 1024**3:    return f"{bps/1024**2:.1f} MB/s"
    return               f"{bps/1024**3:.1f} GB/s"

def mhz_to_ghz_str(mhz: float) -> str:  return f"{mhz/1000:.2f} GHz"
def cpu_freq_str(freq) -> str:
    return mhz_to_ghz_str(freq[0]) if freq and freq[0] else "—"

def health_color(score: float) -> str:
    if score >= 85: return "#39d98a"
    if score >= 70: return "#7ae8b0"
    if score >= 50: return "#ffcb44"
    if score >= 30: return "#ff8c42"
    return "#ff4d6a"

def pct_to_status_color(pct: float) -> str:
    if pct >= 90: return "#ff4d6a"
    if pct >= 75: return "#ff8c42"
    if pct >= 50: return "#ffcb44"
    return "#39d98a"

def seconds_to_human(s: float) -> str:
    if s < 60:    return f"{s:.0f}s"
    if s < 3600:  return f"{s/60:.1f}min"
    if s < 86400: return f"{s/3600:.1f}h"
    return               f"{s/86400:.1f}d"

def timestamp_str(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d  %H:%M:%S") if dt else "—"

_PROCESS_STATUS = {
    "running":"Running","sleeping":"Sleeping","disk-sleep":"Disk sleep",
    "stopped":"Stopped","tracing-stop":"Tracing stop","dead":"Dead",
    "zombie":"Zombie","idle":"Idle","locked":"Locked",
    "waiting":"Waiting","suspended":"Suspended",
}
PROCESS_FILTER_KEYS = ("running","sleeping","disk-sleep","stopped","zombie")

def process_status_label(raw: str) -> str:
    return _PROCESS_STATUS.get((raw or "").lower(), raw) if raw else "—"

def process_status_color(raw: str) -> str:
    return {"running":"#39d98a","sleeping":"#4060e0","zombie":"#ff4d6a",
            "stopped":"#ffcb44","dead":"#2a2a50"}.get((raw or "").lower(), "#2a2a50")

def nice_to_label(nice: int) -> str:
    if nice <= -10: return "High"
    if nice < 0:    return "Above normal"
    if nice == 0:   return "Normal"
    if nice <= 10:  return "Low"
    return "Very Low"

_CONN_STATUS = {
    "ESTABLISHED":"Established","SYN_SENT":"SYN sent","SYN_RECV":"SYN recv",
    "FIN_WAIT1":"FIN wait 1","FIN_WAIT2":"FIN wait 2","TIME_WAIT":"Time wait",
    "CLOSE":"Closed","CLOSE_WAIT":"Close wait","LAST_ACK":"Last ACK",
    "LISTEN":"Listen","LISTENING":"Listening","CLOSING":"Closing","NONE":"None",
}
def connection_status_label(status: str) -> str:
    if not status or status in ("-","—"): return status or "—"
    return _CONN_STATUS.get(status.strip().upper(), status)

_SVC_STATUS = {
    "Running":"Running","Stopped":"Stopped","Paused":"Paused",
    "StartPending":"Starting","StopPending":"Stopping",
}
def service_status_label(status: str) -> str:
    return _SVC_STATUS.get((status or "").strip(), status or "—")
def service_status_color(status: str) -> str:
    return {"Running":"#39d98a","Stopped":"#ff4d6a","Paused":"#ffcb44"}.get(
        (status or "").strip(), "#2a2a50")
