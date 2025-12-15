"""
Utilities for Maestro TUI - Loading states, Error handling, Performance, and UX Trust Signals
"""
import time
import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Any, Dict, List
from functools import wraps
from textual.widgets import Label, Button, Static, Switch
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual import on


class ErrorSeverity(Enum):
    """Severity levels for error presentation."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKED = "blocked"


@dataclass
class ErrorMessage:
    """Normalized error message structure."""
    title: str
    severity: ErrorSeverity
    message: str
    technical_details: Optional[str] = None
    actionable_hint: Optional[str] = None


class LoadingIndicator:
    """Loading indicator utility for the TUI."""

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
        self.status_bar_widget: Optional[Label] = None
        # Track performance metrics
        self.facade_call_times: Dict[str, List[float]] = {}
        self.dev_mode = True  # Can be set to False for production

    def set_status_bar_widget(self, widget: Label):
        """Set the status bar widget to update."""
        self.status_bar_widget = widget

    def update_global_status(self, message: str, is_loading: bool = False):
        """Update the global status bar."""
        if self.status_bar_widget:
            # Add loading indicator if needed
            indicator = " ⏳ " if is_loading else ""
            self.status_bar_widget.update(f"{indicator}{message}")

    def log_facade_call(self, func_name: str, duration: float):
        """Log facade call durations for performance monitoring."""
        if self.dev_mode:
            print(f"DEBUG: Facade call '{func_name}' took {duration:.3f}s")

            # Track call times for this function
            if func_name not in self.facade_call_times:
                self.facade_call_times[func_name] = []
            self.facade_call_times[func_name].append(duration)

    def check_for_throttling(self, func_name: str) -> bool:
        """Check if repeated calls to the same function might indicate thrashing."""
        if func_name in self.facade_call_times:
            recent_calls = self.facade_call_times[func_name][-5:]  # Last 5 calls
            if len(recent_calls) >= 5 and all(duration < 0.1 for duration in recent_calls):
                print(f"WARNING: Function '{func_name}' appears to be called rapidly ({len(recent_calls)} times in quick succession). Consider throttling or memoization.")
                return True
        return False


class ErrorModal(ModalScreen[bool]):
    """A modal for displaying normalized error messages."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("enter", "dismiss", "Close"),
    ]

    def __init__(self, error_msg: ErrorMessage):
        super().__init__()
        self.error_msg = error_msg
        # Track whether technical details should be shown
        self.show_technical_details = False

    def compose(self) -> "ComposeResult":
        """Create child widgets for the error modal."""
        with Vertical(id="error-modal-container"):
            # Header with severity-appropriate styling
            severity_colors = {
                ErrorSeverity.INFO: "[bold blue]",
                ErrorSeverity.WARNING: "[bold yellow]",
                ErrorSeverity.ERROR: "[bold red]",
                ErrorSeverity.BLOCKED: "[bold red]"
            }
            color = severity_colors.get(self.error_msg.severity, "[bold]")
            
            yield Label(f"{color}ERROR: {self.error_msg.title}[/bold]", id="error-title")
            yield Label(self.error_msg.message, id="error-message")
            
            # Add actionable hint if available
            if self.error_msg.actionable_hint:
                yield Label(f"[bold]Hint:[/bold] {self.error_msg.actionable_hint}", id="actionable-hint")
            
            # Button to show technical details
            if self.error_msg.technical_details:
                with Horizontal(id="details-controls"):
                    yield Button("Show Technical Details", variant="default", id="toggle-details")
            
            # Technical details section (initially hidden)
            if self.error_msg.technical_details:
                yield Static(self.error_msg.technical_details, id="technical-details", visible=False)
            
            with Horizontal(id="error-buttons"):
                yield Button("OK", variant="primary", id="ok-button")

    def on_mount(self) -> None:
        """Focus the OK button when mounted."""
        self.query_one("#ok-button").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "ok-button":
            self.dismiss(True)
        elif event.button.id == "toggle-details":
            self.toggle_technical_details()

    def toggle_technical_details(self):
        """Toggle the visibility of technical details."""
        details_container = self.query_one("#technical-details", Static)
        toggle_button = self.query_one("#toggle-details", Button)
        
        self.show_technical_details = not self.show_technical_details
        details_container.visible = self.show_technical_details
        
        if self.show_technical_details:
            toggle_button.label = "Hide Technical Details"
        else:
            toggle_button.label = "Show Technical Details"

    def action_dismiss(self) -> None:
        """Action to dismiss the modal."""
        self.dismiss(True)


class ErrorNormalizer:
    """Normalizes errors from various facade calls."""

    @staticmethod
    def normalize_exception(exc: Exception, context: str = "") -> ErrorMessage:
        """Convert an exception to a normalized ErrorMessage."""
        # Map specific exception types to appropriate severities and messages
        if isinstance(exc, FileNotFoundError):
            return ErrorMessage(
                title="File Not Found",
                severity=ErrorSeverity.BLOCKED,
                message=f"The required file could not be found: {str(exc)}",
                actionable_hint="Check that the specified file exists and is accessible."
            )
        elif isinstance(exc, PermissionError):
            return ErrorMessage(
                title="Permission Denied",
                severity=ErrorSeverity.BLOCKED,
                message=f"Access to the required resource was denied: {str(exc)}",
                actionable_hint="Verify that you have the necessary permissions to access this resource."
            )
        elif isinstance(exc, ValueError):
            return ErrorMessage(
                title="Invalid Value",
                severity=ErrorSeverity.WARNING,
                message=str(exc),
                actionable_hint="Check the input values and try again."
            )
        elif isinstance(exc, ConnectionError):
            return ErrorMessage(
                title="Connection Error",
                severity=ErrorSeverity.ERROR,
                message="Failed to connect to the required service.",
                actionable_hint="Check your network connection and try again."
            )
        else:
            # Default error message for unknown exceptions
            return ErrorMessage(
                title="Operation Failed",
                severity=ErrorSeverity.ERROR,
                message=str(exc) or f"An error occurred during {context}.",
                technical_details=str(type(exc).__name__),
                actionable_hint="Try again or check logs for more details."
            )


# Global instance for status management
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

            # Check for potential thrashing before making the call
            if global_status_manager.check_for_throttling(func.__name__):
                print(f"WARNING: Throttling detected for {func.__name__}, adding delay to prevent thrashing")
                await asyncio.sleep(0.1)  # Small delay to prevent thrashing

            # Start loader for this call
            global_status_manager.loading_indicator.start_loader(call_id)

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                # Log error with duration
                duration = time.time() - start_time
                global_status_manager.log_facade_call(f"{func.__name__}_error", duration)
                print(f"DEBUG: Facade call {func.__name__} took {duration:.2f}s and failed: {str(e)}")
                raise e
            finally:
                # Stop loader for this call
                global_status_manager.loading_indicator.stop_loader(call_id)

                # Update global status display
                duration = time.time() - start_time
                global_status_manager.log_facade_call(func.__name__, duration)
                if duration > duration_threshold:
                    print(f"INFO: Long-running facade call {func.__name__} took {duration:.2f}s")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            call_id = f"{func.__name__}_{time.time()}"
            start_time = time.time()

            # Check for potential thrashing before making the call
            if global_status_manager.check_for_throttling(func.__name__):
                print(f"WARNING: Throttling detected for {func.__name__}, adding delay to prevent thrashing")
                time.sleep(0.1)  # Small delay to prevent thrashing

            # Start loader for this call
            global_status_manager.loading_indicator.start_loader(call_id)

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Log error with duration
                duration = time.time() - start_time
                global_status_manager.log_facade_call(f"{func.__name__}_error", duration)
                print(f"DEBUG: Facade call {func.__name__} took {duration:.2f}s and failed: {str(e)}")
                raise e
            finally:
                # Stop loader for this call
                global_status_manager.loading_indicator.stop_loader(call_id)

                # Update global status display
                duration = time.time() - start_time
                global_status_manager.log_facade_call(func.__name__, duration)
                if duration > duration_threshold:
                    print(f"INFO: Long-running facade call {func.__name__} took {duration:.2f}s")

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Simple memoization cache for read-only data
class MemoizationCache:
    """Simple in-memory cache for memoizing read-only facade calls."""

    def __init__(self):
        self.cache: Dict[str, Tuple[Any, float]] = {}  # Store (value, timestamp)
        self.cache_timeouts: Dict[str, float] = {}  # Timeout in seconds for each key

    def get(self, key: str):
        """Get a value from cache if it's still valid."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            timeout = self.cache_timeouts.get(key, 30.0)  # Default timeout 30 seconds

            if time.time() - timestamp < timeout:
                return value
            else:
                # Remove expired entry
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


# Global memoization cache instance
memoization_cache = MemoizationCache()


def memoize_for(seconds: float = 30.0):
    """Decorator to memoize function results for a specified number of seconds."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            # Check if result is in cache
            cached_result = memoization_cache.get(cache_key)
            if cached_result is not None:
                print(f"DEBUG: Cache HIT for {func.__name__}")
                return cached_result

            # Call the function and cache the result
            result = func(*args, **kwargs)
            memoization_cache.set(cache_key, result, seconds)
            print(f"DEBUG: Cache MISS for {func.__name__}, cached for {seconds}s")

            return result

        return wrapper
    return decorator