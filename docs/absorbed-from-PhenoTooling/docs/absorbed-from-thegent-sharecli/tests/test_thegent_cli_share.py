"""Tests for thegent-cli-share."""

import pytest
from thegent_cli_share.adapters.dedup import InMemoryLockAdapter
from thegent_cli_share.adapters.queue import InMemoryQueueAdapter
from thegent_cli_share.domain.entities import CommandLock, TaskQueueItem, QueuePriority
from thegent_cli_share.domain.value_objects import CommandHash


class TestCommandLock:
    """Tests for CommandLock entity."""

    def test_create_lock(self) -> None:
        """Test creating a new command lock."""
        lock = CommandLock(cmd_hash="test_hash", pid=0)
        assert lock.cmd_hash == "test_hash"
        assert lock.pid == 0

    def test_acquire_lock(self) -> None:
        """Test acquiring a lock."""
        adapter = InMemoryLockAdapter()
        lock = adapter.acquire(CommandHash("test_hash"), 1234)
        assert lock.cmd_hash == "test_hash"
        assert lock.pid == 1234
        assert lock.is_locked()

    def test_release_lock(self) -> None:
        """Test releasing a lock."""
        adapter = InMemoryLockAdapter()
        adapter.acquire(CommandHash("test_hash"), 1234)
        adapter.release(CommandHash("test_hash"), 1234)
        lock = adapter.get(CommandHash("test_hash"))
        assert lock is not None
        assert not lock.is_locked()

    def test_cannot_acquire_locked(self) -> None:
        """Test that we cannot acquire a locked command."""
        adapter = InMemoryLockAdapter()
        adapter.acquire(CommandHash("test_hash"), 1234)
        with pytest.raises(ValueError, match="already locked"):
            adapter.acquire(CommandHash("test_hash"), 5678)


class TestTaskQueue:
    """Tests for TaskQueue."""

    def test_enqueue(self) -> None:
        """Test enqueuing a task."""
        adapter = InMemoryQueueAdapter()
        item = adapter.enqueue(TaskQueueItem(command="echo 'hello'", status="queued"))
        assert item.command == "echo 'hello'"
        assert item.status == "queued"

    def test_dequeue(self) -> None:
        """Test dequeuing a task."""
        adapter = InMemoryQueueAdapter()
        adapter.enqueue(TaskQueueItem(command="task1"))
        adapter.enqueue(TaskQueueItem(command="task2"))
        item = adapter.dequeue()
        assert item is not None
        assert item.command == "task1"
        assert item.status == "dequeued"

    def test_priority_ordering(self) -> None:
        """Test that high priority items are dequeued first."""
        adapter = InMemoryQueueAdapter()
        adapter.enqueue(TaskQueueItem(command="low", priority=QueuePriority.LOW))
        adapter.enqueue(TaskQueueItem(command="high", priority=QueuePriority.HIGH))
        adapter.enqueue(TaskQueueItem(command="normal", priority=QueuePriority.NORMAL))
        item = adapter.dequeue()
        assert item is not None
        assert item.command == "high"


class TestCoordination:
    """Tests for CoordinationService."""

    def test_edit_intent(self) -> None:
        """Test EditIntent creation and checking."""
        from thegent_cli_share.domain.entities import EditIntent

        intent = EditIntent(
            agent_id="agent1",
            file_path="/path/to/file",
            start_line=10,
            end_line=20,
        )
        assert intent.file_path == "/path/to/file"
        assert intent.start_line == 10
        assert intent.end_line == 20
        assert intent.conflicts_with(intent)  # Same range conflicts

    def test_edit_intent_no_conflict(self) -> None:
        """Test that non-overlapping edits don't conflict."""
        from thegent_cli_share.domain.entities import EditIntent

        intent1 = EditIntent(
            agent_id="agent1",
            file_path="/path/to/file",
            start_line=10,
            end_line=20,
        )
        intent2 = EditIntent(
            agent_id="agent2",
            file_path="/path/to/file",
            start_line=30,
            end_line=40,
        )
        assert not intent1.conflicts_with(intent2)
