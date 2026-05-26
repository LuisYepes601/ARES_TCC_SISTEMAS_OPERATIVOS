"""core/data/services_repository.py"""
import csv, io, os, subprocess

def is_windows(): return os.name == "nt"

def fetch_services() -> list:
    if not is_windows(): return []
    try:
        cmd = ["powershell","-NoProfile","-Command",
               "Get-Service | Select-Object Name,DisplayName,Status | ConvertTo-Csv -NoTypeInformation"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0: return []
        reader = csv.DictReader(io.StringIO(r.stdout))
        return [{"name":row.get("Name","").strip(),"display_name":row.get("DisplayName","").strip(),
                 "status":row.get("Status","").strip()} for row in reader]
    except: return []

def start_service(name: str) -> tuple:
    if not is_windows(): return False, "Windows only."
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",f"Start-Service -Name '{name}'"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0: return True, "Service started."
        msg = (r.stderr or r.stdout or "Error").strip()
        if "Access" in msg: msg = "Access denied. Run Ares as Administrator."
        return False, msg
    except subprocess.TimeoutExpired: return False, "Timeout."
    except Exception as e: return False, str(e)

def stop_service(name: str) -> tuple:
    if not is_windows(): return False, "Windows only."
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",f"Stop-Service -Name '{name}' -Force"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0: return True, "Service stopped."
        msg = (r.stderr or r.stdout or "Error").strip()
        if "Access" in msg: msg = "Access denied. Run Ares as Administrator."
        return False, msg
    except subprocess.TimeoutExpired: return False, "Timeout."
    except Exception as e: return False, str(e)
