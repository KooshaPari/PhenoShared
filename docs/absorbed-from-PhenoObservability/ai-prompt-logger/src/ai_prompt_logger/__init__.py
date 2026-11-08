"""AI Prompt Logger - Captures prompts from all AI agents.

Supports:
- Cursor-agent (cursorai.com)
- Forge (forgecode.dev)
- Claude (claude.ai)
- CodeX/Claude Team
- Factory Droid
- OpenCode
- Kilo Code
- Any Claude-compatible API

Usage:
    from ai_prompt_logger import PromptLogger
    
    logger = PromptLogger()
    logger.log_prompt(
        agent="cursor",
        prompt="user request...",
        response="ai response...",
        metadata={"model": "claude-3-opus", "tokens": 1234}
    )
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class AgentType(str, Enum):
    """Supported AI agent types."""
    
    CURSOR = "cursor"
    FORGE = "forge"
    CODEX = "codex"
    CLAUDE = "claude"
    FACTORY_DROID = "factory_droid"
    OPENCODE = "opencode"
    KILO_CODE = "kilo_code"
    UNKNOWN = "unknown"


class PromptLogger:
    """Thread-safe prompt logging to SQLite + ONML files."""
    
    def __init__(
        self,
        db_path: str = "~/.local/share/ai-prompt-logger/prompts.db",
        onml_dir: str = "~/.local/share/ai-prompt-logger/onml/",
    ):
        self.db_path = Path(db_path).expanduser()
        self.onml_dir = Path(onml_dir).expanduser()
        self._local = threading.local()
        self._ensure_db()
        self.onml_dir.mkdir(parents=True, exist_ok=True)
    
    def _ensure_db(self) -> None:
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT,
                model TEXT,
                tokens_used INTEGER,
                duration_ms INTEGER,
                metadata TEXT,
                onml_file TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_timestamp 
            ON prompts(agent, timestamp)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                session_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                prompt_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(str(self.db_path))
        return self._local.conn
    
    def log_prompt(
        self,
        agent: str,
        prompt: str,
        response: Optional[str] = None,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> int:
        """Log a single prompt interaction.
        
        Returns:
            The row ID of the inserted record.
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Write ONML file
        onml_file = self._write_onml(
            agent=agent,
            timestamp=timestamp,
            prompt=prompt,
            response=response,
            metadata=metadata,
        )
        
        # Insert into SQLite
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO prompts 
            (agent, timestamp, prompt, response, model, tokens_used, 
             duration_ms, metadata, onml_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent,
                timestamp,
                prompt,
                response,
                model,
                tokens_used,
                duration_ms,
                json.dumps(metadata) if metadata else None,
                str(onml_file) if onml_file else None,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def _write_onml(
        self,
        agent: str,
        timestamp: str,
        prompt: str,
        response: Optional[str],
        metadata: Optional[dict[str, Any]],
    ) -> Path:
        """Write prompt to ONML file.
        
        ONML format: Ordered Non-JSON Metadata Language
        Human-readable, newline-delimited with metadata headers.
        """
        date_str = timestamp[:10]  # YYYY-MM-DD
        safe_agent = agent.replace("/", "_").replace(" ", "_")
        filename = f"{date_str}_{safe_agent}_{timestamp[11:19].replace(':', '')}.onml"
        filepath = self.onml_dir / filename
        
        with open(filepath, "w") as f:
            f.write("# ONML - AI Prompt Log\n")
            f.write(f"# Agent: {agent}\n")
            f.write(f"# Timestamp: {timestamp}\n")
            
            if metadata:
                f.write("# Metadata:\n")
                for key, value in metadata.items():
                    f.write(f"#   {key}: {value}\n")
            
            f.write("---\n\n")
            f.write(f"[PROMPT]\n{prompt}\n\n")
            
            if response:
                f.write(f"[RESPONSE]\n{response}\n")
        
        return filepath
    
    def query_prompts(
        self,
        agent: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query logged prompts."""
        query = "SELECT * FROM prompts WHERE 1=1"
        params: list[Any] = []
        
        if agent:
            query += " AND agent = ?"
            params.append(agent)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_stats(self) -> dict[str, Any]:
        """Get logging statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM prompts")
        total_prompts = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT agent, COUNT(*) FROM prompts GROUP BY agent ORDER BY COUNT(*) DESC"
        )
        by_agent = dict(cursor.fetchall())
        
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM prompts")
        date_range = cursor.fetchone()
        
        return {
            "total_prompts": total_prompts,
            "by_agent": by_agent,
            "date_range": {"start": date_range[0], "end": date_range[1]}
            if date_range[0] else None,
            "db_path": str(self.db_path),
            "onml_dir": str(self.onml_dir),
        }
    
    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            del self._local.conn


# Global logger instance
_logger: Optional[PromptLogger] = None


def get_logger() -> PromptLogger:
    """Get or create global logger instance."""
    global _logger
    if _logger is None:
        _logger = PromptLogger()
    return _logger


def log_prompt(**kwargs) -> int:
    """Convenience function to log a prompt."""
    return get_logger().log_prompt(**kwargs)


__all__ = [
    "PromptLogger",
    "AgentType",
    "get_logger",
    "log_prompt",
]
