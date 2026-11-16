"""
Core async task orchestration functionality.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from pheno.logging.core.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger("pheno.async.orchestration")


class TaskStatus(Enum):
    """
    Status of a task.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    SCHEDULED = "scheduled"


class TaskPriority(Enum):
    """
    Priority levels for tasks.
    """

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(slots=True)
class TaskResult:
    """
    Result of a task execution.
    """

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Exception | None = None
    execution_time: float = 0.0
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def is_successful(self) -> bool:
        """
        Check if task completed successfully.
        """
        return self.status == TaskStatus.COMPLETED and self.error is None

    def is_failed(self) -> bool:
        """
        Check if task failed.
        """
        return self.status == TaskStatus.FAILED or self.error is not None


@dataclass(slots=True)
class TaskConfig:
    """
    Configuration for a task.
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float | None = None
    dependencies: list[str] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: datetime | None = None


@dataclass(slots=True)
class Task:
    """
    Represents a task in the orchestration system.
    """

    config: TaskConfig
    func: Callable[..., Any]
    args: tuple = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: TaskResult | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self):
        if not self.config.name:
            self.config.name = (
                self.func.__name__ if hasattr(self.func, "__name__") else "unnamed_task"
            )


@dataclass(slots=True)
class OrchestrationConfig:
    """
    Configuration for the orchestration system.
    """

    max_concurrent_tasks: int = 10
    task_timeout: float = 300.0  # 5 minutes
    retry_delay: float = 1.0
    max_retries: int = 3
    enable_metrics: bool = True
    enable_progress_tracking: bool = True
    storage_backend: str = "memory"  # memory, redis, database, file
    storage_config: dict[str, Any] = field(default_factory=dict)


class TaskStorage(ABC):
    """
    Abstract base class for task storage backends.
    """

    @abstractmethod
    async def store_task(self, task: Task) -> None:
        """
        Store a task.
        """

    @abstractmethod
    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.
        """

    @abstractmethod
    async def update_task(self, task: Task) -> None:
        """
        Update a task.
        """

    @abstractmethod
    async def delete_task(self, task_id: str) -> None:
        """
        Delete a task.
        """

    @abstractmethod
    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """
        List tasks, optionally filtered by status.
        """

    @abstractmethod
    async def get_pending_tasks(self) -> list[Task]:
        """
        Get all pending tasks.
        """


class TaskExecutor(ABC):
    """
    Abstract base class for task executors.
    """

    @abstractmethod
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task.
        """


class TaskManager:
    """
    Manages task lifecycle and execution.
    """

    def __init__(self, config: OrchestrationConfig, storage: TaskStorage, executor: TaskExecutor):
        self.config = config
        self.storage = storage
        self.executor = executor
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._task_futures: dict[str, asyncio.Future] = {}
        self._shutdown_event = asyncio.Event()

    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.
        """
        logger.info(f"Submitting task {task.config.task_id}: {task.config.name}")

        # Store the task
        await self.storage.store_task(task)

        # Check if task should be scheduled for later
        if task.config.scheduled_at and task.config.scheduled_at > datetime.now():
            task.status = TaskStatus.SCHEDULED
            await self.storage.update_task(task)
            return task.config.task_id

        # Check dependencies
        if task.config.dependencies:
            await self._wait_for_dependencies(task)

        # Execute immediately if we have capacity
        if len(self._running_tasks) < self.config.max_concurrent_tasks:
            await self._execute_task(task)
        else:
            # Queue for later execution
            task.status = TaskStatus.PENDING
            await self.storage.update_task(task)

        return task.config.task_id

    async def get_task_result(self, task_id: str) -> TaskResult | None:
        """
        Get the result of a task.
        """
        task = await self.storage.get_task(task_id)
        if task:
            return task.result
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        """
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            task.cancel()
            del self._running_tasks[task_id]

            # Update task status
            stored_task = await self.storage.get_task(task_id)
            if stored_task:
                stored_task.status = TaskStatus.CANCELLED
                stored_task.completed_at = datetime.now()
                await self.storage.update_task(stored_task)

            return True

        return False

    async def wait_for_task(self, task_id: str, timeout: float | None = None) -> TaskResult:
        """
        Wait for a task to complete.
        """
        if task_id in self._task_futures:
            try:
                return await asyncio.wait_for(self._task_futures[task_id], timeout=timeout)
            except TimeoutError:
                raise TimeoutError(f"Task {task_id} timed out")

        # Task not found or already completed
        result = await self.get_task_result(task_id)
        if result:
            return result

        raise ValueError(f"Task {task_id} not found")

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """
        List tasks, optionally filtered by status.
        """
        return await self.storage.list_tasks(status)

    async def _execute_task(self, task: Task) -> None:
        """
        Execute a task asynchronously.
        """
        logger.info(f"Executing task {task.config.task_id}: {task.config.name}")

        # Create future for waiting
        future = asyncio.Future()
        self._task_futures[task.config.task_id] = future

        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        await self.storage.update_task(task)

        # Create execution task
        execution_task = asyncio.create_task(self._run_task(task, future))
        self._running_tasks[task.config.task_id] = execution_task

        try:
            await execution_task
        except asyncio.CancelledError:
            logger.info(f"Task {task.config.task_id} was cancelled")
        finally:
            # Cleanup
            if task.config.task_id in self._running_tasks:
                del self._running_tasks[task.config.task_id]
            if task.config.task_id in self._task_futures:
                del self._task_futures[task.config.task_id]

    async def _run_task(self, task: Task, future: asyncio.Future) -> None:
        """
        Run a single task with error handling and retries.
        """
        retry_count = 0
        last_error = None

        while retry_count <= task.config.max_retries:
            try:
                # Execute the task
                result = await self.executor.execute_task(task)

                # Update task with result
                task.result = result
                task.status = result.status
                task.completed_at = result.completed_at

                await self.storage.update_task(task)

                # Set future result
                if not future.done():
                    future.set_result(result)

                logger.info(f"Task {task.config.task_id} completed with status {result.status}")
                return

            except Exception as e:
                last_error = e
                retry_count += 1

                logger.warning(f"Task {task.config.task_id} failed (attempt {retry_count}): {e}")

                if retry_count <= task.config.max_retries:
                    # Wait before retry
                    await asyncio.sleep(task.config.retry_delay * retry_count)
                    task.status = TaskStatus.RETRYING
                    await self.storage.update_task(task)
                else:
                    # Max retries exceeded
                    result = TaskResult(
                        task_id=task.config.task_id,
                        status=TaskStatus.FAILED,
                        error=e,
                        retry_count=retry_count - 1,
                        completed_at=datetime.now(),
                    )

                    task.result = result
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()

                    await self.storage.update_task(task)

                    if not future.done():
                        future.set_exception(e)

                    logger.exception(
                        f"Task {task.config.task_id} failed after {retry_count} attempts"
                    )
                    return

        # This should not be reached, but just in case
        if not future.done():
            future.set_exception(last_error or Exception("Task execution failed"))

    async def _wait_for_dependencies(self, task: Task) -> None:
        """
        Wait for task dependencies to complete.
        """
        logger.info(f"Waiting for dependencies of task {task.config.task_id}")

        for dep_id in task.config.dependencies:
            try:
                result = await self.wait_for_task(dep_id, timeout=task.config.timeout)
                if not result.is_successful():
                    raise Exception(f"Dependency {dep_id} failed")
            except Exception as e:
                logger.exception(f"Dependency {dep_id} failed for task {task.config.task_id}: {e}")
                raise

    async def shutdown(self) -> None:
        """
        Shutdown the task manager.
        """
        logger.info("Shutting down task manager")

        # Cancel all running tasks
        for task_id, task in self._running_tasks.items():
            task.cancel()
            logger.info(f"Cancelled running task {task_id}")

        # Wait for tasks to complete cancellation
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)

        self._shutdown_event.set()


class TaskScheduler:
    """
    Schedules tasks for future execution.
    """

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self._scheduled_tasks: dict[str, asyncio.Task] = {}
        self._scheduler_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """
        Start the scheduler.
        """
        logger.info("Starting task scheduler")
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """
        Stop the scheduler.
        """
        logger.info("Stopping task scheduler")
        self._shutdown_event.set()

        if self._scheduler_task:
            self._scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task

        # Cancel all scheduled tasks
        for task_id, task in self._scheduled_tasks.items():
            task.cancel()
            logger.info(f"Cancelled scheduled task {task_id}")

    async def schedule_task(self, task: Task, delay: float) -> str:
        """
        Schedule a task to run after a delay.
        """
        scheduled_time = datetime.now() + timedelta(seconds=delay)
        task.config.scheduled_at = scheduled_time

        logger.info(f"Scheduling task {task.config.task_id} for {scheduled_time}")

        # Store the task
        await self.task_manager.storage.store_task(task)

        # Create scheduled task
        scheduled_task = asyncio.create_task(self._run_scheduled_task(task, delay))
        self._scheduled_tasks[task.config.task_id] = scheduled_task

        return task.config.task_id

    async def _scheduler_loop(self) -> None:
        """
        Main scheduler loop.
        """
        while not self._shutdown_event.is_set():
            try:
                # Check for tasks that should be executed
                pending_tasks = await self.task_manager.storage.get_pending_tasks()

                for task in pending_tasks:
                    if (
                        task.config.scheduled_at
                        and task.config.scheduled_at <= datetime.now()
                        and task.status == TaskStatus.SCHEDULED
                    ):
                        # Execute the task
                        await self.task_manager._execute_task(task)

                # Sleep for a short interval
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.exception(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5.0)  # Wait longer on error

    async def _run_scheduled_task(self, task: Task, delay: float) -> None:
        """
        Run a scheduled task after delay.
        """
        try:
            await asyncio.sleep(delay)

            # Check if task was cancelled
            if task.config.task_id in self._scheduled_tasks:
                del self._scheduled_tasks[task.config.task_id]

                # Execute the task
                await self.task_manager._execute_task(task)

        except asyncio.CancelledError:
            logger.info(f"Scheduled task {task.config.task_id} was cancelled")
        except Exception as e:
            logger.exception(f"Error running scheduled task {task.config.task_id}: {e}")


class WorkflowEngine:
    """
    Manages complex workflows with multiple tasks and dependencies.
    """

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self._workflows: dict[str, list[str]] = {}  # workflow_id -> task_ids

    async def create_workflow(self, workflow_id: str, tasks: list[Task]) -> str:
        """
        Create a workflow with multiple tasks.
        """
        logger.info(f"Creating workflow {workflow_id} with {len(tasks)} tasks")

        task_ids = []

        # Submit all tasks
        for task in tasks:
            task_id = await self.task_manager.submit_task(task)
            task_ids.append(task_id)

        # Store workflow
        self._workflows[workflow_id] = task_ids

        return workflow_id

    async def wait_for_workflow(
        self,
        workflow_id: str,
        timeout: float | None = None,
    ) -> list[TaskResult]:
        """
        Wait for all tasks in a workflow to complete.
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        task_ids = self._workflows[workflow_id]
        results = []

        for task_id in task_ids:
            try:
                result = await self.task_manager.wait_for_task(task_id, timeout=timeout)
                results.append(result)
            except Exception as e:
                logger.exception(f"Task {task_id} in workflow {workflow_id} failed: {e}")
                # Create a failed result
                results.append(TaskResult(task_id=task_id, status=TaskStatus.FAILED, error=e))

        return results

    async def get_workflow_status(self, workflow_id: str) -> dict[str, TaskStatus]:
        """
        Get the status of all tasks in a workflow.
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        task_ids = self._workflows[workflow_id]
        statuses = {}

        for task_id in task_ids:
            task = await self.task_manager.storage.get_task(task_id)
            if task:
                statuses[task_id] = task.status
            else:
                statuses[task_id] = TaskStatus.FAILED

        return statuses


class TaskOrchestrator:
    """
    Main orchestrator that coordinates all async task management.
    """

    def __init__(self, config: OrchestrationConfig, storage: TaskStorage, executor: TaskExecutor):
        self.config = config
        self.task_manager = TaskManager(config, storage, executor)
        self.scheduler = TaskScheduler(self.task_manager)
        self.workflow_engine = WorkflowEngine(self.task_manager)
        self._running = False

    async def start(self) -> None:
        """
        Start the orchestrator.
        """
        if self._running:
            return

        logger.info("Starting task orchestrator")
        self._running = True

        # Start scheduler
        await self.scheduler.start()

    async def stop(self) -> None:
        """
        Stop the orchestrator.
        """
        if not self._running:
            return

        logger.info("Stopping task orchestrator")
        self._running = False

        # Stop scheduler
        await self.scheduler.stop()

        # Shutdown task manager
        await self.task_manager.shutdown()

    async def submit_task(
        self,
        func: Callable[..., Any],
        *args,
        task_config: TaskConfig | None = None,
        **kwargs,
    ) -> str:
        """
        Submit a task for execution.
        """
        if not task_config:
            task_config = TaskConfig()

        task = Task(config=task_config, func=func, args=args, kwargs=kwargs)

        return await self.task_manager.submit_task(task)

    async def schedule_task(
        self,
        func: Callable[..., Any],
        delay: float,
        *args,
        task_config: TaskConfig | None = None,
        **kwargs,
    ) -> str:
        """
        Schedule a task for future execution.
        """
        if not task_config:
            task_config = TaskConfig()

        task = Task(config=task_config, func=func, args=args, kwargs=kwargs)

        return await self.scheduler.schedule_task(task, delay)

    async def create_workflow(
        self,
        workflow_id: str,
        tasks: list[tuple[Callable, tuple, dict]],
    ) -> str:
        """
        Create a workflow with multiple tasks.
        """
        task_objects = []

        for i, (func, args, kwargs) in enumerate(tasks):
            task_config = TaskConfig(name=f"workflow_task_{i}")
            task = Task(config=task_config, func=func, args=args, kwargs=kwargs)
            task_objects.append(task)

        return await self.workflow_engine.create_workflow(workflow_id, task_objects)

    async def wait_for_task(self, task_id: str, timeout: float | None = None) -> TaskResult:
        """
        Wait for a task to complete.
        """
        return await self.task_manager.wait_for_task(task_id, timeout)

    async def wait_for_workflow(
        self,
        workflow_id: str,
        timeout: float | None = None,
    ) -> list[TaskResult]:
        """
        Wait for a workflow to complete.
        """
        return await self.workflow_engine.wait_for_workflow(workflow_id, timeout)

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        """
        return await self.task_manager.cancel_task(task_id)

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """
        List tasks.
        """
        return await self.task_manager.list_tasks(status)

    async def get_task_result(self, task_id: str) -> TaskResult | None:
        """
        Get task result.
        """
        return await self.task_manager.get_task_result(task_id)

    @property
    def is_running(self) -> bool:
        """
        Check if orchestrator is running.
        """
        return self._running
