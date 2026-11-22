from __future__ import annotations

from enum import Enum, IntEnum


class Priority(IntEnum):
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3


class Freshness(str, Enum):
    CURRENT = "CURRENT"
    LAST_KNOWN = "LAST_KNOWN"
    STALE = "STALE"
    GAP = "GAP"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"


class Availability(str, Enum):
    WIRED = "WIRED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    UNCONFIGURED = "UNCONFIGURED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class CommandStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    RECORDED = "RECORDED"
    REJECTED = "REJECTED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
