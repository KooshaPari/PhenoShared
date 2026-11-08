"""AI Prompt Logger - Scrapes prompts from various AI agent platforms.

Supports:
- Cursor Agent
- Forge Code (forgecode.dev/forge)
- Claude (claude.ai)
- Factory Droid
- OpenCode
- Kilo Code
- Codex (OpenAI)

Usage:
    from prompt_logger import PromptLogger
    
    logger = PromptLogger()
    logger.log_prompt("cursor-agent", "user query here")
"""

import json
import sqlite3
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class PromptEntry:
    """Single prompt entry in the log."""
    id: str
    agent: str
    prompt: str
    timestamp: str
    session_id: Optional[str]
    user_id: Optional[str]
    metadata: dict
    
    def to_dict(self) -> dict:
        return asdict(self)


class PromptLogger:
    """Centralized prompt logger for all AI agents."""
    
    def __init__(self, db_path: str = "ai_prompts.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                prompt TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                user_id TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent ON prompts(agent)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON prompts(timestamp)
        """)
        conn.commit()
        conn.close()
    
    def _generate_id(self, prompt: str, agent: str) -> str:
        """Generate unique ID for prompt."""
        data = f"{agent}:{prompt}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def log_prompt(
        self,
        agent: str,
        prompt: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> PromptEntry:
        """Log a prompt from an AI agent."""
        entry = PromptEntry(
            id=self._generate_id(prompt, agent),
            agent=agent,
            prompt=prompt,
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO prompts (id, agent, prompt, timestamp, session_id, user_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.agent,
            entry.prompt,
            entry.timestamp,
            entry.session_id,
            entry.user_id,
            json.dumps(entry.metadata)
        ))
        conn.commit()
        conn.close()
        
        return entry
    
    def get_prompts(
        self,
        agent: Optional[str] = None,
        limit: int = 100
    ) -> list[PromptEntry]:
        """Retrieve prompts, optionally filtered by agent."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if agent:
            cursor.execute("""
                SELECT * FROM prompts WHERE agent = ? ORDER BY timestamp DESC LIMIT ?
            """, (agent, limit))
        else:
            cursor.execute("""
                SELECT * FROM prompts ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            PromptEntry(
                id=row['id'],
                agent=row['agent'],
                prompt=row['prompt'],
                timestamp=row['timestamp'],
                session_id=row['session_id'],
                user_id=row['user_id'],
                metadata=json.loads(row['metadata'] or '{}')
            )
            for row in rows
        ]
    
    def export_to_jsonl(self, output_path: str = "prompts.jsonl"):
        """Export all prompts to JSONL format."""
        prompts = self.get_prompts(limit=100000)
        with open(output_path, 'w') as f:
            for prompt in prompts:
                f.write(json.dumps(prompt.to_dict()) + '\n')
        return len(prompts)
    
    def export_to_onml(self, output_path: str = "prompts.onml"):
        """Export all prompts to ONML (Ordered Newline Manifest Language) format."""
        prompts = self.get_prompts(limit=100000)
        with open(output_path, 'w') as f:
            for prompt in prompts:
                f.write(f"# PROMPT {prompt.id}\n")
                f.write(f"@agent: {prompt.agent}\n")
                f.write(f"@timestamp: {prompt.timestamp}\n")
                f.write(f"@session: {prompt.session_id or 'none'}\n")
                f.write(f"@user: {prompt.user_id or 'none'}\n")
                if prompt.metadata:
                    f.write(f"@metadata: {json.dumps(prompt.metadata)}\n")
                f.write("---\n")
                f.write(prompt.prompt)
                f.write("\n---\n\n")
        return len(prompts)


# Agent-specific loggers
class CursorAgentLogger(PromptLogger):
    """Logger specifically for Cursor Agent."""
    
    def log_cursor_prompt(self, prompt: str, file_context: Optional[str] = None):
        return self.log_prompt(
            agent="cursor-agent",
            prompt=prompt,
            metadata={"context": file_context}
        )


class ForgeCodeLogger(PromptLogger):
    """Logger specifically for Forge Code (forgecode.dev)."""
    
    def log_forge_prompt(self, prompt: str, workspace: Optional[str] = None):
        return self.log_prompt(
            agent="forge-code",
            prompt=prompt,
            metadata={"workspace": workspace}
        )


class ClaudeLogger(PromptLogger):
    """Logger specifically for Claude."""
    
    def log_claude_prompt(self, prompt: str, model: str = "claude-3"):
        return self.log_prompt(
            agent="claude",
            prompt=prompt,
            metadata={"model": model}
        )


class FactoryDroidLogger(PromptLogger):
    """Logger specifically for Factory Droid."""
    
    def log_factory_prompt(self, prompt: str, task_type: str = "general"):
        return self.log_prompt(
            agent="factory-droid",
            prompt=prompt,
            metadata={"task_type": task_type}
        )


class OpenCodeLogger(PromptLogger):
    """Logger specifically for OpenCode."""
    
    def log_opencode_prompt(self, prompt: str, language: str = "unknown"):
        return self.log_prompt(
            agent="opencode",
            prompt=prompt,
            metadata={"language": language}
        )


class KiloCodeLogger(PromptLogger):
    """Logger specifically for Kilo Code."""
    
    def log_kilocode_prompt(self, prompt: str, context: str = "general"):
        return self.log_prompt(
            agent="kilo-code",
            prompt=prompt,
            metadata={"context": context}
        )


class CodexLogger(PromptLogger):
    """Logger specifically for OpenAI Codex."""
    
    def log_codex_prompt(self, prompt: str, language: str = "python"):
        return self.log_prompt(
            agent="codex",
            prompt=prompt,
            metadata={"language": language}
        )


if __name__ == "__main__":
    # Example usage
    logger = PromptLogger()
    
    # Log prompts from various agents
    logger.log_cursor_prompt("Fix the authentication bug in login.py")
    logger.log_forge_prompt("Add unit tests for the API endpoints")
    logger.log_claude_prompt("Refactor the database schema")
    logger.log_factory_prompt("Optimize the query performance")
    logger.log_opencode_prompt("Add error handling to the service")
    logger.log_kilocode_prompt("Update the documentation")
    logger.log_codex_prompt("Create a new API endpoint")
    
    # Export
    count = logger.export_to_jsonl()
    print(f"Exported {count} prompts to prompts.jsonl")
    
    count = logger.export_to_onml()
    print(f"Exported {count} prompts to prompts.onml")
