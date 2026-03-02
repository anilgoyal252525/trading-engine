# error_handling.py
import asyncio
import functools
import inspect
import traceback
from collections.abc import Callable
from typing import Any, TypeVar
from src.infrastructure.logger import logger

T = TypeVar('T')

class ErrorHandling:
    __slots__ = ('retries', 're_raise', 'backoff', 'exclude')
    
    def __init__(
        self,
        retries: int = 0,
        re_raise: bool = False,
        backoff: float = 0,
        exclude: frozenset[str] = frozenset()
    ):
        self.retries = retries
        self.re_raise = re_raise
        self.backoff = backoff
        self.exclude = exclude if isinstance(exclude, frozenset) else frozenset(exclude)

    def _log_exception(self, func_name: str, exc: Exception, attempt: int) -> None:
        """Log exception with context."""
        logger.error(
            f"[ERROR] '{func_name}' failed (attempt {attempt}/{self.retries + 1}): "
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        )

    def _wrap(self, func: Callable[..., T]) -> Callable[..., T]:
        """Wrap function with retry logic."""
        is_coro = inspect.iscoroutinefunction(func)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(self.retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    self._log_exception(func.__name__, exc, attempt + 1)
                    if attempt < self.retries:
                        if self.backoff > 0:
                            await asyncio.sleep(self.backoff)
                    elif self.re_raise:
                        raise
            return None  # All retries exhausted, no re-raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(self.retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    self._log_exception(func.__name__, exc, attempt + 1)
                    if attempt < self.retries:
                        if self.backoff > 0:
                            import time
                            time.sleep(self.backoff)
                    elif self.re_raise:
                        raise
            return None  # All retries exhausted, no re-raise
        
        return async_wrapper if is_coro else sync_wrapper

    def __call__(self, obj: type | Callable[..., T] | None = None) -> Any:
        """Enable usage as @ErrorHandling or @ErrorHandling()."""
        if obj is None:
            return self
        
        # Class decoration
        if inspect.isclass(obj):
            for name in dir(obj):
                if name in self.exclude or name.startswith('_') and name != '__init__':
                    continue
                attr = getattr(obj, name)
                if callable(attr):
                    setattr(obj, name, self._wrap(attr))
            return obj
        
        # Function/method decoration
        return self._wrap(obj)

error_handling = ErrorHandling(retries=3, re_raise=True, backoff=5)
