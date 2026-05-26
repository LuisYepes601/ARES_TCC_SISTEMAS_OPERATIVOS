"""core/data/process_repository.py"""
import os, subprocess, sys
from typing import Optional
import psutil

PRIORITY_MAP = {-20:"Real Time",-10:"High",0:"Normal",10:"Low",19:"Very Low"}
NICE_PRESETS = {"Tiempo Real":-20,"Alto":-10,"Normal":0,"Bajo":10,"Muy Bajo":19,
                "Real Time":-20,"High":-10,"Low":10,"Very Low":19}


def fetch_processes() -> list[dict]:
    result = []
    for proc in psutil.process_iter(["pid","name","cpu_percent","memory_percent","status","nice","num_threads"]):
        try:
            info = proc.info
            exe_path = None
            try: exe_path = proc.exe()
            except Exception: pass
            result.append({
                "pid":     info.get("pid"),
                "name":    (info.get("name") or "")[:80],
                "cpu":     float(info.get("cpu_percent") or 0),
                "memory":  float(info.get("memory_percent") or 0),
                "status":  info.get("status") or "",
                "exe_path": exe_path,
                "nice":    info.get("nice") or 0,
                "threads": info.get("num_threads") or 0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return result


def fetch_process_exe(pid: int) -> str | None:
    try: return psutil.Process(pid).exe()
    except Exception: return None


def fetch_process_details(pid: int) -> dict | None:
    try:
        p   = psutil.Process(pid)
        mem = p.memory_info()
        return {
            "pid": p.pid, "name": p.name(), "status": p.status(),
            "create_time": p.create_time(), "cpu_times": p.cpu_times(),
            "mem_rss_mb": mem.rss/(1024**2), "mem_vms_mb": mem.vms/(1024**2),
            "num_threads": p.num_threads(),
            "children": [c.pid for c in p.children()],
            "username": _safe(p.username),
            "cmdline":  _safe(lambda: " ".join(p.cmdline())),
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def _safe(fn):
    try: return fn() if callable(fn) else fn
    except Exception: return "—"


def terminate_process(pid: int) -> tuple[bool, str]:
    try: psutil.Process(pid).terminate(); return True, "Process terminated."
    except psutil.NoSuchProcess: return False, "Process no longer exists."
    except psutil.AccessDenied:  return False, f"Access denied.\n{_hint()}"
    except Exception as e:       return False, str(e)


def kill_process_tree(pid: int) -> tuple[bool, str]:
    try:
        parent   = psutil.Process(pid)
        children = parent.children(recursive=True)
        for c in children:
            try: c.kill()
            except Exception: pass
        parent.kill()
        return True, f"Process tree killed ({len(children)+1} processes)."
    except psutil.NoSuchProcess: return False, "Process no longer exists."
    except psutil.AccessDenied:  return False, f"Access denied.\n{_hint()}"
    except Exception as e:       return False, str(e)


def set_process_priority(pid: int, nice: int) -> tuple[bool, str]:
    try: psutil.Process(pid).nice(nice); return True, f"Priority set (nice={nice})."
    except psutil.NoSuchProcess: return False, "Process no longer exists."
    except psutil.AccessDenied:  return False, f"Access denied.\n{_hint()}"
    except Exception as e:       return False, str(e)


def suspend_process(pid: int) -> tuple[bool, str]:
    try: psutil.Process(pid).suspend(); return True, "Process suspended."
    except psutil.NoSuchProcess: return False, "Process no longer exists."
    except psutil.AccessDenied:  return False, "Access denied."
    except Exception as e:       return False, str(e)


def resume_process(pid: int) -> tuple[bool, str]:
    try: psutil.Process(pid).resume(); return True, "Process resumed."
    except psutil.NoSuchProcess: return False, "Process no longer exists."
    except psutil.AccessDenied:  return False, "Access denied."
    except Exception as e:       return False, str(e)


def open_exe_folder(exe_path: str) -> tuple[bool, str]:
    if not exe_path or not os.path.isfile(exe_path): return False, "Invalid path."
    try:
        if os.name == "nt":         subprocess.Popen(["explorer", "/select,"+exe_path])
        elif sys.platform=="darwin": subprocess.Popen(["open","-R",exe_path])
        else:                        subprocess.Popen(["xdg-open", os.path.dirname(exe_path)])
        return True, "Location opened."
    except Exception as e: return False, str(e)


def _hint() -> str:
    if sys.platform=="darwin": return "Some system processes cannot be modified on macOS."
    if os.name=="nt":          return "Re-open Ares as Administrator."
    return "Elevated permissions may be required."
