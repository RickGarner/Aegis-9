import ctypes
import sys
from ctypes import wintypes

from pydantic import BaseModel, Field


class MonitorWorkArea(BaseModel):
    slot: int = Field(ge=1)
    left: int
    top: int
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class WorkflowWindowPlacement(BaseModel):
    workflow_id: int
    title: str
    state: str
    monitor: MonitorWorkArea
    window_state: str = "planned"


class TopologyReconciliation(BaseModel):
    changed: bool
    topology_fingerprint: str
    requeued_workflow_ids: list[int] = []


class WorkflowCapacity(BaseModel):
    detected_monitors: int | None
    configured_limit: int = Field(ge=1, le=6)
    effective_capacity: int = Field(ge=1, le=6)
    detection_source: str
    monitors: list[MonitorWorkArea] = []

    @property
    def topology_fingerprint(self) -> str:
        return "|".join(
            f"{monitor.slot}:{monitor.left},{monitor.top},{monitor.width},{monitor.height}"
            for monitor in self.monitors
        ) or "fallback"


def get_workflow_capacity(configured_limit: int) -> WorkflowCapacity:
    monitors = _get_windows_monitor_work_areas()
    if not monitors:
        return WorkflowCapacity(
            detected_monitors=None,
            configured_limit=configured_limit,
            effective_capacity=min(4, configured_limit),
            detection_source="fallback",
        )

    return WorkflowCapacity(
        detected_monitors=len(monitors),
        configured_limit=configured_limit,
        effective_capacity=min(len(monitors), configured_limit, 6),
        detection_source="windows-display-topology",
        monitors=monitors[:6],
    )


def _get_windows_monitor_work_areas() -> list[MonitorWorkArea]:
    if sys.platform != "win32":
        return []

    class MonitorInfo(ctypes.Structure):
        _fields_ = [
            ("cb_size", ctypes.c_ulong),
            ("rc_monitor", wintypes.RECT),
            ("rc_work", wintypes.RECT),
            ("flags", ctypes.c_ulong),
        ]

    monitor_work_areas: list[MonitorWorkArea] = []

    @ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.RECT),
        ctypes.c_ssize_t,
    )
    def collect_monitor_work_area(monitor_handle, _device_context, _monitor_rect, _data):
        monitor_info = MonitorInfo()
        monitor_info.cb_size = ctypes.sizeof(MonitorInfo)
        if ctypes.windll.user32.GetMonitorInfoW(monitor_handle, ctypes.byref(monitor_info)):
            work_area = monitor_info.rc_work
            monitor_work_areas.append(
                MonitorWorkArea(
                    slot=len(monitor_work_areas) + 1,
                    left=work_area.left,
                    top=work_area.top,
                    width=work_area.right - work_area.left,
                    height=work_area.bottom - work_area.top,
                )
            )
        return 1

    try:
        ctypes.windll.user32.EnumDisplayMonitors(None, None, collect_monitor_work_area, 0)
    except (AttributeError, OSError):
        return []

    return monitor_work_areas