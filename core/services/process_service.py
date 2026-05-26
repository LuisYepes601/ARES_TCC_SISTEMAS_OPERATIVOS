"""core/services/process_service.py"""
import csv, io
from core.data.process_repository import (
    NICE_PRESETS, fetch_process_details, fetch_processes, fetch_process_exe,
    kill_process_tree, open_exe_folder, resume_process, set_process_priority,
    suspend_process, terminate_process,
)

SORT_BY_CPU    = "cpu"
SORT_BY_MEMORY = "memory"
SORT_BY_NAME   = "name"
SORT_BY_PID    = "pid"


def get_processes(sort_by=SORT_BY_CPU) -> list[dict]:
    procs = fetch_processes()
    if sort_by == SORT_BY_CPU:    procs.sort(key=lambda x: x["cpu"],    reverse=True)
    elif sort_by == SORT_BY_MEMORY: procs.sort(key=lambda x: x["memory"], reverse=True)
    elif sort_by == SORT_BY_NAME: procs.sort(key=lambda x: (x["name"] or "").lower())
    else:                         procs.sort(key=lambda x: x["pid"] or 0)
    return procs

def get_process_exe_path(pid: int) -> str | None: return fetch_process_exe(pid)
def get_process_details(pid: int) -> dict | None:  return fetch_process_details(pid)
def kill_process(pid: int)        -> tuple:        return terminate_process(pid)
def kill_process_and_children(pid: int) -> tuple:  return kill_process_tree(pid)
def change_priority(pid: int, label: str) -> tuple:
    nice = NICE_PRESETS.get(label)
    if nice is None: return False, f"Unknown priority: '{label}'"
    return set_process_priority(pid, nice)
def suspend(pid: int) -> tuple: return suspend_process(pid)
def resume(pid: int)  -> tuple: return resume_process(pid)
def open_process_folder(exe_path: str) -> tuple: return open_exe_folder(exe_path)
def get_priority_options() -> list[str]: return list(NICE_PRESETS.keys())
def get_top_processes(n=5, by=SORT_BY_CPU) -> list[dict]: return get_processes(sort_by=by)[:n]

def export_processes_csv() -> str:
    procs  = get_processes()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["pid","name","cpu","memory","status","threads","nice"], extrasaction="ignore")
    writer.writeheader(); writer.writerows(procs)
    return output.getvalue()
