"""Persistent memory store for Kimi-K2 synthesizer.

Stores:
- All incoming messages
- All synthesis results  
- Extracted insights
- Evolving context

Uses SQLite for portability + JSON for complex data.
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).parent / "kimi_memory.db"


def get_connection() -> sqlite3.Connection:
    """Get database connection, creating tables if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Create tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            channel TEXT,
            role TEXT NOT NULL,  -- user, assistant, system
            content TEXT NOT NULL,
            metadata JSON,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS synthesis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER REFERENCES messages(id),
            timestamp TEXT NOT NULL,
            enriched_prompt TEXT,
            intent TEXT,
            confidence REAL,
            dream_seeds JSON,
            skill_chain JSON,
            project_refs JSON,
            route TEXT,
            route_reason TEXT,
            raw_result JSON,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS context_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value JSON NOT NULL,
            category TEXT,  -- preference, fact, pattern, insight
            confidence REAL DEFAULT 0.5,
            last_updated TEXT,
            access_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS knowledge_graph (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            source TEXT,  -- synthesis, dream, manual
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(subject, predicate, object)
        );
        
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
        CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel);
        CREATE INDEX IF NOT EXISTS idx_synthesis_intent ON synthesis_results(intent);
        CREATE INDEX IF NOT EXISTS idx_context_category ON context_memory(category);
        CREATE INDEX IF NOT EXISTS idx_knowledge_subject ON knowledge_graph(subject);
    """)
    
    conn.commit()
    return conn


class MemoryStore:
    """Persistent memory store for Kimi-K2."""
    
    def __init__(self, db_path: Optional[Path] = None):
        global DB_PATH
        if db_path:
            DB_PATH = db_path
        self.conn = get_connection()
    
    # Message storage
    def save_message(
        self,
        content: str,
        role: str = "user",
        channel: str = None,
        metadata: Dict = None
    ) -> int:
        """Save an incoming or outgoing message."""
        cursor = self.conn.execute(
            """INSERT INTO messages (timestamp, channel, role, content, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(),
                channel,
                role,
                content,
                json.dumps(metadata) if metadata else None
            )
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_recent_messages(
        self,
        limit: int = 50,
        channel: str = None,
        role: str = None
    ) -> List[Dict]:
        """Get recent messages for context."""
        query = "SELECT * FROM messages WHERE 1=1"
        params = []
        
        if channel:
            query += " AND channel = ?"
            params.append(channel)
        if role:
            query += " AND role = ?"
            params.append(role)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in reversed(rows)]
    
    # Synthesis results
    def save_synthesis(
        self,
        message_id: int,
        result: Dict
    ) -> int:
        """Save a synthesis result."""
        cursor = self.conn.execute(
            """INSERT INTO synthesis_results 
               (message_id, timestamp, enriched_prompt, intent, confidence,
                dream_seeds, skill_chain, project_refs, route, route_reason, raw_result)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message_id,
                datetime.utcnow().isoformat(),
                result.get("enriched_prompt"),
                result.get("intent"),
                result.get("confidence"),
                json.dumps(result.get("dream_seeds", [])),
                json.dumps(result.get("skill_chain")),
                json.dumps(result.get("project_refs", [])),
                result.get("route"),
                result.get("route_reason"),
                json.dumps(result)
            )
        )
        self.conn.commit()
        return cursor.lastrowid
    
    # Context memory
    def remember(
        self,
        key: str,
        value: Any,
        category: str = "fact",
        confidence: float = 0.5
    ):
        """Store a piece of context memory."""
        self.conn.execute(
            """INSERT INTO context_memory (key, value, category, confidence, last_updated)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                 value = excluded.value,
                 confidence = excluded.confidence,
                 last_updated = excluded.last_updated,
                 access_count = access_count + 1""",
            (
                key,
                json.dumps(value),
                category,
                confidence,
                datetime.utcnow().isoformat()
            )
        )
        self.conn.commit()
    
    def recall(self, key: str) -> Optional[Any]:
        """Retrieve a piece of context memory."""
        row = self.conn.execute(
            "SELECT value FROM context_memory WHERE key = ?",
            (key,)
        ).fetchone()
        
        if row:
            # Update access count
            self.conn.execute(
                "UPDATE context_memory SET access_count = access_count + 1 WHERE key = ?",
                (key,)
            )
            self.conn.commit()
            return json.loads(row["value"])
        return None
    
    def get_context_by_category(self, category: str, limit: int = 20) -> List[Dict]:
        """Get context memories by category."""
        rows = self.conn.execute(
            """SELECT key, value, confidence, access_count 
               FROM context_memory 
               WHERE category = ?
               ORDER BY access_count DESC, confidence DESC
               LIMIT ?""",
            (category, limit)
        ).fetchall()
        return [
            {"key": r["key"], "value": json.loads(r["value"]), 
             "confidence": r["confidence"], "access_count": r["access_count"]}
            for r in rows
        ]
    
    # Knowledge graph
    def add_knowledge(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 0.5,
        source: str = "synthesis"
    ):
        """Add a knowledge triple."""
        try:
            self.conn.execute(
                """INSERT INTO knowledge_graph (subject, predicate, object, confidence, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (subject, predicate, obj, confidence, source)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Already exists, update confidence
            self.conn.execute(
                """UPDATE knowledge_graph 
                   SET confidence = MAX(confidence, ?)
                   WHERE subject = ? AND predicate = ? AND object = ?""",
                (confidence, subject, predicate, obj)
            )
            self.conn.commit()
    
    def query_knowledge(self, subject: str = None, predicate: str = None) -> List[Dict]:
        """Query knowledge graph."""
        query = "SELECT * FROM knowledge_graph WHERE 1=1"
        params = []
        
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if predicate:
            query += " AND predicate = ?"
            params.append(predicate)
        
        query += " ORDER BY confidence DESC LIMIT 50"
        
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    
    # Stats
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "total_messages": self.conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0],
            "total_syntheses": self.conn.execute(
                "SELECT COUNT(*) FROM synthesis_results"
            ).fetchone()[0],
            "context_memories": self.conn.execute(
                "SELECT COUNT(*) FROM context_memory"
            ).fetchone()[0],
            "knowledge_triples": self.conn.execute(
                "SELECT COUNT(*) FROM knowledge_graph"
            ).fetchone()[0],
            "intents": dict(self.conn.execute(
                "SELECT intent, COUNT(*) FROM synthesis_results GROUP BY intent"
            ).fetchall()),
        }
    
    def build_context_summary(self, max_tokens: int = 2000) -> str:
        """Build a context summary for Kimi-K2."""
        summary_parts = []
        
        # Recent messages
        recent = self.get_recent_messages(limit=10)
        if recent:
            summary_parts.append("## Recent Conversation")
            for msg in recent[-5:]:
                summary_parts.append(f"[{msg['role']}] {msg['content'][:200]}...")
        
        # Key preferences
        prefs = self.get_context_by_category("preference", limit=10)
        if prefs:
            summary_parts.append("\n## Known Preferences")
            for p in prefs:
                summary_parts.append(f"- {p['key']}: {p['value']}")
        
        # Key facts
        facts = self.get_context_by_category("fact", limit=10)
        if facts:
            summary_parts.append("\n## Known Facts")
            for f in facts:
                summary_parts.append(f"- {f['key']}: {f['value']}")
        
        # Patterns
        patterns = self.get_context_by_category("pattern", limit=5)
        if patterns:
            summary_parts.append("\n## Observed Patterns")
            for p in patterns:
                summary_parts.append(f"- {p['key']}: {p['value']}")
        
        return "\n".join(summary_parts)


# Singleton
_store = None

def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
