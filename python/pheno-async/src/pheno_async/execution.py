"""
Task execution engines and workers.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from pheno.logging.core.logger import get_logger

from .orchestration import Task, TaskExecutor, TaskResult, TaskStatus

logger = get_logger("pheno.async.execution")


class AsyncTaskExecutor(TaskExecutor):
    """
    Async task executor that runs tasks in asyncio event loop.
    """

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task asynchronously.
        """
        start_time = time.time()

        try:
            logger.info(f"Executing async task {task.config.task_id}: {task.config.name}")

            # Check if function is async
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, task.func, *task.args, **task.kwargs)

            execution_time = time.time() - start_time

            return TaskResult(
                task_id=task.config.task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                completed_at=time.time(),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"Task {task.config.task_id} failed: {e}")

            return TaskResult(
                task_id=task.config.task_id,
                status=TaskStatus.FAILED,
                error=e,
                execution_time=execution_time,
                completed_at=time.time(),
            )


class SyncTaskExecutor(TaskExecutor):
    """
    Synchronous task executor that runs tasks in thread pool.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task synchronously in thread pool.
        """
        start_time = time.time()

        try:
            logger.info(f"Executing sync task {task.config.task_id}: {task.config.name}")

            # Run in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                task.func,
                *task.args,
                **task.kwargs,
            )

            execution_time = time.time() - start_time

            return TaskResult(
                task_id=task.config.task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                completed_at=time.time(),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"Task {task.config.task_id} failed: {e}")

            return TaskResult(
                task_id=task.config.task_id,
                status=TaskStatus.FAILED,
                error=e,
                execution_time=execution_time,
                completed_at=time.time(),
            )

    def shutdown(self) -> None:
        """
        Shutdown the thread pool executor.
        """
        self._executor.shutdown(wait=True)


@dataclass(slots=True)
class TaskWorker:
    """
    Individual task worker.
    """

    worker_id: str
    task_executor: TaskExecutor
    is_running: bool = False
    current_task: Task | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task.
        """
        self.is_running = True
        self.current_task = task

        try:
            result = await self.task_executor.execute_task(task)

            if result.is_successful():
                self.tasks_completed += 1
            else:
                self.tasks_failed += 1

            self.total_execution_time += result.execution_time
            return result

        finally:
            self.is_running = False
            self.current_task = None


class WorkerPool:
    """
    Pool of task workers.
    """

    def __init__(self, size: int, task_executor: TaskExecutor):
        self.size = size
        self.task_executor = task_executor
        self.workers: list[TaskWorker] = []
        self._available_workers: asyncio.Queue = asyncio.Queue()
        self._shutdown_event = asyncio.Event()

        # Initialize workers
        for i in range(size):
            worker = TaskWorker(worker_id=f"worker-{i}", task_executor=task_executor)
            self.workers.append(worker)
            self._available_workers.put_nowait(worker)

    async def start(self) -> None:
        """
        Start the worker pool.
        """
        logger.info(f"Started worker pool with {self.size} workers")

    async def stop(self) -> None:
        """
        Stop the worker pool.
        """
        logger.info("Stopping worker pool")
        self._shutdown_event.set()

        # Wait for all workers to finish current tasks
        for worker in self.workers:
            while worker.is_running:
                await asyncio.sleep(0.1)

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task using an available worker.
        """
        # Wait for available worker
        worker = await self._available_workers.get()

        try:
            # Execute task
            return await worker.execute_task(task)

        finally:
            # Return worker to pool
            self._available_workers.put_nowait(worker)

    def get_stats(self) -> dict[str, Any]:
        """
        Get worker pool statistics.
        """
        total_tasks = sum(w.tasks_completed + w.tasks_failed for w in self.workers)
        total_time = sum(w.total_execution_time for w in self.workers)
        active_workers = sum(1 for w in self.workers if w.is_running)

        return {
            "total_workers": self.size,
            "active_workers": active_workers,
            "idle_workers": self.size - active_workers,
            "total_tasks_completed": sum(w.tasks_completed for w in self.workers),
            "total_tasks_failed": sum(w.tasks_failed for w in self.workers),
            "total_execution_time": total_time,
            "average_execution_time": total_time / max(1, total_tasks),
            "worker_stats": [
                {
                    "worker_id": w.worker_id,
                    "is_running": w.is_running,
                    "current_task": w.current_task.config.task_id if w.current_task else None,
                    "tasks_completed": w.tasks_completed,
                    "tasks_failed": w.tasks_failed,
                    "total_execution_time": w.total_execution_time,
                }
                for w in self.workers
            ],
        }


class HybridTaskExecutor(TaskExecutor):
    """
    Hybrid executor that can run both async and sync tasks.
    """

    def __init__(self, max_workers: int = 4):
        self.async_executor = AsyncTaskExecutor()
        self.sync_executor = SyncTaskExecutor(max_workers=max_workers)

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task using appropriate executor.
        """
        # Check if function is async
        if asyncio.iscoroutinefunction(task.func):
            return await self.async_executor.execute_task(task)
        return await self.sync_executor.execute_task(task)

    def shutdown(self) -> None:
        """
        Shutdown the hybrid executor.
        """
        self.sync_executor.shutdown()


class ProcessTaskExecutor(TaskExecutor):
    """
    Process-based task executor for CPU-intensive tasks.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = None

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task in a separate process.
        """
        start_time = time.time()

        try:
            logger.info(f"Executing process task {task.config.task_id}: {task.config.name}")

            # Create process pool if not exists
            if self._executor is None:
                from concurrent.futures import ProcessPoolExecutor

                self._executor = ProcessPoolExecutor(max_workers=self.max_workers)

            # Run in process pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                task.func,
                *task.args,
                **task.kwargs,
            )

            execution_time = time.time() - start_time

            return TaskResult(
                task_id=task.config.task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                completed_at=time.time(),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"Process task {task.config.task_id} failed: {e}")

            return TaskResult(
                task_id=task.config.task_id,
                status=TaskStatus.FAILED,
                error=e,
                execution_time=execution_time,
                completed_at=time.time(),
            )

    def shutdown(self) -> None:
        """
        Shutdown the process pool executor.
        """
        if self._executor:
            self._executor.shutdown(wait=True)


class TaskExecutionEngine:
    """
    High-level task execution engine with multiple strategies.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.executors: dict[str, TaskExecutor] = {}
        self.worker_pools: dict[str, WorkerPool] = {}
        self._setup_executors()

    def _setup_executors(self) -> None:
        """
        Setup different types of executors.
        """
        # Async executor
        self.executors["async"] = AsyncTaskExecutor()

        # Sync executor
        max_workers = self.config.get("max_workers", 4)
        self.executors["sync"] = SyncTaskExecutor(max_workers=max_workers)

        # Hybrid executor
        self.executors["hybrid"] = HybridTaskExecutor(max_workers=max_workers)

        # Process executor
        self.executors["process"] = ProcessTaskExecutor(max_workers=max_workers)

        # Worker pools
        self.worker_pools["async"] = WorkerPool(max_workers, self.executors["async"])
        self.worker_pools["sync"] = WorkerPool(max_workers, self.executors["sync"])
        self.worker_pools["hybrid"] = WorkerPool(max_workers, self.executors["hybrid"])

    async def start(self) -> None:
        """
        Start all worker pools.
        """
        for pool in self.worker_pools.values():
            await pool.start()

    async def stop(self) -> None:
        """
        Stop all worker pools and executors.
        """
        for pool in self.worker_pools.values():
            await pool.stop()

        for executor in self.executors.values():
            if hasattr(executor, "shutdown"):
                executor.shutdown()

    async def execute_task(self, task: Task, executor_type: str = "hybrid") -> TaskResult:
        """
        Execute a task using specified executor type.
        """
        if executor_type in self.worker_pools:
            return await self.worker_pools[executor_type].execute_task(task)
        if executor_type in self.executors:
            return await self.executors[executor_type].execute_task(task)
        raise ValueError(f"Unknown executor type: {executor_type}")

    def get_executor_stats(self) -> dict[str, Any]:
        """
        Get statistics for all executors and worker pools.
        """
        stats = {}

        for name, pool in self.worker_pools.items():
            stats[f"pool_{name}"] = pool.get_stats()

        return stats

    def choose_executor_type(self, task: Task) -> str:
        """
        Choose the best executor type for a task.
        """
        # Simple heuristic based on function type
        if asyncio.iscoroutinefunction(task.func):
            return "async"
        # Check if it's CPU intensive (heuristic)
        if any(
            keyword in task.config.name.lower()
            for keyword in ["compute", "calculate", "process", "analyze"]
        ):
            return "process"
        return "sync"
