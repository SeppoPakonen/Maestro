"""
Registry for MC shell pane views.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Type, Any
import traceback
import logging

from maestro.tui.panes.base import PaneFactory, PaneView, MCPane

# Central registry for all panes - single source of truth
PANE_REGISTRY: Dict[str, Type[PaneView]] = {}

# Import-safe pane factories for deferred loading
PANE_FACTORIES: Dict[str, PaneFactory] = {}


def register_pane(pane_id: str, pane_class: Type[PaneView]) -> None:
    """Register a pane class for a pane ID."""
    PANE_REGISTRY[pane_id] = pane_class


def register_pane_factory(pane_id: str, factory: PaneFactory) -> None:
    """Register a pane factory for lazy loading."""
    PANE_FACTORIES[pane_id] = factory


def get_pane_class(pane_id: str) -> Optional[Type[PaneView]]:
    """Return the pane class for a given pane ID, if registered."""
    return PANE_REGISTRY.get(pane_id)


def create_pane(pane_id: str) -> Optional[PaneView]:
    """Create a pane instance for the pane ID, if registered.

    Returns None if no pane is registered for the ID.
    """
    # First try to get from the main registry
    pane_class = get_pane_class(pane_id)
    if pane_class:
        try:
            return pane_class()
        except Exception as e:
            logging.error(f"Failed to instantiate pane {pane_id}: {e}")
            return None

    # Fallback to factory
    factory = PANE_FACTORIES.get(pane_id)
    if factory:
        try:
            return factory()
        except Exception as e:
            logging.error(f"Failed to create pane via factory {pane_id}: {e}")
            return None

    return None


def create_pane_safe(pane_id: str) -> tuple[Optional[PaneView], Optional[Exception]]:
    """Create a pane with hard failure containment.

    Returns (pane_instance, exception) tuple.
    If creation succeeds, exception is None.
    If creation fails, pane_instance is None and exception contains the error.
    """
    # We need to re-implement the creation logic to properly capture exceptions
    pane_class = get_pane_class(pane_id)
    if pane_class:
        try:
            return pane_class(), None
        except Exception as e:
            logging.error(f"Safe creation failed for pane {pane_id}: {e}")
            return None, e

    # Fallback to factory
    factory = PANE_FACTORIES.get(pane_id)
    if factory:
        try:
            return factory(), None
        except Exception as e:
            logging.error(f"Safe creation failed for pane {pane_id} via factory: {e}")
            return None, e

    # If not found in registry
    return None, ValueError(f"No pane registered with ID: {pane_id}")


def registered_pane_ids() -> List[str]:
    """List all registered pane IDs."""
    return list(PANE_REGISTRY.keys())


def get_pane_factory(pane_id: str) -> Optional[PaneFactory]:
    """Return the factory for a given pane ID, if any."""
    # Fallback to the legacy registry for backward compatibility
    return PANE_FACTORIES.get(pane_id)


def registered_pane_classes() -> List[Type[PaneView]]:
    """List all registered pane classes."""
    return list(PANE_REGISTRY.values())


def registered_sections() -> List[str]:
    """List registered section names (backward compatibility)."""
    return registered_pane_ids()


def load_all_pane_modules():
    """Load all pane modules to ensure they are registered.

    This function imports all pane modules to ensure they register themselves
    with the registry during startup.

    All imports are controlled here to avoid side effects at import time
    in other modules.
    """
    # Import all pane modules to ensure registration
    # This maintains import-side effect discipline
    try:
        import maestro.tui.panes.sessions  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import sessions pane: {e}")

    # Import additional pane modules as they are created
    # Add new pane imports here in the future:
    try:
        import maestro.tui.panes.phases  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import phases pane: {e}")

    try:
        import maestro.tui.panes.tasks  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import tasks pane: {e}")

    try:
        import maestro.tui.panes.build  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import build pane: {e}")

    try:
        import maestro.tui.panes.convert  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import convert pane: {e}")

    try:
        import maestro.tui.panes.semantic  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import semantic pane: {e}")

    try:
        import maestro.tui.panes.decision  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import decision pane: {e}")

    try:
        import maestro.tui.panes.batch  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import batch pane: {e}")

    try:
        import maestro.tui.panes.timeline  # noqa: F401
    except ImportError as e:
        logging.warning(f"Could not import timeline pane: {e}")

    # This centralized import ensures no side effects in other files


def safe_load_all_panes() -> Dict[str, tuple[bool, Optional[str]]]:
    """Test that all registered panes can be instantiated safely.

    Returns a dictionary mapping pane_id to (success, error_message).
    """
    results = {}
    for pane_id in registered_pane_ids():
        try:
            pane = create_pane(pane_id)
            if pane is not None:
                results[pane_id] = (True, None)
            else:
                results[pane_id] = (False, "Pane creation returned None")
        except Exception as e:
            results[pane_id] = (False, str(e))

    return results


# IMPORT-SAFE: no side effects allowed
