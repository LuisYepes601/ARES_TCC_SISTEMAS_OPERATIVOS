"""core/data/alerts_repository.py"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AlertLevel(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    level:     AlertLevel
    category:  str
    title:     str
    message:   str
    timestamp: datetime = field(default_factory=datetime.now)
    dismissed: bool     = False

    def age_seconds(self) -> float:
        return (datetime.now() - self.timestamp).total_seconds()


_MAX_ALERTS = 200
_alert_store: deque[Alert] = deque(maxlen=_MAX_ALERTS)


def add_alert(level: AlertLevel, category: str, title: str, message: str) -> Alert:
    alert = Alert(level=level, category=category, title=title, message=message)
    _alert_store.appendleft(alert)
    return alert


def fetch_alerts(*, include_dismissed: bool = False, max_count: int = 100) -> list[Alert]:
    result = [a for a in _alert_store if include_dismissed or not a.dismissed]
    return result[:max_count]


def dismiss_alert(alert: Alert) -> None:
    alert.dismissed = True


def dismiss_all() -> None:
    for a in _alert_store:
        a.dismissed = True


def clear_all() -> None:
    _alert_store.clear()


def count_active(level: AlertLevel | None = None) -> int:
    return sum(1 for a in _alert_store if not a.dismissed and (level is None or a.level == level))
