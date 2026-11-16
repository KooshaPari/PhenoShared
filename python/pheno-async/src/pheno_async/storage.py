"""
Storage backends for task orchestration.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from pheno.logging.core.logger import get_logger

from .orchestration import Task, TaskResult, TaskStatus, TaskStorage

logger = get_logger("pheno.async.storage")


class InMemoryTaskStorage(TaskStorage):
    """
    In-memory storage backend for tasks.
    """

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()

    async def store_task(self, task: Task) -> None:
        """
        Store a task in memory.
        """
        async with self._lock:
            self._tasks[task.config.task_id] = task
            logger.debug(f"Stored task {task.config.task_id} in memory")

    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.
        """
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task(self, task: Task) -> None:
        """
        Update a task.
        """
        async with self._lock:
            if task.config.task_id in self._tasks:
                self._tasks[task.config.task_id] = task
                logger.debug(f"Updated task {task.config.task_id} in memory")

    async def delete_task(self, task_id: str) -> None:
        """
        Delete a task.
        """
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.debug(f"Deleted task {task_id} from memory")

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """
        List tasks, optionally filtered by status.
        """
        async with self._lock:
            tasks = list(self._tasks.values())

            if status is not None:
                tasks = [task for task in tasks if task.status == status]

            return tasks

    async def get_pending_tasks(self) -> list[Task]:
        """
        Get all pending tasks.
        """
        return await self.list_tasks(TaskStatus.PENDING)


class FileTaskStorage(TaskStorage):
    """
    File-based storage backend for tasks.
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _get_task_file(self, task_id: str) -> Path:
        """
        Get the file path for a task.
        """
        return self.storage_dir / f"{task_id}.json"

    async def store_task(self, task: Task) -> None:
        """
        Store a task to file.
        """
        async with self._lock:
            task_file = self._get_task_file(task.config.task_id)

            # Convert task to serializable format
            task_data = self._serialize_task(task)

            # Write to file
            with open(task_file, "w") as f:
                json.dump(task_data, f, indent=2, default=str)

            logger.debug(f"Stored task {task.config.task_id} to file {task_file}")

    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.
        """
        async with self._lock:
            task_file = self._get_task_file(task_id)

            if not task_file.exists():
                return None

            try:
                with open(task_file) as f:
                    task_data = json.load(f)

                return self._deserialize_task(task_data)
            except Exception as e:
                logger.exception(f"Failed to load task {task_id} from file: {e}")
                return None

    async def update_task(self, task: Task) -> None:
        """
        Update a task.
        """
        await self.store_task(task)  # File storage just overwrites

    async def delete_task(self, task_id: str) -> None:
        """
        Delete a task.
        """
        async with self._lock:
            task_file = self._get_task_file(task_id)

            if task_file.exists():
                task_file.unlink()
                logger.debug(f"Deleted task {task_id} file {task_file}")

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """
        List tasks, optionally filtered by status.
        """
        async with self._lock:
            tasks = []

            for task_file in self.storage_dir.glob("*.json"):
                try:
                    with open(task_file) as f:
                        task_data = json.load(f)

                    task = self._deserialize_task(task_data)
                    if task:
                        if status is None or task.status == status:
                            tasks.append(task)

                except Exception as e:
                    logger.warning(f"Failed to load task from {task_file}: {e}")

            return tasks

    async def get_pending_tasks(self) -> list[Task]:
        """
        Get all pending tasks.
        """
        return await self.list_tasks(TaskStatus.PENDING)

    def _serialize_task(self, task: Task) -> dict[str, Any]:
        """
        Serialize a task to a dictionary.
        """
        return {
            "config": {
                "task_id": task.config.task_id,
                "name": task.config.name,
                "description": task.config.description,
                "priority": task.config.priority.value,
                "max_retries": task.config.max_retries,
                "retry_delay": task.config.retry_delay,
                "timeout": task.config.timeout,
                "dependencies": task.config.dependencies,
                "tags": list(task.config.tags),
                "metadata": task.config.metadata,
                "created_at": task.config.created_at.isoformat(),
                "scheduled_at": (
                    task.config.scheduled_at.isoformat() if task.config.scheduled_at else None
                ),
            },
            "func_name": task.func.__name__ if hasattr(task.func, "__name__") else "unknown",
            "args": task.args,
            "kwargs": task.kwargs,
            "status": task.status.value,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": self._serialize_result(task.result) if task.result else None,
        }

    def _deserialize_task(self, task_data: dict[str, Any]) -> Task | None:
        """
        Deserialize a task from a dictionary.
        """
        try:
            from .orchestration import Task, TaskConfig, TaskPriority

            # Reconstruct config
            config_data = task_data["config"]
            config = TaskConfig(
                task_id=config_data["task_id"],
                name=config_data["name"],
                description=config_data["description"],
                priority=TaskPriority(config_data["priority"]),
                max_retries=config_data["max_retries"],
                retry_delay=config_data["retry_delay"],
                timeout=config_data["timeout"],
                dependencies=config_data["dependencies"],
                tags=set(config_data["tags"]),
                metadata=config_data["metadata"],
                created_at=datetime.fromisoformat(config_data["created_at"]),
                scheduled_at=(
                    datetime.fromisoformat(config_data["scheduled_at"])
                    if config_data["scheduled_at"]
                    else None
                ),
            )

            # Create a dummy function (we can't serialize actual functions)
            def dummy_func(*args, **kwargs):
                raise NotImplementedError("Function not available in file storage")

            # Reconstruct task
            return Task(
                config=config,
                func=dummy_func,
                args=tuple(task_data["args"]),
                kwargs=task_data["kwargs"],
                status=TaskStatus(task_data["status"]),
                started_at=(
                    datetime.fromisoformat(task_data["started_at"])
                    if task_data["started_at"]
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(task_data["completed_at"])
                    if task_data["completed_at"]
                    else None
                ),
                result=(
                    self._deserialize_result(task_data["result"]) if task_data["result"] else None
                ),
            )

        except Exception as e:
            logger.exception(f"Failed to deserialize task: {e}")
            return None

    def _serialize_result(self, result: TaskResult) -> dict[str, Any]:
        """
        Serialize a task result.
        """
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": str(result.error) if result.error else None,
            "execution_time": result.execution_time,
            "retry_count": result.retry_count,
            "metadata": result.metadata,
            "created_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        }

    def _deserialize_result(self, result_data: dict[str, Any]) -> TaskResult:
        """
        Deserialize a task result.
        """
        from .orchestration import TaskResult, TaskStatus

        return TaskResult(
            task_id=result_data["task_id"],
            status=TaskStatus(result_data["status"]),
            result=result_data["result"],
            error=Exception(result_data["error"]) if result_data["error"] else None,
            execution_time=result_data["execution_time"],
            retry_count=result_data["retry_count"],
            metadata=result_data["metadata"],
            created_at=datetime.fromisoformat(result_data["created_at"]),
            completed_at=(
                datetime.fromisoformat(result_data["completed_at"])
                if result_data["completed_at"]
                else None
            ),
        )


class DatabaseTaskStorage(TaskStorage):
    """
    SQLite database storage backend for tasks.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._init_database()

    def _init_database(self) -> None:
        """
        Initialize the database schema.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    priority INTEGER NOT NULL,
                    max_retries INTEGER NOT NULL,
                    retry_delay REAL NOT NULL,
                    timeout REAL,
                    dependencies TEXT,
                    tags TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    scheduled_at TEXT,
                    func_name TEXT,
                    args TEXT,
                    kwargs TEXT,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result_data TEXT
                )
            """,
            )
            conn.commit()

    async def store_task(self, task: Task) -> None:
        """
        Store a task in the database.
        """
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tasks (
                        task_id, name, description, priority, max_retries, retry_delay,
                        timeout, dependencies, tags, metadata, created_at, scheduled_at,
                        func_name, args, kwargs, status, started_at, completed_at, result_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        task.config.task_id,
                        task.config.name,
                        task.config.description,
                        task.config.priority.value,
                        task.config.max_retries,
                        task.config.retry_delay,
                        task.config.timeout,
                        json.dumps(task.config.dependencies),
                        json.dumps(list(task.config.tags)),
                        json.dumps(task.config.metadata),
                        task.config.created_at.isoformat(),
                        task.config.scheduled_at.isoformat() if task.config.scheduled_at else None,
                        task.func.__name__ if hasattr(task.func, "__name__") else "unknown",
                        json.dumps(task.args),
                        json.dumps(task.kwargs),
                        task.status.value,
                        task.started_at.isoformat() if task.started_at else None,
                        task.completed_at.isoformat() if task.completed_at else None,
                        json.dumps(self._serialize_result(task.result)) if task.result else None,
                    ),
                )
                conn.commit()

            logger.debug(f"Stored task {task.config.task_id} in database")

    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.
        """
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_task(row)

    async def update_task(self, task: Task) -> None:
        """
        Update a task.
        """
        await self.store_task(task)  # Database storage uses INSERT OR REPLACE

    async def delete_task(self, task_id: str) -> None:
        """
        Delete a task.
        """
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
                conn.commit()

            logger.debug(f"Deleted task {task_id} from database")

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """
        List tasks, optionally filtered by status.
        """
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                if status is not None:
                    cursor = conn.execute("SELECT * FROM tasks WHERE status = ?", (status.value,))
                else:
                    cursor = conn.execute("SELECT * FROM tasks")

                rows = cursor.fetchall()
                return [self._row_to_task(row) for row in rows if self._row_to_task(row)]

    async def get_pending_tasks(self) -> list[Task]:
        """
        Get all pending tasks.
        """
        return await self.list_tasks(TaskStatus.PENDING)

    def _row_to_task(self, row) -> Task | None:
        """
        Convert a database row to a Task object.
        """
        try:
            from .orchestration import (
                Task,
                TaskConfig,
                TaskPriority,
                TaskStatus,
            )

            # Reconstruct config
            config = TaskConfig(
                task_id=row[0],
                name=row[1],
                description=row[2] or "",
                priority=TaskPriority(row[3]),
                max_retries=row[4],
                retry_delay=row[5],
                timeout=row[6],
                dependencies=json.loads(row[7]) if row[7] else [],
                tags=set(json.loads(row[8])) if row[8] else set(),
                metadata=json.loads(row[9]) if row[9] else {},
                created_at=datetime.fromisoformat(row[10]),
                scheduled_at=datetime.fromisoformat(row[11]) if row[11] else None,
            )

            # Create dummy function
            def dummy_func(*args, **kwargs):
                raise NotImplementedError("Function not available in database storage")

            # Reconstruct task
            return Task(
                config=config,
                func=dummy_func,
                args=tuple(json.loads(row[13])) if row[13] else (),
                kwargs=json.loads(row[14]) if row[14] else {},
                status=TaskStatus(row[15]),
                started_at=datetime.fromisoformat(row[16]) if row[16] else None,
                completed_at=datetime.fromisoformat(row[17]) if row[17] else None,
                result=self._deserialize_result(json.loads(row[18])) if row[18] else None,
            )

        except Exception as e:
            logger.exception(f"Failed to convert database row to task: {e}")
            return None

    def _serialize_result(self, result: TaskResult) -> dict[str, Any]:
        """
        Serialize a task result.
        """
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": str(result.error) if result.error else None,
            "execution_time": result.execution_time,
            "retry_count": result.retry_count,
            "metadata": result.metadata,
            "created_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        }

    def _deserialize_result(self, result_data: dict[str, Any]) -> TaskResult:
        """
        Deserialize a task result.
        """
        from .orchestration import TaskResult, TaskStatus

        return TaskResult(
            task_id=result_data["task_id"],
            status=TaskStatus(result_data["status"]),
            result=result_data["result"],
            error=Exception(result_data["error"]) if result_data["error"] else None,
            execution_time=result_data["execution_time"],
            retry_count=result_data["retry_count"],
            metadata=result_data["metadata"],
            created_at=datetime.fromisoformat(result_data["created_at"]),
            completed_at=(
                datetime.fromisoformat(result_data["completed_at"])
                if result_data["completed_at"]
                else None
            ),
        )


class RedisTaskStorage(TaskStorage):
    """
    Redis storage backend for tasks.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None
        self._lock = asyncio.Lock()

    async def _get_redis(self):
        """
        Get Redis connection.
        """
        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(self.redis_url)
            except ImportError:
                raise ImportError("redis package is required for RedisTaskStorage")

        return self._redis

    async def store_task(self, task: Task) -> None:
        """
        Store a task in Redis.
        """
        async with self._lock:
            redis = await self._get_redis()

            # Serialize task
            task_data = self._serialize_task(task)

            # Store in Redis
            await redis.hset(f"task:{task.config.task_id}", mapping=task_data)
            await redis.sadd("task_ids", task.config.task_id)

            logger.debug(f"Stored task {task.config.task_id} in Redis")

    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.
        """
        async with self._lock:
            redis = await self._get_redis()

            task_data = await redis.hgetall(f"task:{task_id}")
            if not task_data:
                return None

            # Convert bytes to strings
            task_data = {k.decode(): v.decode() for k, v in task_data.items()}

            return self._deserialize_task(task_data)

    async def update_task(self, task: Task) -> None:
        """
        Update a task.
        """
        await self.store_task(task)  # Redis storage just overwrites

    async def delete_task(self, task_id: str) -> None:
        """
        Delete a task.
        """
        async with self._lock:
            redis = await self._get_redis()

            await redis.delete(f"task:{task_id}")
            await redis.srem("task_ids", task_id)

            logger.debug(f"Deleted task {task_id} from Redis")

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """
        List tasks, optionally filtered by status.
        """
        async with self._lock:
            redis = await self._get_redis()

            task_ids = await redis.smembers("task_ids")
            tasks = []

            for task_id in task_ids:
                task_id = task_id.decode()
                task = await self.get_task(task_id)
                if task and (status is None or task.status == status):
                    tasks.append(task)

            return tasks

    async def get_pending_tasks(self) -> list[Task]:
        """
        Get all pending tasks.
        """
        return await self.list_tasks(TaskStatus.PENDING)

    def _serialize_task(self, task: Task) -> dict[str, str]:
        """
        Serialize a task to a dictionary.
        """
        return {
            "config": json.dumps(
                {
                    "task_id": task.config.task_id,
                    "name": task.config.name,
                    "description": task.config.description,
                    "priority": task.config.priority.value,
                    "max_retries": task.config.max_retries,
                    "retry_delay": task.config.retry_delay,
                    "timeout": task.config.timeout,
                    "dependencies": task.config.dependencies,
                    "tags": list(task.config.tags),
                    "metadata": task.config.metadata,
                    "created_at": task.config.created_at.isoformat(),
                    "scheduled_at": (
                        task.config.scheduled_at.isoformat() if task.config.scheduled_at else None
                    ),
                },
            ),
            "func_name": task.func.__name__ if hasattr(task.func, "__name__") else "unknown",
            "args": json.dumps(task.args),
            "kwargs": json.dumps(task.kwargs),
            "status": task.status.value,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": json.dumps(self._serialize_result(task.result)) if task.result else None,
        }

    def _deserialize_task(self, task_data: dict[str, str]) -> Task | None:
        """
        Deserialize a task from a dictionary.
        """
        try:
            from .orchestration import (
                Task,
                TaskConfig,
                TaskPriority,
                TaskStatus,
            )

            # Reconstruct config
            config_data = json.loads(task_data["config"])
            config = TaskConfig(
                task_id=config_data["task_id"],
                name=config_data["name"],
                description=config_data["description"],
                priority=TaskPriority(config_data["priority"]),
                max_retries=config_data["max_retries"],
                retry_delay=config_data["retry_delay"],
                timeout=config_data["timeout"],
                dependencies=config_data["dependencies"],
                tags=set(config_data["tags"]),
                metadata=config_data["metadata"],
                created_at=datetime.fromisoformat(config_data["created_at"]),
                scheduled_at=(
                    datetime.fromisoformat(config_data["scheduled_at"])
                    if config_data["scheduled_at"]
                    else None
                ),
            )

            # Create dummy function
            def dummy_func(*args, **kwargs):
                raise NotImplementedError("Function not available in Redis storage")

            # Reconstruct task
            return Task(
                config=config,
                func=dummy_func,
                args=tuple(json.loads(task_data["args"])),
                kwargs=json.loads(task_data["kwargs"]),
                status=TaskStatus(task_data["status"]),
                started_at=(
                    datetime.fromisoformat(task_data["started_at"])
                    if task_data["started_at"]
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(task_data["completed_at"])
                    if task_data["completed_at"]
                    else None
                ),
                result=(
                    self._deserialize_result(json.loads(task_data["result"]))
                    if task_data["result"]
                    else None
                ),
            )

        except Exception as e:
            logger.exception(f"Failed to deserialize task from Redis: {e}")
            return None

    def _serialize_result(self, result: TaskResult) -> dict[str, Any]:
        """
        Serialize a task result.
        """
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": str(result.error) if result.error else None,
            "execution_time": result.execution_time,
            "retry_count": result.retry_count,
            "metadata": result.metadata,
            "created_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        }

    def _deserialize_result(self, result_data: dict[str, Any]) -> TaskResult:
        """
        Deserialize a task result.
        """
        from .orchestration import TaskResult, TaskStatus

        return TaskResult(
            task_id=result_data["task_id"],
            status=TaskStatus(result_data["status"]),
            result=result_data["result"],
            error=Exception(result_data["error"]) if result_data["error"] else None,
            execution_time=result_data["execution_time"],
            retry_count=result_data["retry_count"],
            metadata=result_data["metadata"],
            created_at=datetime.fromisoformat(result_data["created_at"]),
            completed_at=(
                datetime.fromisoformat(result_data["completed_at"])
                if result_data["completed_at"]
                else None
            ),
        )
