"""
Task monitoring and metrics collection.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from pheno.logging.core.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from .orchestration import Task, TaskResult, TaskStatus

logger = get_logger("pheno.async.monitoring")


@dataclass(slots=True)
class TaskMetrics:
    """
    Metrics for task execution.
    """

    # Counts
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    retried_tasks: int = 0

    # Timing
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    min_execution_time: float = float("inf")
    max_execution_time: float = 0.0

    # Throughput
    tasks_per_second: float = 0.0
    tasks_per_minute: float = 0.0

    # Status distribution
    status_counts: dict[TaskStatus, int] = field(default_factory=lambda: defaultdict(int))

    # Recent activity
    recent_tasks: deque = field(default_factory=lambda: deque(maxlen=100))

    def update_with_task(self, task: Task, result: TaskResult | None = None) -> None:
        """
        Update metrics with a task.
        """
        self.total_tasks += 1
        self.status_counts[task.status] += 1

        if result:
            if result.is_successful():
                self.completed_tasks += 1
            elif result.is_failed():
                self.failed_tasks += 1

            if result.retry_count > 0:
                self.retried_tasks += 1

            # Update timing metrics
            if result.execution_time > 0:
                self.total_execution_time += result.execution_time
                self.min_execution_time = min(self.min_execution_time, result.execution_time)
                self.max_execution_time = max(self.max_execution_time, result.execution_time)
                self.average_execution_time = self.total_execution_time / max(
                    1,
                    self.completed_tasks,
                )

        # Add to recent tasks
        self.recent_tasks.append(
            {
                "task_id": task.config.task_id,
                "name": task.config.name,
                "status": task.status.value,
                "execution_time": result.execution_time if result else 0.0,
                "timestamp": datetime.now(),
            },
        )

    def get_success_rate(self) -> float:
        """
        Get task success rate.
        """
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    def get_failure_rate(self) -> float:
        """
        Get task failure rate.
        """
        if self.total_tasks == 0:
            return 0.0
        return self.failed_tasks / self.total_tasks

    def get_retry_rate(self) -> float:
        """
        Get task retry rate.
        """
        if self.total_tasks == 0:
            return 0.0
        return self.retried_tasks / self.total_tasks

    def to_dict(self) -> dict[str, Any]:
        """
        Convert metrics to dictionary.
        """
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "cancelled_tasks": self.cancelled_tasks,
            "retried_tasks": self.retried_tasks,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.average_execution_time,
            "min_execution_time": (
                self.min_execution_time if self.min_execution_time != float("inf") else 0.0
            ),
            "max_execution_time": self.max_execution_time,
            "tasks_per_second": self.tasks_per_second,
            "tasks_per_minute": self.tasks_per_minute,
            "success_rate": self.get_success_rate(),
            "failure_rate": self.get_failure_rate(),
            "retry_rate": self.get_retry_rate(),
            "status_counts": {status.value: count for status, count in self.status_counts.items()},
            "recent_tasks": list(self.recent_tasks),
        }


class ProgressTracker:
    """
    Tracks progress of individual tasks and workflows.
    """

    def __init__(self):
        self._task_progress: dict[str, dict[str, Any]] = {}
        self._workflow_progress: dict[str, dict[str, Any]] = {}
        self._progress_callbacks: list[Callable[[str, dict[str, Any]], None]] = []

    def start_task_tracking(self, task_id: str, total_steps: int = 1) -> None:
        """
        Start tracking progress for a task.
        """
        self._task_progress[task_id] = {
            "total_steps": total_steps,
            "completed_steps": 0,
            "current_step": 0,
            "progress_percentage": 0.0,
            "started_at": datetime.now(),
            "last_updated": datetime.now(),
            "status": "running",
        }
        self._notify_progress(task_id, self._task_progress[task_id])

    def update_task_progress(
        self,
        task_id: str,
        completed_steps: int | None = None,
        current_step: int | None = None,
        message: str | None = None,
    ) -> None:
        """
        Update progress for a task.
        """
        if task_id not in self._task_progress:
            return

        progress = self._task_progress[task_id]

        if completed_steps is not None:
            progress["completed_steps"] = completed_steps
        if current_step is not None:
            progress["current_step"] = current_step
        if message is not None:
            progress["message"] = message

        # Calculate percentage
        if progress["total_steps"] > 0:
            progress["progress_percentage"] = (
                progress["completed_steps"] / progress["total_steps"]
            ) * 100

        progress["last_updated"] = datetime.now()

        self._notify_progress(task_id, progress)

    def complete_task_tracking(self, task_id: str, success: bool = True) -> None:
        """
        Complete tracking for a task.
        """
        if task_id not in self._task_progress:
            return

        progress = self._task_progress[task_id]
        progress["completed_steps"] = progress["total_steps"]
        progress["progress_percentage"] = 100.0
        progress["status"] = "completed" if success else "failed"
        progress["completed_at"] = datetime.now()
        progress["last_updated"] = datetime.now()

        self._notify_progress(task_id, progress)

    def start_workflow_tracking(self, workflow_id: str, total_tasks: int) -> None:
        """
        Start tracking progress for a workflow.
        """
        self._workflow_progress[workflow_id] = {
            "total_tasks": total_tasks,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "progress_percentage": 0.0,
            "started_at": datetime.now(),
            "last_updated": datetime.now(),
            "status": "running",
            "tasks": {},
        }
        self._notify_progress(workflow_id, self._workflow_progress[workflow_id])

    def update_workflow_progress(
        self,
        workflow_id: str,
        task_id: str,
        task_status: str,
        task_progress: dict[str, Any] | None = None,
    ) -> None:
        """
        Update progress for a workflow.
        """
        if workflow_id not in self._workflow_progress:
            return

        progress = self._workflow_progress[workflow_id]
        progress["tasks"][task_id] = {
            "status": task_status,
            "progress": task_progress or {},
            "updated_at": datetime.now(),
        }

        # Update counts
        if task_status == "completed":
            progress["completed_tasks"] += 1
        elif task_status == "failed":
            progress["failed_tasks"] += 1

        # Calculate percentage
        total_processed = progress["completed_tasks"] + progress["failed_tasks"]
        if progress["total_tasks"] > 0:
            progress["progress_percentage"] = (total_processed / progress["total_tasks"]) * 100

        progress["last_updated"] = datetime.now()

        self._notify_progress(workflow_id, progress)

    def complete_workflow_tracking(self, workflow_id: str, success: bool = True) -> None:
        """
        Complete tracking for a workflow.
        """
        if workflow_id not in self._workflow_progress:
            return

        progress = self._workflow_progress[workflow_id]
        progress["status"] = "completed" if success else "failed"
        progress["completed_at"] = datetime.now()
        progress["last_updated"] = datetime.now()

        self._notify_progress(workflow_id, progress)

    def get_task_progress(self, task_id: str) -> dict[str, Any] | None:
        """
        Get progress for a task.
        """
        return self._task_progress.get(task_id)

    def get_workflow_progress(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get progress for a workflow.
        """
        return self._workflow_progress.get(workflow_id)

    def add_progress_callback(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """
        Add a progress callback.
        """
        self._progress_callbacks.append(callback)

    def _notify_progress(self, entity_id: str, progress: dict[str, Any]) -> None:
        """
        Notify progress callbacks.
        """
        for callback in self._progress_callbacks:
            try:
                callback(entity_id, progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")


class MetricsCollector:
    """
    Collects and aggregates metrics from task execution.
    """

    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.metrics = TaskMetrics()
        self._collection_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._task_history: deque = deque(maxlen=1000)
        self._throughput_window = 60.0  # seconds
        self._throughput_data: deque = deque()

    async def start(self) -> None:
        """
        Start metrics collection.
        """
        if self._collection_task is not None:
            return

        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Started metrics collection")

    async def stop(self) -> None:
        """
        Stop metrics collection.
        """
        if self._collection_task is None:
            return

        self._shutdown_event.set()
        self._collection_task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await self._collection_task

        logger.info("Stopped metrics collection")

    def record_task(self, task: Task, result: TaskResult | None = None) -> None:
        """
        Record a task execution.
        """
        self.metrics.update_with_task(task, result)

        # Add to history
        self._task_history.append(
            {
                "task_id": task.config.task_id,
                "name": task.config.name,
                "status": task.status.value,
                "execution_time": result.execution_time if result else 0.0,
                "timestamp": datetime.now(),
            },
        )

        # Add to throughput data
        self._throughput_data.append(datetime.now())

    def get_metrics(self) -> TaskMetrics:
        """
        Get current metrics.
        """
        return self.metrics

    def get_metrics_dict(self) -> dict[str, Any]:
        """
        Get metrics as dictionary.
        """
        return self.metrics.to_dict()

    def get_recent_tasks(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent task executions.
        """
        return list(self._task_history)[-limit:]

    def get_throughput_metrics(self) -> dict[str, float]:
        """
        Get throughput metrics.
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self._throughput_window)

        # Filter recent data
        recent_data = [ts for ts in self._throughput_data if ts >= cutoff]

        if len(recent_data) < 2:
            return {"tasks_per_second": 0.0, "tasks_per_minute": 0.0}

        # Calculate throughput
        time_span = (recent_data[-1] - recent_data[0]).total_seconds()
        if time_span > 0:
            tasks_per_second = len(recent_data) / time_span
            tasks_per_minute = tasks_per_second * 60
        else:
            tasks_per_second = 0.0
            tasks_per_minute = 0.0

        # Update metrics
        self.metrics.tasks_per_second = tasks_per_second
        self.metrics.tasks_per_minute = tasks_per_minute

        return {"tasks_per_second": tasks_per_second, "tasks_per_minute": tasks_per_minute}

    async def _collection_loop(self) -> None:
        """
        Main metrics collection loop.
        """
        while not self._shutdown_event.is_set():
            try:
                # Update throughput metrics
                self.get_throughput_metrics()

                # Clean old throughput data
                cutoff = datetime.now() - timedelta(seconds=self._throughput_window)
                while self._throughput_data and self._throughput_data[0] < cutoff:
                    self._throughput_data.popleft()

                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.exception(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5.0)


class TaskMonitor:
    """
    High-level task monitoring system.
    """

    def __init__(self, collection_interval: float = 1.0):
        self.metrics_collector = MetricsCollector(collection_interval)
        self.progress_tracker = ProgressTracker()
        self._alerts: list[Callable[[str, dict[str, Any]], None]] = []
        self._thresholds = {
            "failure_rate": 0.1,  # 10%
            "average_execution_time": 30.0,  # 30 seconds
            "queue_size": 100,
        }

    async def start(self) -> None:
        """
        Start monitoring.
        """
        await self.metrics_collector.start()
        logger.info("Started task monitoring")

    async def stop(self) -> None:
        """
        Stop monitoring.
        """
        await self.metrics_collector.stop()
        logger.info("Stopped task monitoring")

    def record_task(self, task: Task, result: TaskResult | None = None) -> None:
        """
        Record a task execution.
        """
        self.metrics_collector.record_task(task, result)
        self._check_alerts()

    def start_task_progress(self, task_id: str, total_steps: int = 1) -> None:
        """
        Start tracking progress for a task.
        """
        self.progress_tracker.start_task_tracking(task_id, total_steps)

    def update_task_progress(self, task_id: str, **kwargs) -> None:
        """
        Update progress for a task.
        """
        self.progress_tracker.update_task_progress(task_id, **kwargs)

    def complete_task_progress(self, task_id: str, success: bool = True) -> None:
        """
        Complete progress tracking for a task.
        """
        self.progress_tracker.complete_task_tracking(task_id, success)

    def start_workflow_progress(self, workflow_id: str, total_tasks: int) -> None:
        """
        Start tracking progress for a workflow.
        """
        self.progress_tracker.start_workflow_tracking(workflow_id, total_tasks)

    def update_workflow_progress(
        self,
        workflow_id: str,
        task_id: str,
        task_status: str,
        task_progress: dict[str, Any] | None = None,
    ) -> None:
        """
        Update progress for a workflow.
        """
        self.progress_tracker.update_workflow_progress(
            workflow_id,
            task_id,
            task_status,
            task_progress,
        )

    def complete_workflow_progress(self, workflow_id: str, success: bool = True) -> None:
        """
        Complete progress tracking for a workflow.
        """
        self.progress_tracker.complete_workflow_tracking(workflow_id, success)

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current metrics.
        """
        return self.metrics_collector.get_metrics_dict()

    def get_task_progress(self, task_id: str) -> dict[str, Any] | None:
        """
        Get progress for a task.
        """
        return self.progress_tracker.get_task_progress(task_id)

    def get_workflow_progress(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get progress for a workflow.
        """
        return self.progress_tracker.get_workflow_progress(workflow_id)

    def add_alert_callback(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """
        Add an alert callback.
        """
        self._alerts.append(callback)

    def add_progress_callback(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """
        Add a progress callback.
        """
        self.progress_tracker.add_progress_callback(callback)

    def set_threshold(self, metric: str, value: float) -> None:
        """
        Set alert threshold for a metric.
        """
        self._thresholds[metric] = value

    def _check_alerts(self) -> None:
        """
        Check for alert conditions.
        """
        metrics = self.metrics_collector.get_metrics()

        # Check failure rate
        if metrics.get_success_rate() < (1 - self._thresholds["failure_rate"]):
            self._trigger_alert(
                "high_failure_rate",
                {
                    "failure_rate": metrics.get_failure_rate(),
                    "threshold": self._thresholds["failure_rate"],
                },
            )

        # Check average execution time
        if metrics.average_execution_time > self._thresholds["average_execution_time"]:
            self._trigger_alert(
                "slow_execution",
                {
                    "average_execution_time": metrics.average_execution_time,
                    "threshold": self._thresholds["average_execution_time"],
                },
            )

    def _trigger_alert(self, alert_type: str, data: dict[str, Any]) -> None:
        """
        Trigger an alert.
        """
        alert_data = {"type": alert_type, "timestamp": datetime.now(), "data": data}

        for callback in self._alerts:
            try:
                callback(alert_type, alert_data)
            except Exception as e:
                logger.warning(f"Alert callback failed: {e}")

    def get_health_status(self) -> dict[str, Any]:
        """
        Get overall health status.
        """
        metrics = self.metrics_collector.get_metrics()

        health_score = 100.0

        # Deduct points for failures
        if metrics.get_failure_rate() > 0.05:  # 5%
            health_score -= metrics.get_failure_rate() * 100

        # Deduct points for slow execution
        if metrics.average_execution_time > 10.0:  # 10 seconds
            health_score -= min(20, (metrics.average_execution_time - 10) * 2)

        # Determine status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "health_score": health_score,
            "metrics": metrics.to_dict(),
            "timestamp": datetime.now(),
        }
