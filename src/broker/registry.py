from __future__ import annotations

from typing import Any, Dict, Type

from ..core.interfaces.idata_broker import IDataBroker
from ..core.interfaces.iorder_broker import IOrderBroker

_DATA_REGISTRY: Dict[str, Type[IDataBroker]] = {}
_ORDER_REGISTRY: Dict[str, Type[IOrderBroker]] = {}


def register_data_broker(name: str):
    """Class decorator — @register_data_broker("fyers")"""
    def decorator(cls: Type[IDataBroker]) -> Type[IDataBroker]:
        _DATA_REGISTRY[name.lower()] = cls
        return cls
    return decorator


def register_order_broker(name: str):
    """Class decorator — @register_order_broker("fyers")"""
    def decorator(cls: Type[IOrderBroker]) -> Type[IOrderBroker]:
        _ORDER_REGISTRY[name.lower()] = cls
        return cls
    return decorator


class BrokerRegistry:

    @staticmethod
    def get_data_broker(name: str, **kwargs: Any) -> IDataBroker:
        key = name.lower()
        if key not in _DATA_REGISTRY:
            available = list(_DATA_REGISTRY.keys())
            raise ValueError(f"Data broker '{name}' not registered. Available: {available}")
        return _DATA_REGISTRY[key](**kwargs)

    @staticmethod
    def get_order_broker(name: str, **kwargs: Any) -> IOrderBroker:
        key = name.lower()
        if key not in _ORDER_REGISTRY:
            available = list(_ORDER_REGISTRY.keys())
            raise ValueError(f"Order broker '{name}' not registered. Available: {available}")
        return _ORDER_REGISTRY[key](**kwargs)