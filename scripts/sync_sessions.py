#!/usr/bin/env python3
"""
Sync Clawdbot session transcripts to kimi_memory.db

Run periodically via cron or manually:
  python3 ~/projects/dream-weaver-engine/scripts/sync_sessions.py
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, Dict, Any

# Paths
SESSIONS_DIR = Path.home() / ".clawdbot" / "agents" / "main" / "sessions"
MEMORY_DB = Path.home() / "projects" / "dream-weaver-engine" / "memory" / "kimi_memory.db"
LAST_SYNC_FILE = Path.home() / "projects" / "dream-weaver-engine" / "memory" / ".last_sync"


def get_last_sync_time() -> datetime:
    """Get the timestamp of the last sync."""
    if LAST_SYNC_FILE.exists():
        try:
            return datetime.fromisoformat(LAST_SYNC_FILE.read_text().strip())
        except:
            pass
    # Default: sync last 24 hours
    return datetime.now() - timedelta(hours=24)


def save_last_sync_time():
    """Save current time as last sync."""
    LAST_SYNC_FILE.write_text(datetime.now().isoformat())


def iter_session_messages(since: datetime) -> Generator[Dict[str, Any], None, None]:
    """Iterate over messages from session files modified since given time."""
    if not SESSIONS_DIR.exists():
        print(f"Sessions directory not found: {SESSIONS_DIR}")
        return
    
    for session_file in SESSIONS_DIR.glob("**/*.jsonl"):
        # Check if file was modified recently
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        if mtime < since:
            continue
        
        print(f"Processing: {session_file.name}")
        
        try:
            with open(session_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "message":
                            msg = entry.get("message", {})
                            role = msg.get("role")
                            if role in ("user", "assistant"):
                                content = msg.get("content", "")
                                if isinstance(content, list):
                                    # Extract text from content array
                                    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                                    content = "\n".join(text_parts)
                                
                                if content and not content.startswith("/"):
                                    yield {
                                        "timestamp": entry.get("ts", datetime.now().isoformat()),
                                        "role": role,
                                        "content": content,
                                        "channel": session_file.stem,
                                        "metadata": {
                                            "session_file": str(session_file.name),
                                            "entry_type": entry.get("type")
                                        }
                                    }
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error processing {session_file}: {e}")


def sync_to_database(messages: Generator) -> int:
    """Insert messages into kimi_memory.db."""
    if not MEMORY_DB.exists():
        print(f"Database not found: {MEMORY_DB}")
        return 0
    
    conn = sqlite3.connect(MEMORY_DB)
    inserted = 0
    
    for msg in messages:
        try:
            # Check if message already exists (by content hash)
            content_hash = hash(msg["content"][:200] + msg["timestamp"][:16])
            existing = conn.execute(
                "SELECT id FROM messages WHERE content = ? AND timestamp LIKE ?",
                (msg["content"], msg["timestamp"][:16] + "%")
            ).fetchone()
            
            if not existing:
                conn.execute(
                    "INSERT INTO messages (timestamp, channel, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
                    (
                        msg["timestamp"],
                        msg["channel"],
                        msg["role"],
                        msg["content"],
                        json.dumps(msg["metadata"])
                    )
                )
                inserted += 1
        except sqlite3.IntegrityError:
            pass  # Duplicate
        except Exception as e:
            print(f"Error inserting message: {e}")
    
    conn.commit()
    conn.close()
    return inserted


def main():
    print(f"Syncing sessions to {MEMORY_DB}")
    
    last_sync = get_last_sync_time()
    print(f"Last sync: {last_sync.isoformat()}")
    
    messages = iter_session_messages(last_sync)
    inserted = sync_to_database(messages)
    
    print(f"Inserted {inserted} new messages")
    
    save_last_sync_time()
    
    # Show current stats
    if MEMORY_DB.exists():
        conn = sqlite3.connect(MEMORY_DB)
        total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        conn.close()
        print(f"Total messages in DB: {total}")


if __name__ == "__main__":
    main()
