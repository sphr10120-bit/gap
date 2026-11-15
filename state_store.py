from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any


class ConversationMemory:
    """Bounded, in-process transcript; message text is never written to SQLite."""

    def __init__(self, *, ttl_seconds: int, max_messages: int = 12) -> None:
        self.ttl_seconds = max(60, int(ttl_seconds))
        self.max_messages = max(2, int(max_messages))
        self._messages: dict[int, list[dict[str, Any]]] = {}

    def add(
        self,
        chat_id: int,
        message_id: int,
        role: str,
        text: str,
        *,
        author: str = "",
        at: float | None = None,
    ) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        cleaned = (text or "").strip()[:1200]
        if not cleaned:
            return
        timestamp = time.time() if at is None else at
        self.purge_expired(now=timestamp, chat_id=chat_id)
        messages = self._messages.setdefault(chat_id, [])
        messages.append({
            "chat_id": chat_id,
            "message_id": message_id,
            "role": role,
            "author": (author or "")[:80],
            "text": cleaned,
            "created_at": timestamp,
        })
        self._messages[chat_id] = messages[-self.max_messages:]

    def recent(
        self,
        chat_id: int,
        *,
        now: float | None = None,
        exclude_message_id: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        timestamp = time.time() if now is None else now
        self.purge_expired(now=timestamp, chat_id=chat_id)
        count = self.max_messages if limit is None else max(1, min(limit, self.max_messages))
        messages = [
            item for item in self._messages.get(chat_id, [])
            if exclude_message_id is None or item["message_id"] != exclude_message_id
        ]
        return [dict(item) for item in messages[-count:]]

    def purge_expired(self, *, now: float | None = None, chat_id: int | None = None) -> None:
        timestamp = time.time() if now is None else now
        cutoff = timestamp - self.ttl_seconds
        chat_ids = [chat_id] if chat_id is not None else list(self._messages)
        for current_chat_id in chat_ids:
            retained = [
                item for item in self._messages.get(current_chat_id, [])
                if item["created_at"] >= cutoff
            ]
            if retained:
                self._messages[current_chat_id] = retained
            else:
                self._messages.pop(current_chat_id, None)


class StateStore:
    """SQLite store for restart-safe timestamps, topics and command cooldowns only."""

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(os.path.expanduser(path))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=15)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout = 15000")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = NORMAL")
        self._create_schema()

    def _create_schema(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_state (
                    chat_id INTEGER PRIMARY KEY,
                    last_activity REAL,
                    last_topic_at REAL,
                    last_reply_at REAL,
                    weekly_anchor REAL
                );
                CREATE TABLE IF NOT EXISTS chat_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    is_weekly INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_topics_chat_time
                    ON chat_topics(chat_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS command_cooldowns (
                    chat_id INTEGER NOT NULL,
                    command TEXT NOT NULL,
                    last_used REAL NOT NULL,
                    PRIMARY KEY (chat_id, command)
                );
                """
            )

    def record_activity(self, chat_id: int, *, at: float | None = None) -> None:
        timestamp = time.time() if at is None else at
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO chat_state(chat_id, last_activity, weekly_anchor)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    last_activity = excluded.last_activity,
                    weekly_anchor = COALESCE(chat_state.weekly_anchor, excluded.weekly_anchor)
                """,
                (chat_id, timestamp, timestamp),
            )

    def record_reply(self, chat_id: int, *, at: float | None = None) -> None:
        timestamp = time.time() if at is None else at
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO chat_state(chat_id, last_reply_at)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET last_reply_at = excluded.last_reply_at
                """,
                (chat_id, timestamp),
            )

    def record_topic(self, chat_id: int, topic: str, *, at: float | None = None, weekly: bool = False) -> None:
        timestamp = time.time() if at is None else at
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO chat_state(chat_id, last_topic_at, weekly_anchor)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    last_topic_at = excluded.last_topic_at,
                    weekly_anchor = CASE WHEN ? THEN excluded.weekly_anchor
                                         ELSE COALESCE(chat_state.weekly_anchor, excluded.weekly_anchor) END
                """,
                (chat_id, timestamp, timestamp, int(weekly)),
            )
            self.connection.execute(
                "INSERT INTO chat_topics(chat_id, topic, created_at, is_weekly) VALUES (?, ?, ?, ?)",
                (chat_id, topic[:1000], timestamp, int(weekly)),
            )
            self.connection.execute(
                """
                DELETE FROM chat_topics
                WHERE chat_id = ? AND id NOT IN (
                    SELECT id FROM chat_topics WHERE chat_id = ? ORDER BY created_at DESC, id DESC LIMIT 12
                )
                """,
                (chat_id, chat_id),
            )

    def recent_topics(self, chat_id: int, *, limit: int = 8) -> list[str]:
        rows = self.connection.execute(
            "SELECT topic FROM chat_topics WHERE chat_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (chat_id, max(1, min(limit, 12))),
        ).fetchall()
        return [row["topic"] for row in reversed(rows)]

    def weekly_due(self, chat_id: int, *, now: float, interval_seconds: int) -> bool:
        row = self.connection.execute(
            "SELECT weekly_anchor FROM chat_state WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        if row is None or row["weekly_anchor"] is None:
            self.record_activity(chat_id, at=now)
            return False
        return now - float(row["weekly_anchor"]) >= interval_seconds

    def load_chat_states(self) -> dict[int, dict[str, float | None]]:
        rows = self.connection.execute(
            "SELECT chat_id, last_activity, last_topic_at, last_reply_at, weekly_anchor FROM chat_state"
        ).fetchall()
        return {
            int(row["chat_id"]): {
                key: (float(row[key]) if row[key] is not None else None)
                for key in ("last_activity", "last_topic_at", "last_reply_at", "weekly_anchor")
            }
            for row in rows
        }

    def claim_command(self, chat_id: int, command: str, *, now: float, cooldown_seconds: int) -> tuple[bool, int]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                "SELECT last_used FROM command_cooldowns WHERE chat_id = ? AND command = ?",
                (chat_id, command),
            ).fetchone()
            if row is not None:
                remaining = int(cooldown_seconds - (now - float(row["last_used"])))
                if remaining > 0:
                    self.connection.rollback()
                    return False, remaining
            self.connection.execute(
                """
                INSERT INTO command_cooldowns(chat_id, command, last_used) VALUES (?, ?, ?)
                ON CONFLICT(chat_id, command) DO UPDATE SET last_used = excluded.last_used
                """,
                (chat_id, command, now),
            )
            self.connection.commit()
            return True, 0
        except Exception:
            self.connection.rollback()
            raise

    def close(self) -> None:
        self.connection.close()
