"""
Shared UI facade utilities that must not depend on Textual.
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple


class LoadingIndicator:
    """Loading indicator utility for facade calls."""

    def __init__(self):
        self.active_loaders: Dict[str, float] = {}
        self.global_loader_active = False

    def start_loader(self, loader_id: str, description: str = ""):
        """Start a loader with given ID."""
        self.active_loaders[loader_id] = time.time()
        if len(self.active_loaders) == 1:
            self.global_loader_active = True

    def stop_loader(self, loader_id: str):
        """Stop a loader with given ID."""
        if loader_id in self.active_loaders:
            del self.active_loaders[loader_id]
            if not self.active_loaders:
                self.global_loader_active = False


class GlobalStatusManager:
    """Manages global status indicators like loading indicators."""

    def __init__(self):
        self.loading_indicator = LoadingIndicator()
        self.status_bar_widget: Optional[object] = None
        self.facade_call_times: Dict[str, List[float]] = {}
        self.dev_mode = True

    def set_status_bar_widget(self, widget: object):
        """Set the status bar widget to update."""
        self.status_bar_widget = widget

    def update_global_status(self, message: str, is_loading: bool = False):
        """Update the global status bar."""
        if self.status_bar_widget:
            indicator = " ⏳ " if is_loading else ""
            self.status_bar_widget.update(f"{indicator}{message}")

    def log_facade_call(self, func_name: str, duration: float):
        """Log facade call durations for performance monitoring."""
        if self.dev_mode:
            print(f"DEBUG: Facade call '{func_name}' took {duration:.3f}s")

            if func_name not in self.facade_call_times:
                self.facade_call_times[func_name] = []
            self.facade_call_times[func_name].append(duration)

    def check_for_throttling(self, func_name: str) -> bool:
        """Check if repeated calls to the same function might indicate thrashing."""
        if func_name in self.facade_call_times:
            recent_calls = self.facade_call_times[func_name][-5:]
            if len(recent_calls) >= 5 and all(duration < 0.1 for duration in recent_calls):
                print(
                    f"WARNING: Function '{func_name}' appears to be called rapidly "
                    f"({len(recent_calls)} times in quick succession). Consider throttling or memoization."
                )
                return True
        return False


global_status_manager = GlobalStatusManager()


def track_facade_call(duration_threshold: float = 0.1):
    """
    Decorator to track facade calls and show loading indicators if they exceed threshold.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            call_id = f"{func.__name__}_{time.time()}"
            start_time = time.time()

            if global_status_manager.check_for_throttling(func.__name__):
                print(f"WARNING: Throttling detected for {func.__name__}, adding delay to prevent thrashing")
                await asyncio.sleep(0.1)

            global_status_manager.loading_indicator.start_loader(call_id)

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                duration = time.time() - start_time
                global_status_manager.log_facade_call(f"{func.__name__}_error", duration)
                print(f"DEBUG: Facade call {func.__name__} took {duration:.2f}s and failed: {str(e)}")
                raise e
            finally:
                global_status_manager.loading_indicator.stop_loader(call_id)

                duration = time.time() - start_time
                global_status_manager.log_facade_call(func.__name__, duration)
                if duration > duration_threshold:
                    print(f"INFO: Long-running facade call {func.__name__} took {duration:.2f}s")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            call_id = f"{func.__name__}_{time.time()}"
            start_time = time.time()

            if global_status_manager.check_for_throttling(func.__name__):
                print(f"WARNING: Throttling detected for {func.__name__}, adding delay to prevent thrashing")
                time.sleep(0.1)

            global_status_manager.loading_indicator.start_loader(call_id)

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                duration = time.time() - start_time
                global_status_manager.log_facade_call(f"{func.__name__}_error", duration)
                print(f"DEBUG: Facade call {func.__name__} took {duration:.2f}s and failed: {str(e)}")
                raise e
            finally:
                global_status_manager.loading_indicator.stop_loader(call_id)

                duration = time.time() - start_time
                global_status_manager.log_facade_call(func.__name__, duration)
                if duration > duration_threshold:
                    print(f"INFO: Long-running facade call {func.__name__} took {duration:.2f}s")

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class MemoizationCache:
    """Simple in-memory cache for memoizing read-only facade calls."""

    def __init__(self):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.cache_timeouts: Dict[str, float] = {}

    def get(self, key: str):
        """Get a value from cache if it's still valid."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            timeout = self.cache_timeouts.get(key, 30.0)

            if time.time() - timestamp < timeout:
                return value
            del self.cache[key]
            if key in self.cache_timeouts:
                del self.cache_timeouts[key]

        return None

    def set(self, key: str, value: Any, timeout: float = 30.0):
        """Set a value in the cache."""
        self.cache[key] = (value, time.time())
        self.cache_timeouts[key] = timeout

    def clear(self):
        """Clear the entire cache."""
        self.cache.clear()
        self.cache_timeouts.clear()


memoization_cache = MemoizationCache()


def memoize_for(seconds: float = 30.0):
    """Decorator to memoize function results for a specified number of seconds."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            cached_result = memoization_cache.get(cache_key)
            if cached_result is not None:
                print(f"DEBUG: Cache HIT for {func.__name__}")
                return cached_result

            result = func(*args, **kwargs)
            memoization_cache.set(cache_key, result, seconds)
            print(f"DEBUG: Cache MISS for {func.__name__}, cached for {seconds}s")

            return result

        return wrapper

    return decorator
