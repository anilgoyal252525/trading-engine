from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class SymbolConfig:
    name: str
    mode: str           # "tick" | "candle"
    timeframe: int = 1  # minutes, only relevant for candle mode


@dataclass
class StrategyConfig:
    id: str
    module: str
    enabled: bool = True
    max_trades: int = 1
    symbols: List[SymbolConfig] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerConfig:
    data: str
    order: str


@dataclass
class AppConfig:
    brokers: BrokerConfig
    strategies: List[StrategyConfig]


def load_config(path: str = "config/settings.yml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path.resolve()}")

    with config_path.open() as f:
        raw: Dict = yaml.safe_load(f)

    # --- brokers ---
    broker_raw = raw.get("brokers", {})
    brokers = BrokerConfig(
        data=broker_raw["data"],
        order=broker_raw["order"],
    )

    # --- strategies ---
    strategies: List[StrategyConfig] = []
    for s in raw.get("strategies", []):
        symbols = [
            SymbolConfig(
                name=sym["name"],
                mode=sym.get("mode", "candle"),
                timeframe=int(sym.get("timeframe", 1)),
            )
            for sym in s.get("symbols", [])
        ]
        strategies.append(
            StrategyConfig(
                id=s["id"],
                module=s["module"],
                enabled=s.get("enabled", True),
                max_trades=s.get("max_trades", 1),
                symbols=symbols,
                params=s.get("params", {}),
            )
        )

    return AppConfig(brokers=brokers, strategies=strategies)