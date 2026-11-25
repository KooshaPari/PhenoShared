"""
Adapter type enumeration.
"""

from __future__ import annotations

from enum import Enum


class AdapterType(Enum):
    """
    Supported adapter categories.
    """

    CONFIG = "config"
    AUTH = "auth"
    VECTOR = "vector"
    DEPLOY = "deploy"
    LLM = "llm"
    EVENT = "event"
    STORAGE = "storage"
    LOGGING = "logging"
    DATABASE = "database"
    MONITORING = "monitoring"
    HTTP = "http"
    MESSAGE_QUEUE = "message_queue"
    CACHE = "cache"
    ML = "ml"


__all__ = ["AdapterType"]
