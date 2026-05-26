"""
core/workers/data_worker.py
Hilo de fondo de alta frecuencia para recolección no bloqueante de métricas.
Emite señales con datos frescos; la UI nunca llama a psutil directamente.
"""
from __future__ import annotations
import time
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal

from core.services.system_service import (
    get_cpu_percent,
    get_cpu_percent_per_core,
    get_cpu_freq,
    get_disk_info,
    get_disk_io,
    get_memory_details,
    get_memory_info,
    get_network_io,
    get_uptime_str,
    get_process_count,
    get_system_health_score,
)
from core.services.gpu_service import get_gpu_info
from core.services.process_service import get_processes
from core.services.alerts_service import check_all


class DataWorker(QThread):
    """
    Recolecta métricas del sistema en background y emite señales.
    system_interval : segundos entre actualizaciones de CPU/mem/disco/red/GPU
    process_interval: segundos entre actualizaciones de la lista de procesos
    """

    system_ready  = pyqtSignal(dict)   # métricas del sistema
    process_ready = pyqtSignal(list)   # lista de procesos

    def __init__(
        self,
        system_interval: float = 1.0,
        process_interval: float = 3.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._sys_interval  = max(0.25, system_interval)
        self._proc_interval = max(1.0,  process_interval)
        self._running       = True
        self._last_proc_t   = 0.0
        self._last_net_io   : tuple[int, int] = (0, 0)
        self._last_net_t    : float = 0.0
        self._disk_path     : str = "/"
        self._wifi_max_mbps : float = 100.0

    def set_disk_path(self, path: str) -> None:
        self._disk_path = path

    def set_wifi_max(self, mbps: float) -> None:
        self._wifi_max_mbps = max(1.0, mbps)

    def stop(self) -> None:
        self._running = False
        self.quit()
        self.wait(2000)

    # ------------------------------------------------------------------
    def run(self) -> None:
        while self._running:
            t0 = time.perf_counter()

            try:
                self._emit_system()
            except Exception:
                pass

            now = time.perf_counter()
            if now - self._last_proc_t >= self._proc_interval:
                try:
                    procs = get_processes(sort_by="cpu")
                    self.process_ready.emit(procs)
                except Exception:
                    pass
                self._last_proc_t = now

            elapsed   = time.perf_counter() - t0
            sleep_ms  = max(50, int((self._sys_interval - elapsed) * 1000))
            self.msleep(sleep_ms)

    # ------------------------------------------------------------------
    def _emit_system(self) -> None:
        cpu        = get_cpu_percent()
        cores      = get_cpu_percent_per_core()
        freq       = get_cpu_freq()
        mem_pct, mem_used, mem_total = get_memory_info()
        mem_det    = get_memory_details()
        disk_pct, disk_used, disk_total = get_disk_info(self._disk_path)
        disk_io    = get_disk_io()
        sent, recv = get_network_io()
        now        = time.perf_counter()

        sent_rate = recv_rate = net_mbps = net_pct = 0.0
        if self._last_net_t > 0 and now > self._last_net_t:
            dt         = now - self._last_net_t
            sent_rate  = max(0.0, (sent - self._last_net_io[0]) / dt)
            recv_rate  = max(0.0, (recv - self._last_net_io[1]) / dt)
            net_mbps   = (sent_rate + recv_rate) / (1024 * 1024) * 8
            net_pct    = min(100.0, net_mbps / self._wifi_max_mbps * 100.0)
        self._last_net_io = (sent, recv)
        self._last_net_t  = now

        gpu_pct, gpu_name = get_gpu_info()
        score, health_desc = get_system_health_score(cpu, mem_pct, disk_pct)

        check_all(cpu, mem_pct, disk_pct, gpu_pct, self._disk_path)

        self.system_ready.emit({
            "cpu"        : cpu,
            "cores"      : cores,
            "freq"       : freq,
            "mem_pct"    : mem_pct,
            "mem_used"   : mem_used,
            "mem_total"  : mem_total,
            "mem_det"    : mem_det,
            "disk_pct"   : disk_pct,
            "disk_used"  : disk_used,
            "disk_total" : disk_total,
            "disk_path"  : self._disk_path,
            "disk_io"    : disk_io,
            "net_sent_r" : sent_rate,
            "net_recv_r" : recv_rate,
            "net_mbps"   : net_mbps,
            "net_pct"    : net_pct,
            "gpu_pct"    : gpu_pct,
            "gpu_name"   : gpu_name,
            "health"     : score,
            "health_desc": health_desc,
            "uptime"     : get_uptime_str(),
            "proc_count" : get_process_count(),
        })
