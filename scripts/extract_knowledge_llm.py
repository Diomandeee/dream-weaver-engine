#!/usr/bin/env python3
"""
LLM-powered knowledge extraction — focused pass.
Uses Kimi-K2 via Together API to extract high-quality semantic triples.
"""

import os, sys, json, sqlite3, re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MEMORY_DB = PROJECT_ROOT / "memory" / "kimi_memory.db"
MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

PROMPT = """Extract knowledge triples from this conversation. Focus on:
- WHO works on WHAT (projects, tools)
- WHAT uses WHAT (tech dependencies)  
- WHO wants/likes/prefers WHAT
- Project relationships and architecture decisions
- Named entities: people, services, apps, frameworks

Output ONLY a JSON array. Each triple: {{"subject":"...","predicate":"...","object":"...","confidence":0.0-1.0}}

Rules:
- subject/object must be proper nouns or clear entities (not pronouns or fragments)
- predicate must be a clean verb: uses, works_on, depends_on, built_with, prefers, wants, created, deploys_to, integrates_with, has_feature, etc.
- Skip vague or fragmentary relationships
- confidence: 0.9 for explicit facts, 0.7 for implied, 0.5 for uncertain

Conversation:
{text}"""


def main():
    from together import Together

    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("TOGETHER_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
    
    if not api_key:
        print("No TOGETHER_API_KEY"); return

    client = Together(api_key=api_key)
    conn = sqlite3.connect(MEMORY_DB)

    # Ensure column exists
    try:
        conn.execute("SELECT knowledge_extracted FROM messages LIMIT 1")
    except:
        conn.execute("ALTER TABLE messages ADD COLUMN knowledge_extracted INTEGER DEFAULT 0")
        conn.commit()

    # Get richest user messages (long content, not tool calls)
    rows = conn.execute("""
        SELECT id, timestamp, role, content, channel
        FROM messages 
        WHERE role = 'user' 
        AND length(content) > 80
        AND content NOT LIKE '%tool_call%'
        AND content NOT LIKE '%HEARTBEAT%'
        AND (knowledge_extracted = 0 OR knowledge_extracted IS NULL)
        ORDER BY timestamp DESC
        LIMIT 200
    """).fetchall()

    print(f"LLM Knowledge Extraction (Kimi-K2)")
    print(f"Processing {len(rows)} rich user messages")
    print(f"Model: {MODEL}\n")

    # Process in batches of 10
    batch_size = 10
    total_new = 0
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        text = "\n\n".join([f"[{r[1]}] {r[2]}: {r[3][:500]}" for r in batch])
        
        print(f"  Batch {i//batch_size + 1}/{(len(rows) + batch_size - 1)//batch_size}...", end=" ", flush=True)
        
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": PROMPT.format(text=text)}],
                max_tokens=2000,
                temperature=0.2
            )
            content = resp.choices[0].message.content.strip()
            
            # Strip thinking tags / markdown fences
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*$', '', content)
            
            # Extract JSON
            match = re.search(r'\[[\s\S]*\]', content)
            if match:
                triples = json.loads(match.group())
                added = 0
                for t in triples:
                    s, p, o = t.get("subject","").strip(), t.get("predicate","").strip(), t.get("object","").strip()
                    conf = float(t.get("confidence", 0.7))
                    if len(s) < 2 or len(p) < 2 or len(o) < 2: continue
                    try:
                        conn.execute("""
                            INSERT INTO knowledge_graph (subject, predicate, object, confidence, source)
                            VALUES (?, ?, ?, ?, 'kimi-k2-extraction')
                            ON CONFLICT(subject, predicate, object) DO UPDATE SET
                                confidence = MAX(knowledge_graph.confidence, excluded.confidence),
                                source = 'kimi-k2-extraction'
                        """, (s, p, o, conf))
                        added += 1
                    except: pass
                conn.commit()
                total_new += added
                print(f"+{added} triples")
            else:
                print("no JSON")
        except Exception as e:
            print(f"error: {e}")
        
        # Mark processed
        conn.executemany("UPDATE messages SET knowledge_extracted = 1 WHERE id = ?",
                         [(r[0],) for r in batch])
        conn.commit()

    # Stats
    kg_count = conn.execute("SELECT COUNT(*) FROM knowledge_graph").fetchone()[0]
    kg_llm = conn.execute("SELECT COUNT(*) FROM knowledge_graph WHERE source = 'kimi-k2-extraction'").fetchone()[0]
    conn.close()

    print(f"\n{'='*50}")
    print(f"  New triples from LLM: {total_new}")
    print(f"  LLM triples total:    {kg_llm}")
    print(f"  All triples:          {kg_count}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
