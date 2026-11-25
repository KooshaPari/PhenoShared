"""In-memory lock adapter for command deduplication."""

from typing import Optional
from ..domain.entities import CommandLock, LockStatus
from ..domain.value_objects import CommandHash


class InMemoryLockAdapter:
    """In-memory implementation of LockPort for testing and local use."""

    def __init__(self) -> None:
        self._locks: dict[str, CommandLock] = {}

    def acquire(
        self, cmd_hash: CommandHash, pid: int, output_path: Optional[str] = None
    ) -> CommandLock:
        """Acquire a command lock."""
        key = str(cmd_hash)
        if key in self._locks:
            lock = self._locks[key]
            if lock.is_locked() and lock.pid != pid:
                raise ValueError("already locked")
            lock.acquire(pid, output_path)
            return lock
        else:
            lock = CommandLock(cmd_hash=key, pid=pid, output_path=output_path)
            lock.status = LockStatus.LOCKED
            self._locks[key] = lock
            return lock

    def release(self, cmd_hash: CommandHash, pid: int) -> None:
        """Release a command lock."""
        key = str(cmd_hash)
        if key not in self._locks:
            raise ValueError(f"No lock found for {key}")
        lock = self._locks[key]
        lock.release(pid)

    def get(self, cmd_hash: CommandHash) -> Optional[CommandLock]:
        """Get lock status."""
        return self._locks.get(str(cmd_hash))

    def list_all(self) -> list[CommandLock]:
        """List all locks."""
        return list(self._locks.values())


__all__ = ["InMemoryLockAdapter"]
