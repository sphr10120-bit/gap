from __future__ import annotations

import os
import re
import sqlite3
import time
import unicodedata
from pathlib import Path
from typing import Any


def normalize_quiz_question(question: str) -> str:
    text = unicodedata.normalize("NFKC", (question or "").strip()).casefold()
    text = text.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه"}))
    return re.sub(r"[^\w]+", "", text, flags=re.UNICODE)


class ConversationMemory:
    """Bounded in-process cache; persistent copies are managed separately by StateStore."""

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
        user_id: int | None = None,
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
            "user_id": user_id,
            "text": cleaned,
            "created_at": timestamp,
        })
        user_messages = [item for item in messages if item.get("user_id") == user_id]
        if len(user_messages) > self.max_messages:
            expired_ids = {item["message_id"] for item in user_messages[:-self.max_messages]}
            messages = [item for item in messages if item["message_id"] not in expired_ids]
        self._messages[chat_id] = messages

    def delete_user(self, chat_id: int, user_id: int) -> None:
        retained = [
            item for item in self._messages.get(chat_id, [])
            if item.get("user_id") != user_id
        ]
        if retained:
            self._messages[chat_id] = retained
        else:
            self._messages.pop(chat_id, None)

    def recent(
        self,
        chat_id: int,
        *,
        now: float | None = None,
        exclude_message_id: int | None = None,
        limit: int | None = None,
        user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        timestamp = time.time() if now is None else now
        self.purge_expired(now=timestamp, chat_id=chat_id)
        count = self.max_messages if limit is None else max(1, min(limit, self.max_messages))
        messages = [
            item for item in self._messages.get(chat_id, [])
            if exclude_message_id is None or item["message_id"] != exclude_message_id
            if user_id is None or item.get("user_id") == user_id
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
    """SQLite store for restart-safe scheduling and bounded, expiring group/user memory."""

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
                CREATE TABLE IF NOT EXISTS weekly_interaction_schedule (
                    chat_id INTEGER NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('poll', 'quiz')),
                    next_due_at REAL NOT NULL,
                    PRIMARY KEY (chat_id, kind)
                );
                CREATE TABLE IF NOT EXISTS quiz_question_history (
                    chat_id INTEGER NOT NULL,
                    question_key TEXT NOT NULL,
                    question TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (chat_id, question_key)
                );
                CREATE INDEX IF NOT EXISTS idx_quiz_history_chat_time
                    ON quiz_question_history(chat_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    author TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (chat_id, message_id)
                );
                CREATE INDEX IF NOT EXISTS idx_conversation_chat_time
                    ON conversation_messages(chat_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_conversation_user
                    ON conversation_messages(chat_id, user_id);
                CREATE TABLE IF NOT EXISTS user_profile_memories (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    preference TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (chat_id, user_id, preference)
                );
                CREATE INDEX IF NOT EXISTS idx_user_profile_time
                    ON user_profile_memories(chat_id, user_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                );
                """
            )

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.connection.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key = ?",
            (key,),
        ).fetchone()
        return str(row["setting_value"]) if row is not None else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO app_settings(setting_key, setting_value) VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
                """,
                (str(key), str(value)),
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

    def record_quiz_question(
        self,
        chat_id: int,
        question: str,
        *,
        at: float | None = None,
        max_items: int = 100,
    ) -> None:
        cleaned = (question or "").strip()[:300]
        question_key = normalize_quiz_question(cleaned)
        if not question_key:
            return
        timestamp = time.time() if at is None else at
        keep = max(1, int(max_items))
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO quiz_question_history(chat_id, question_key, question, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, question_key) DO UPDATE SET
                    question = excluded.question,
                    created_at = excluded.created_at
                """,
                (chat_id, question_key, cleaned, timestamp),
            )
            self.connection.execute(
                """
                DELETE FROM quiz_question_history
                WHERE chat_id = ? AND question_key NOT IN (
                    SELECT question_key FROM quiz_question_history
                    WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?
                )
                """,
                (chat_id, chat_id, keep),
            )

    def recent_quiz_questions(self, chat_id: int, *, limit: int = 30) -> list[str]:
        rows = self.connection.execute(
            """
            SELECT question FROM quiz_question_history
            WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?
            """,
            (chat_id, max(1, min(limit, 100))),
        ).fetchall()
        return [str(row["question"]) for row in reversed(rows)]

    def record_conversation_message(
        self,
        chat_id: int,
        message_id: int,
        role: str,
        text: str,
        *,
        user_id: int | None = None,
        author: str = "",
        at: float | None = None,
        ttl_seconds: int = 30 * 24 * 60 * 60,
        max_messages: int = 12,
    ) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        cleaned = (text or "").strip()[:1200]
        if not cleaned:
            return
        timestamp = time.time() if at is None else at
        cutoff = timestamp - max(60, int(ttl_seconds))
        keep = max(1, int(max_messages))
        with self.connection:
            self.connection.execute(
                "DELETE FROM conversation_messages WHERE chat_id = ? AND created_at < ?",
                (chat_id, cutoff),
            )
            self.connection.execute(
                """
                INSERT OR REPLACE INTO conversation_messages
                    (chat_id, message_id, user_id, role, author, text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (chat_id, message_id, user_id, role, (author or "")[:80], cleaned, timestamp),
            )
            self.connection.execute(
                """
                DELETE FROM conversation_messages
                WHERE chat_id = ? AND user_id IS ? AND message_id NOT IN (
                    SELECT message_id FROM conversation_messages
                    WHERE chat_id = ? AND user_id IS ?
                    ORDER BY created_at DESC, message_id DESC LIMIT ?
                )
                """,
                (chat_id, user_id, chat_id, user_id, keep),
            )

    def recent_conversation_messages(
        self,
        chat_id: int,
        *,
        now: float,
        ttl_seconds: int = 30 * 24 * 60 * 60,
        exclude_message_id: int | None = None,
        limit: int = 12,
        user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        cutoff = now - max(60, int(ttl_seconds))
        with self.connection:
            self.connection.execute(
                "DELETE FROM conversation_messages WHERE chat_id = ? AND created_at < ?",
                (chat_id, cutoff),
            )
        rows = self.connection.execute(
            """
            SELECT chat_id, message_id, user_id, role, author, text, created_at
            FROM conversation_messages
            WHERE chat_id = ? AND created_at >= ?
              AND (? IS NULL OR message_id != ?)
              AND (? IS NULL OR user_id = ?)
            ORDER BY created_at DESC, message_id DESC LIMIT ?
            """,
            (
                chat_id,
                cutoff,
                exclude_message_id,
                exclude_message_id,
                user_id,
                user_id,
                max(1, min(limit, 12)),
            ),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def record_user_preference(
        self,
        chat_id: int,
        user_id: int,
        preference: str,
        *,
        at: float | None = None,
        ttl_seconds: int = 30 * 24 * 60 * 60,
        max_items: int = 5,
    ) -> None:
        cleaned = (preference or "").strip()[:500]
        if not cleaned:
            return
        timestamp = time.time() if at is None else at
        cutoff = timestamp - max(60, int(ttl_seconds))
        keep = max(1, int(max_items))
        with self.connection:
            self.connection.execute(
                "DELETE FROM user_profile_memories WHERE chat_id = ? AND user_id = ? AND updated_at < ?",
                (chat_id, user_id, cutoff),
            )
            self.connection.execute(
                """
                INSERT INTO user_profile_memories(chat_id, user_id, preference, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, user_id, preference) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (chat_id, user_id, cleaned, timestamp),
            )
            self.connection.execute(
                """
                DELETE FROM user_profile_memories
                WHERE chat_id = ? AND user_id = ? AND preference NOT IN (
                    SELECT preference FROM user_profile_memories
                    WHERE chat_id = ? AND user_id = ?
                    ORDER BY updated_at DESC, preference DESC LIMIT ?
                )
                """,
                (chat_id, user_id, chat_id, user_id, keep),
            )

    def user_preferences(
        self,
        chat_id: int,
        user_id: int,
        *,
        now: float,
        ttl_seconds: int = 30 * 24 * 60 * 60,
        limit: int = 5,
    ) -> list[str]:
        cutoff = now - max(60, int(ttl_seconds))
        with self.connection:
            self.connection.execute(
                "DELETE FROM user_profile_memories WHERE chat_id = ? AND user_id = ? AND updated_at < ?",
                (chat_id, user_id, cutoff),
            )
        rows = self.connection.execute(
            """
            SELECT preference FROM user_profile_memories
            WHERE chat_id = ? AND user_id = ? AND updated_at >= ?
            ORDER BY updated_at ASC, preference ASC LIMIT ?
            """,
            (chat_id, user_id, cutoff, max(1, min(limit, 5))),
        ).fetchall()
        return [str(row["preference"]) for row in rows]

    def forget_user(self, chat_id: int, user_id: int) -> tuple[int, int]:
        with self.connection:
            messages = self.connection.execute(
                "DELETE FROM conversation_messages WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            ).rowcount
            preferences = self.connection.execute(
                "DELETE FROM user_profile_memories WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            ).rowcount
        return messages, preferences

    def purge_expired_user_data(
        self,
        *,
        now: float,
        conversation_ttl_seconds: int = 30 * 24 * 60 * 60,
        preference_ttl_seconds: int = 30 * 24 * 60 * 60,
    ) -> tuple[int, int]:
        conversation_cutoff = now - max(60, int(conversation_ttl_seconds))
        preference_cutoff = now - max(60, int(preference_ttl_seconds))
        with self.connection:
            messages = self.connection.execute(
                "DELETE FROM conversation_messages WHERE created_at < ?",
                (conversation_cutoff,),
            ).rowcount
            preferences = self.connection.execute(
                "DELETE FROM user_profile_memories WHERE updated_at < ?",
                (preference_cutoff,),
            ).rowcount
        return messages, preferences

    def weekly_due(self, chat_id: int, *, now: float, interval_seconds: int) -> bool:
        row = self.connection.execute(
            "SELECT weekly_anchor FROM chat_state WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        if row is None or row["weekly_anchor"] is None:
            self.record_activity(chat_id, at=now)
            return False
        return now - float(row["weekly_anchor"]) >= interval_seconds

    def ensure_weekly_interaction_schedule(
        self,
        chat_id: int,
        *,
        now: float,
        first_poll_delay_seconds: int,
        spacing_seconds: int,
    ) -> None:
        poll_due = now + max(0, first_poll_delay_seconds)
        quiz_due = poll_due + max(0, spacing_seconds)
        with self.connection:
            self.connection.executemany(
                "INSERT OR IGNORE INTO weekly_interaction_schedule(chat_id, kind, next_due_at) VALUES (?, ?, ?)",
                ((chat_id, "poll", poll_due), (chat_id, "quiz", quiz_due)),
            )

    def due_weekly_interactions(self, chat_id: int, *, now: float) -> list[tuple[str, float]]:
        rows = self.connection.execute(
            """
            SELECT kind, next_due_at FROM weekly_interaction_schedule
            WHERE chat_id = ? AND next_due_at <= ?
            ORDER BY next_due_at ASC, kind ASC
            """,
            (chat_id, now),
        ).fetchall()
        return [(str(row["kind"]), float(row["next_due_at"])) for row in rows]

    def set_weekly_interaction_due(
        self,
        chat_id: int,
        kind: str,
        *,
        next_due_at: float,
    ) -> None:
        if kind not in {"poll", "quiz"}:
            raise ValueError("kind must be 'poll' or 'quiz'")
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO weekly_interaction_schedule(chat_id, kind, next_due_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, kind) DO UPDATE SET next_due_at = excluded.next_due_at
                """,
                (chat_id, kind, next_due_at),
            )

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
