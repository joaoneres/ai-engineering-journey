"""Central application state: pickups, loading flag, last error and active filters.

The state is immutable: every function returns a new AppState, so transitions
are easy to reason about and to test.
"""

from dataclasses import dataclass, field, replace

from domain.pickups import FILTER_OPTIONS, filter_by
from errors import FilaFacilError, InputError


@dataclass(frozen=True)
class AppState:
    """Snapshot of everything the menu needs to know."""

    pickups: list[dict] = field(default_factory=list)
    loading: bool = False
    last_error: dict | None = None  # {"kind": "input" | "file" | "api", "message": str}
    filters: dict = field(default_factory=dict)  # {"status": "pending", "priority": "high"}


def initial_state(pickups: list[dict] | None = None) -> AppState:
    """Build the starting state with the pickups loaded from the file."""
    return AppState(pickups=list(pickups or []))


def set_pickups(state: AppState, pickups: list[dict]) -> AppState:
    """Replace the pickup list."""
    return replace(state, pickups=list(pickups))


def set_loading(state: AppState, loading: bool) -> AppState:
    """Mark the state as loading (API or file operation in progress) or idle."""
    return replace(state, loading=loading)


def set_error(state: AppState, error: FilaFacilError) -> AppState:
    """Store the last error with its origin (input, file or api)."""
    return replace(state, last_error={"kind": error.kind, "message": str(error)})


def clear_error(state: AppState) -> AppState:
    """Forget the last error."""
    return replace(state, last_error=None)


def set_filter(state: AppState, field_name: str, value: str) -> AppState:
    """Activate a status or priority filter; raise InputError for invalid values."""
    if field_name not in FILTER_OPTIONS:
        raise InputError("Filtro inválido.")
    allowed, message = FILTER_OPTIONS[field_name]
    if value not in allowed:
        raise InputError(message)
    return replace(state, filters={**state.filters, field_name: value})


def clear_filters(state: AppState) -> AppState:
    """Remove every active filter."""
    return replace(state, filters={})


def visible_pickups(state: AppState) -> list[dict]:
    """Return the pickups that match all active filters."""
    return _apply_filters(state.pickups, state.filters)


def _apply_filters(pickups: list[dict], filters: dict) -> list[dict]:
    """Apply the filters one after another."""
    result = pickups
    for field_name, value in filters.items():
        result = filter_by(result, field_name, value)
    return result
