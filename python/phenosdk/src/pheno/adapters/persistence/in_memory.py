"""In-memory persistence adapter (for testing)."""

from typing import Any


class InMemoryPersistence:
    """In-memory persistence adapter for testing."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def save(self, key: str, value: Any) -> None:
        """Save value to in-memory store."""
        self._store[key] = value

    def load(self, key: str) -> Any | None:
        """Load value from in-memory store."""
        return self._store.get(key)

    def delete(self, key: str) -> None:
        """Delete value from in-memory store."""
        if key in self._store:
            del self._store[key]

    def list_keys(self) -> list[str]:
        """List all keys in store."""
        return list(self._store.keys())
