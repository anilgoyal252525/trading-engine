from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StrategyOneParams:
    """
    Strategy-specific parameters loaded from settings.yml under `params:`.
    Add your own fields here.
    """
    fast_period: int = 9
    slow_period: int = 21
    entry_buffer_pts: float = 5.0

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyOneParams":
        return cls(
            fast_period=d.get("fast_period", 9),
            slow_period=d.get("slow_period", 21),
            entry_buffer_pts=d.get("entry_buffer_pts", 5.0),
        )