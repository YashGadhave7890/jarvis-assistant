"""
Advanced System Agent — full diagnostics: CPU, RAM, disk, battery, network, top processes.
"""

import asyncio
import logging
import platform
import socket
from agents.base_agent import BaseAgent
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class SystemAgent(BaseAgent):
    """
    Provides rich system status: CPU, RAM, disk, battery, network, top processes.
    """

    def __init__(self, event_bus: EventBus):
        super().__init__(name="System", event_bus=event_bus)

    async def execute(self, payload: dict) -> any:
        text   = payload.get("text", "").lower()
        intent = payload.get("intent", "system_status")

        logger.info(f"SystemAgent: text='{text}' intent='{intent}'")

        try:
            import psutil
        except ImportError:
            await self.emit_action("Action.Speak", {
                "text": "I need the psutil library for system monitoring, sir."
            })
            return

        # Route to sub-command based on keywords
        if any(w in text for w in ["battery", "charge", "charging"]):
            reply = await asyncio.to_thread(self._battery_status, psutil)
        elif any(w in text for w in ["disk", "storage", "space", "drive"]):
            reply = await asyncio.to_thread(self._disk_status, psutil)
        elif any(w in text for w in ["network", "internet", "ip", "wifi"]):
            reply = await asyncio.to_thread(self._network_status, psutil)
        elif any(w in text for w in ["process", "running apps", "top apps"]):
            reply = await asyncio.to_thread(self._top_processes, psutil)
        elif any(w in text for w in ["temperature", "temp", "heat"]):
            reply = await asyncio.to_thread(self._temperature_status, psutil)
        else:
            # Full overview
            reply = await asyncio.to_thread(self._full_status, psutil)

        await self.emit_action("Action.Speak", {"text": reply})
        return reply

    # ── Sub-routines ──────────────────────────────────────────────────────────
    def _full_status(self, psutil) -> str:
        cpu  = psutil.cpu_percent(interval=0.5)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        os_n = f"{platform.system()} {platform.release()}"

        ram_used  = ram.used  // (1024 ** 2)
        ram_total = ram.total // (1024 ** 2)
        disk_free = disk.free  // (1024 ** 3)

        parts = [
            f"System overview sir: running {os_n}.",
            f"CPU at {cpu:.0f} percent.",
            f"RAM: {ram_used} of {ram_total} megabytes used — {ram.percent:.0f} percent.",
            f"Disk: {disk_free} gigabytes free — {disk.percent:.0f} percent used.",
        ]

        # Battery if available
        bat = psutil.sensors_battery()
        if bat:
            status = "charging" if bat.power_plugged else "on battery"
            parts.append(f"Battery at {bat.percent:.0f} percent, {status}.")

        return " ".join(parts)

    def _battery_status(self, psutil) -> str:
        bat = psutil.sensors_battery()
        if not bat:
            return "This system doesn't appear to have a battery, sir."
        status    = "currently charging" if bat.power_plugged else "on battery power"
        pct       = bat.percent
        secs_left = bat.secsleft
        if secs_left > 0 and not bat.power_plugged:
            hrs  = secs_left // 3600
            mins = (secs_left % 3600) // 60
            time_str = f" Approximately {hrs} hours and {mins} minutes remaining."
        else:
            time_str = ""
        return f"Battery is at {pct:.0f} percent and {status}.{time_str}"

    def _disk_status(self, psutil) -> str:
        parts = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                free  = usage.free  // (1024 ** 3)
                total = usage.total // (1024 ** 3)
                parts.append(
                    f"Drive {part.device}: {free} GB free of {total} GB total, {usage.percent:.0f} percent used."
                )
            except PermissionError:
                continue
        if not parts:
            return "Could not read disk information, sir."
        return "Disk status sir: " + " ".join(parts)

    def _network_status(self, psutil) -> str:
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            hostname = "unknown"
            local_ip = "unknown"

        net_io = psutil.net_io_counters()
        sent   = net_io.bytes_sent  // (1024 ** 2)
        recv   = net_io.bytes_recv  // (1024 ** 2)

        return (
            f"Network status sir: hostname is {hostname}, local IP {local_ip}. "
            f"This session: sent {sent} MB, received {recv} MB."
        )

    def _top_processes(self, psutil) -> str:
        procs = []
        for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                continue
        # Sort by CPU desc
        procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
        top5 = procs[:5]
        if not top5:
            return "No processes found, sir."
        lines = [
            f"{p['name']} using {p.get('cpu_percent', 0):.1f}% CPU"
            for p in top5
        ]
        return "Top running processes sir: " + "; ".join(lines) + "."

    def _temperature_status(self, psutil) -> str:
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return "Temperature sensors are not available on this system, sir."
            parts = []
            for name, entries in temps.items():
                for e in entries:
                    parts.append(f"{name}: {e.current:.0f}°C")
            return "Temperature readings sir: " + ", ".join(parts) + "."
        except AttributeError:
            return "Temperature monitoring is not supported on Windows via this method, sir."
