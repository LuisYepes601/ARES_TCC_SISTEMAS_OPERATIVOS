"""core/services/services_service.py"""
import os
from core.data.services_repository import fetch_services, start_service as _s, stop_service as _stop

def is_services_available() -> bool: return os.name == "nt"
def get_services()          -> list: return fetch_services()
def start_service(name: str) -> tuple:
    if not name.strip(): return False, "Empty service name."
    return _s(name.strip())
def stop_service(name: str) -> tuple:
    if not name.strip(): return False, "Empty service name."
    return _stop(name.strip())
