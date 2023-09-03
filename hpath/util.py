"""Utility functions and constants."""
import dataclasses
from typing import Any, is_typeddict

ARR_RATE_INTERVAL_HOURS = 1
"""Interval duration for which specimen arrival rates are defined in the Excel config template."""

RESOURCE_ALLOCATION_INTERVAL_HOURS = 0.5
"""Interval duration for which resource allocations are defined in the Excel config template."""


def dc_names(dataclass_inst) -> list[str]:
    """Get the field names of a dataclass instance."""
    return [field.name for field in dataclasses.fields(dataclass_inst)]


def dc_values(dataclass_inst) -> list:
    """Get the field values of a dataclass instance."""
    return [getattr(dataclass_inst, field.name) for field in dataclasses.fields(dataclass_inst)]


def is_dataclass_instance(obj) -> bool:
    """Returns whether the object is a dataclass instance."""
    return dataclasses.is_dataclass(obj) and not isinstance(obj, type)


def dc_dict(dataclass_inst) -> dict[str, Any]:
    """Convert a dataclass instance to a dict.
    """
    def _fn(obj):
        if is_dataclass_instance(obj):
            return dc_dict(obj)
        return obj
    return {field.name: _fn(getattr(dataclass_inst, field.name))
            for field in dataclasses.fields(dataclass_inst)}


def dc_items(dataclass_inst) -> list[tuple[str, Any]]:
    """Convert a dataclass instance to a list of tuples. Useful for iteration."""
    return [(field.name, getattr(dataclass_inst, field.name))
            for field in dataclasses.fields(dataclass_inst)]


def serialiser(obj: Any) -> Any:
    """Serialiser for :py:func:`json.dump` or :py:func:`json.dumps`."""
    if is_dataclass_instance(obj):
        return dc_dict(obj)  # convert to dict first
    if is_typeddict(obj):
        return dict(obj)  # convert to normal dict
    # Neither built-in or our serialiser understand this data type
    raise TypeError
