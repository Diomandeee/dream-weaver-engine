#!/usr/bin/env python3
"""
Local Knowledge Extraction (No API required)

Uses pattern matching to extract basic knowledge triples from messages.
For deeper extraction, use extract_knowledge.py with Kimi API.

Run: python3 ~/projects/dream-weaver-engine/scripts/extract_knowledge_local.py
"""

import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

MEMORY_DB = Path.home() / "projects" / "dream-weaver-engine" / "memory" / "kimi_memory.db"

# Pattern-based extractors
PATTERNS = [
    # Project references
    (r'\b(BWB|Comp-Core|Milkmen|Serenity|MFP)\b', 'project', 'mentioned'),
    (r'working on\s+([A-Za-z0-9_-]+)', 'user', 'works_on'),
    (r'building\s+([A-Za-z0-9_-]+)', 'user', 'building'),
    
    # Tech stack
    (r'\b(Swift|SwiftUI|Python|TypeScript|React|Expo|Next\.js|Prisma)\b', None, 'uses_tech'),
    (r'\b(SQLite|PostgreSQL|LanceDB|Redis)\b', None, 'uses_database'),
    
    # Tools/services
    (r'\b(Clawdbot|Claude|Kimi|Together|OpenAI|Anthropic)\b', None, 'uses_service'),
    (r'\b(Discord|Telegram|WhatsApp|iMessage)\b', None, 'uses_channel'),
    
    # Actions/intentions
    (r'want(?:s)? to\s+(\w+(?:\s+\w+){0,3})', 'user', 'wants_to'),
    (r'need(?:s)? to\s+(\w+(?:\s+\w+){0,3})', 'user', 'needs_to'),
    (r'should\s+(\w+(?:\s+\w+){0,3})', 'context', 'should'),
    
    # Preferences
    (r'prefer(?:s)?\s+(\w+(?:\s+\w+){0,2})', 'user', 'prefers'),
    (r'like(?:s)?\s+(\w+(?:\s+\w+){0,2})', 'user', 'likes'),
    
    # File/path references
    (r'~/([A-Za-z0-9_/.-]+)', 'filesystem', 'has_path'),
    (r'(\w+\.(?:py|ts|js|swift|md|json))\b', 'codebase', 'has_file'),
]

# Entity normalization
ENTITY_ALIASES = {
    'bwb': 'BWB',
    'comp-core': 'Comp-Core',
    'milkmen': 'Milkmen Delivery',
    'serenity': 'Serenity Soother',
    'mfp': 'Meaningful Power',
}


def normalize_entity(entity: str) -> str:
    """Normalize entity names."""
    lower = entity.lower().strip()
    return ENTITY_ALIASES.get(lower, entity.strip())


def extract_from_text(text: str) -> List[Dict]:
    """Extract knowledge triples from text using patterns."""
    triples = []
    text_lower = text.lower()
    
    for pattern, subject, predicate in PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            obj = normalize_entity(match.group(1) if match.groups() else match.group())
            
            # Determine subject
            if subject is None:
                # Infer subject from context
                subj = 'system' if predicate.startswith('uses_') else 'context'
            else:
                subj = subject
            
            # Skip very short or common words
            if len(obj) < 2 or obj.lower() in ('the', 'a', 'an', 'to', 'of'):
                continue
            
            triples.append({
                'subject': subj,
                'predicate': predicate,
                'object': obj,
                'confidence': 0.6
            })
    
    return triples


def deduplicate_triples(triples: List[Dict]) -> List[Dict]:
    """Remove duplicate triples, keeping highest confidence."""
    seen = {}
    for t in triples:
        key = (t['subject'], t['predicate'], t['object'])
        if key not in seen or t['confidence'] > seen[key]['confidence']:
            seen[key] = t
    return list(seen.values())


def main():
    print(f"Local Knowledge Extraction")
    print(f"Database: {MEMORY_DB}")
    
    if not MEMORY_DB.exists():
        print("Database not found!")
        return
    
    conn = sqlite3.connect(MEMORY_DB)
    
    # Get all messages
    messages = conn.execute("""
        SELECT id, content, role FROM messages
    """).fetchall()
    
    print(f"Processing {len(messages)} messages...")
    
    all_triples = []
    for msg_id, content, role in messages:
        if not content:
            continue
        triples = extract_from_text(content)
        all_triples.extend(triples)
    
    # Deduplicate
    unique_triples = deduplicate_triples(all_triples)
    print(f"Extracted {len(unique_triples)} unique triples")
    
    # Store in database
    inserted = 0
    for t in unique_triples:
        try:
            conn.execute("""
                INSERT INTO knowledge_graph (subject, predicate, object, confidence, source)
                VALUES (?, ?, ?, ?, 'pattern')
                ON CONFLICT(subject, predicate, object) DO UPDATE SET
                    confidence = MAX(knowledge_graph.confidence, excluded.confidence)
            """, (t['subject'], t['predicate'], t['object'], t['confidence']))
            inserted += 1
        except Exception as e:
            print(f"Error: {e}")
    
    conn.commit()
    
    # Show stats
    total = conn.execute("SELECT COUNT(*) FROM knowledge_graph").fetchone()[0]
    print(f"\nInserted/updated {inserted} triples")
    print(f"Total knowledge_graph entries: {total}")
    
    # Show sample
    print("\nSample knowledge:")
    for row in conn.execute("SELECT subject, predicate, object, confidence FROM knowledge_graph LIMIT 10").fetchall():
        print(f"  {row[0]} --[{row[1]}]--> {row[2]} ({row[3]:.2f})")
    
    conn.close()


if __name__ == "__main__":
    main()
