#!/usr/bin/env python3
"""
Knowledge Extraction Pipeline

Processes messages from kimi_memory.db and extracts knowledge triples
to populate the knowledge_graph table.

Run after sync_sessions.py:
  python3 ~/projects/dream-weaver-engine/scripts/extract_knowledge.py
"""

import os
import sys
import json
import sqlite3
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from together import Together

MEMORY_DB = PROJECT_ROOT / "memory" / "kimi_memory.db"
MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

# Extraction prompt for knowledge triples
EXTRACTION_PROMPT = """You are a knowledge extraction engine. Extract factual relationships from the conversation.

For each meaningful fact, preference, or relationship, output a JSON object with:
- subject: the entity or topic
- predicate: the relationship type (e.g., "prefers", "works_on", "is_a", "has", "wants", "created", "uses")
- object: the related entity or value
- confidence: 0.0-1.0 based on how explicit the information is

Focus on:
1. User preferences and habits
2. Project relationships and dependencies
3. Technical facts and decisions
4. Named entities (people, tools, projects)
5. Goals and intentions

Output ONLY a JSON array of triples. No explanation.

Example output:
[
  {{"subject": "user", "predicate": "works_on", "object": "BWB app", "confidence": 0.9}},
  {{"subject": "BWB", "predicate": "uses", "object": "SwiftUI", "confidence": 0.85}}
]

If no extractable knowledge, output: []

Conversation:
{conversation}
"""


def get_unprocessed_messages(conn: sqlite3.Connection, limit: int = 50) -> List[Dict]:
    """Get messages that haven't been processed for knowledge extraction."""
    # Check if we have a processed marker column
    try:
        conn.execute("SELECT knowledge_extracted FROM messages LIMIT 1")
    except sqlite3.OperationalError:
        # Add the column if it doesn't exist
        conn.execute("ALTER TABLE messages ADD COLUMN knowledge_extracted INTEGER DEFAULT 0")
        conn.commit()
    
    rows = conn.execute("""
        SELECT id, timestamp, role, content, channel 
        FROM messages 
        WHERE knowledge_extracted = 0 OR knowledge_extracted IS NULL
        ORDER BY timestamp ASC
        LIMIT ?
    """, (limit,)).fetchall()
    
    return [
        {"id": r[0], "timestamp": r[1], "role": r[2], "content": r[3], "channel": r[4]}
        for r in rows
    ]


def format_conversation(messages: List[Dict]) -> str:
    """Format messages into a conversation string."""
    lines = []
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"][:1000]  # Truncate long messages
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


async def extract_knowledge(client: Together, conversation: str) -> List[Dict]:
    """Use Kimi to extract knowledge triples from conversation."""
    import re
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": EXTRACTION_PROMPT.format(conversation=conversation)}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        
        # Handle thinking model output (may have <think> tags)
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        
        # Clean up common JSON issues
        content = content.replace("'", '"')  # Single to double quotes
        content = re.sub(r',\s*]', ']', content)  # Remove trailing commas
        content = re.sub(r',\s*}', '}', content)  # Remove trailing commas
        
        # Extract JSON array
        match = re.search(r'\[[\s\S]*\]', content)
        if match:
            json_str = match.group()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"  JSON parse error: {e}")
                print(f"  Raw: {json_str[:200]}...")
                return []
        
        print(f"  No JSON array found in response")
        return []
    except Exception as e:
        import traceback
        print(f"Extraction error: {e}")
        traceback.print_exc()
        return []


def store_knowledge(conn: sqlite3.Connection, triples: List[Dict], source: str):
    """Store extracted knowledge triples in the database."""
    for triple in triples:
        try:
            subject = triple.get("subject", "").strip()
            predicate = triple.get("predicate", "").strip()
            obj = triple.get("object", "").strip()
            confidence = float(triple.get("confidence", 0.5))
            
            if not subject or not predicate or not obj:
                continue
            
            # Insert or update confidence if already exists
            conn.execute("""
                INSERT INTO knowledge_graph (subject, predicate, object, confidence, source)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(subject, predicate, object) DO UPDATE SET
                    confidence = MAX(knowledge_graph.confidence, excluded.confidence)
            """, (subject, predicate, obj, confidence, source))
        except Exception as e:
            print(f"Store error: {e}")
    
    conn.commit()


def mark_processed(conn: sqlite3.Connection, message_ids: List[int]):
    """Mark messages as processed."""
    conn.executemany(
        "UPDATE messages SET knowledge_extracted = 1 WHERE id = ?",
        [(mid,) for mid in message_ids]
    )
    conn.commit()


async def main():
    print(f"Knowledge Extraction Pipeline")
    print(f"Database: {MEMORY_DB}")
    
    if not MEMORY_DB.exists():
        print("Database not found!")
        return
    
    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        # Try loading from .env
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("TOGETHER_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
                    break
    
    if not api_key:
        print("TOGETHER_API_KEY not found!")
        return
    
    client = Together(api_key=api_key)
    conn = sqlite3.connect(MEMORY_DB)
    
    # Get unprocessed messages
    messages = get_unprocessed_messages(conn, limit=50)
    print(f"Found {len(messages)} unprocessed messages")
    
    if not messages:
        print("Nothing to process")
        return
    
    # Process in batches of 5 messages (to keep context manageable)
    batch_size = 5
    total_triples = 0
    
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i+batch_size]
        conversation = format_conversation(batch)
        
        print(f"Processing batch {i//batch_size + 1}...")
        triples = await extract_knowledge(client, conversation)
        
        if triples:
            print(f"  Extracted {len(triples)} triples")
            store_knowledge(conn, triples, "synthesis")
            total_triples += len(triples)
        
        # Mark as processed
        mark_processed(conn, [m["id"] for m in batch])
    
    conn.close()
    
    # Show results
    conn = sqlite3.connect(MEMORY_DB)
    kg_count = conn.execute("SELECT COUNT(*) FROM knowledge_graph").fetchone()[0]
    conn.close()
    
    print(f"\nExtracted {total_triples} new triples")
    print(f"Total knowledge_graph entries: {kg_count}")


if __name__ == "__main__":
    asyncio.run(main())
