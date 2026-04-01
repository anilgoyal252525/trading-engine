from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from ..data_model import Signal, TradeData


class IOrderBroker(ABC):

    @abstractmethod
    async def connect(self) -> None:
        """Establish session / auth."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close session."""

    @abstractmethod
    async def place_order(self, signal: Signal) -> str:
        """Place order. Returns broker order_id."""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order. Returns True on success."""

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict:
        """Raw order status dict from broker."""

    @abstractmethod
    async def get_positions(self) -> List[TradeData]:
        """Current open positions."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return session state."""