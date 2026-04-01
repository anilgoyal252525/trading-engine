from __future__ import annotations

import importlib
import logging
from typing import Dict, List, Type

from ..core.interfaces.istrategy import IStrategy
from ..infrastructure.config_loader import StrategyConfig

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Dynamically loads strategy classes from config.
    Convention: src/strategies/{module}/handler.py must contain
    a class named `Handler` that implements IStrategy.
    """

    @staticmethod
    def load(configs: List[StrategyConfig]) -> List[IStrategy]:
        strategies: List[IStrategy] = []
        for cfg in configs:
            if not cfg.enabled:
                logger.info("Skipping disabled strategy: %s", cfg.id)
                continue
            try:
                module = importlib.import_module(
                    f"src.strategies.{cfg.module}.handler"
                )
                handler_cls: Type[IStrategy] = module.Handler
                instance = handler_cls(cfg)
                strategies.append(instance)
                logger.info("Loaded strategy: %s", cfg.id)
            except Exception:
                logger.exception("Failed to load strategy: %s", cfg.id)
        return strategies