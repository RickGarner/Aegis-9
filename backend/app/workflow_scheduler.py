import os
import socket
import calendar
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.storage import Workflow


class ScheduleError(ValueError):
    pass


def is_due(workflow: Workflow, now: datetime | None = None) -> bool:
    schedule = workflow.schedule
    if workflow.state != "scheduled" or not schedule:
        return False
    now = now or datetime.now(timezone.utc)
    timezone_name = str(schedule.get("timezone") or "UTC")
    try:
        schedule_timezone = timezone.utc if timezone_name.casefold() in {"utc", "etc/utc"} else ZoneInfo(timezone_name)
        local_now = now.astimezone(schedule_timezone)
    except ZoneInfoNotFoundError as error:
        raise ScheduleError(f"Unknown timezone: {timezone_name}. Install the Python tzdata package for IANA timezone support on Windows.") from error
    last = datetime.fromisoformat(workflow.last_run_at.replace("Z", "+00:00")) if workflow.last_run_at else None
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    trigger = str(schedule.get("trigger") or "manual").casefold()
    expression = str(schedule.get("expression") or "").strip()
    if trigger == "manual":
        return False
    if trigger in {"recurring", "once"} and schedule.get("start_date"):
        try:
            start_date = datetime.strptime(str(schedule["start_date"]), "%Y-%m-%d").date()
            end_date = datetime.strptime(str(schedule["end_date"]), "%Y-%m-%d").date() if schedule.get("end_date") else None
            start_clock = datetime.strptime(str(schedule.get("start_time") or "00:00"), "%H:%M").time()
            end_clock = datetime.strptime(str(schedule.get("end_time") or "23:59"), "%H:%M").time()
        except ValueError as error:
            raise ScheduleError("Calendar schedules require YYYY-MM-DD dates and HH:mm times.") from error
        if local_now.date() < start_date or (end_date and local_now.date() > end_date):
            return False
        first_run = datetime.combine(start_date, start_clock, schedule_timezone)
        if local_now < first_run:
            return False
        if trigger == "once":
            return last is None or last.astimezone(schedule_timezone) < first_run
        within_window = start_clock <= local_now.time() <= end_clock if start_clock <= end_clock else (local_now.time() >= start_clock or local_now.time() <= end_clock)
        if not within_window:
            return False
        if last is None:
            return True
        value = int(schedule.get("interval_value") or 1)
        unit = str(schedule.get("interval_unit") or "days").casefold()
        if value < 1:
            raise ScheduleError("Recurrence interval must be at least one.")
        last_local = last.astimezone(schedule_timezone)
        if unit == "minutes": next_run = last_local + timedelta(minutes=value)
        elif unit == "hours": next_run = last_local + timedelta(hours=value)
        elif unit == "days": next_run = last_local + timedelta(days=value)
        elif unit == "weeks": next_run = last_local + timedelta(weeks=value)
        elif unit == "months": next_run = _add_months(last_local, value)
        else: raise ScheduleError(f"Unsupported recurrence unit '{unit}'.")
        return local_now >= next_run
    if trigger == "daily":
        try:
            hour, minute = (int(part) for part in expression.split(":"))
            scheduled_local = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (TypeError, ValueError) as error:
            raise ScheduleError("Daily expression must use 24-hour HH:mm format.") from error
        if local_now < scheduled_local:
            return False
        scheduled_utc = scheduled_local.astimezone(timezone.utc)
        return last is None or last.astimezone(timezone.utc) < scheduled_utc
    if trigger == "once":
        try:
            scheduled_local = datetime.fromisoformat(expression).replace(tzinfo=local_now.tzinfo)
        except ValueError as error:
            raise ScheduleError("Once expression must use YYYY-MM-DD HH:mm format.") from error
        scheduled_utc = scheduled_local.astimezone(timezone.utc)
        return now >= scheduled_utc and (last is None or last.astimezone(timezone.utc) < scheduled_utc)
    if trigger == "weekly":
        try:
            day_text, time_text = expression.split(maxsplit=1)
            weekday = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}[day_text[:3].casefold()]
            hour, minute = (int(part) for part in time_text.split(":"))
        except (KeyError, TypeError, ValueError) as error:
            raise ScheduleError("Weekly expression must use a weekday and 24-hour time, such as Mon 07:00.") from error
        days_back = (local_now.weekday() - weekday) % 7
        scheduled_local = (local_now - timedelta(days=days_back)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if local_now < scheduled_local:
            scheduled_local -= timedelta(days=7)
        scheduled_utc = scheduled_local.astimezone(timezone.utc)
        return last is None or last.astimezone(timezone.utc) < scheduled_utc
    if trigger == "interval":
        normalized = expression.casefold().removesuffix("minutes").removesuffix("minute").removesuffix("m").strip()
        try:
            minutes = int(normalized)
        except ValueError as error:
            raise ScheduleError("Interval expression must be a whole number of minutes, such as 15m.") from error
        if minutes < 1:
            raise ScheduleError("Interval must be at least one minute.")
        return last is None or now - last.astimezone(timezone.utc) >= timedelta(minutes=minutes)
    raise ScheduleError(f"Unsupported schedule trigger '{trigger}'.")


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def prerequisites_met(schedule: dict) -> tuple[bool, str]:
    source = str(schedule.get("start_conditions") or "").strip()
    if not source or source.casefold() == "always":
        return True, "No blocking prerequisites."
    for condition in (item.strip() for item in source.split(";") if item.strip()):
        key, separator, value = condition.partition("=")
        if not separator or not value.strip():
            return False, f"Unsupported prerequisite '{condition}'. Use key=value declarative conditions."
        key, value = key.strip().casefold(), value.strip()
        if key == "file_exists":
            if not Path(value).is_file(): return False, f"Required file is unavailable: {value}"
        elif key == "env_present":
            if not os.environ.get(value): return False, f"Required environment setting is unavailable: {value}"
        elif key == "host_reachable":
            host, colon, port_text = value.rpartition(":")
            if not colon: return False, "host_reachable must use host:port."
            try:
                with socket.create_connection((host, int(port_text)), timeout=2): pass
            except (OSError, ValueError): return False, f"Required endpoint is unavailable: {value}"
        else:
            return False, f"Unsupported prerequisite type '{key}'."
    return True, "Every declarative prerequisite passed."
