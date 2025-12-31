"""Compatibility shim for legacy imports."""

from maestro.convert.inventory_generator import (
    generate_inventory,
    load_inventory,
    save_inventory,
)

__all__ = [
    "generate_inventory",
    "load_inventory",
    "save_inventory",
]
