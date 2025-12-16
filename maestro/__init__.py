"""
Maestro package - AI Task Management & Orchestration
"""

try:
    from .main import main, __version__  # type: ignore
except Exception:
    __version__ = "unknown"

    def main(*args, **kwargs):  # type: ignore
        raise RuntimeError("maestro.main could not be imported") from None

__all__ = ["main", "__version__"]
