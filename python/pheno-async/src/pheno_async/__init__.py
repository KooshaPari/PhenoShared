"""Pheno Async Module.

This module provides comprehensive asynchronous task orchestration capabilities.
It consolidates generic async patterns that can be used across all projects in the Pheno ecosystem.

Key Features:
- Generic task management
- Progress tracking
- Pluggable storage backends
- Task scheduling and execution
- Error handling and retry mechanisms
- Task dependencies and workflows
"""

from .execution import (
    AsyncTaskExecutor,
    SyncTaskExecutor,
    TaskExecutor,
    TaskWorker,
    WorkerPool,
)
from .monitoring import MetricsCollector, ProgressTracker, TaskMetrics, TaskMonitor
from .orchestration import (
    OrchestrationConfig,
    TaskConfig,
    TaskManager,
    TaskOrchestrator,
    TaskPriority,
    TaskResult,
    TaskScheduler,
    TaskStatus,
    WorkflowEngine,
)
from .storage import (
    DatabaseTaskStorage,
    FileTaskStorage,
    InMemoryTaskStorage,
    RedisTaskStorage,
    TaskStorage,
)

__all__ = [
    "AsyncTaskExecutor",
    "DatabaseTaskStorage",
    "FileTaskStorage",
    "InMemoryTaskStorage",
    "MetricsCollector",
    "OrchestrationConfig",
    "ProgressTracker",
    "RedisTaskStorage",
    "SyncTaskExecutor",
    "TaskConfig",
    # Execution
    "TaskExecutor",
    "TaskManager",
    "TaskMetrics",
    # Monitoring
    "TaskMonitor",
    # Core orchestration
    "TaskOrchestrator",
    "TaskPriority",
    "TaskResult",
    "TaskScheduler",
    # Task models
    "TaskStatus",
    # Storage
    "TaskStorage",
    "TaskWorker",
    "WorkerPool",
    "WorkflowEngine",
]

__version__ = "1.0.0"
