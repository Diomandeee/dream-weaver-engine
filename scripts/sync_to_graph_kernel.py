#!/usr/bin/env python3
"""
Sync knowledge triples from local SQLite → Graph Kernel (Supabase).
Only syncs NEW triples since last successful sync using rowid tracking.
"""

import sys
import json
import sqlite3
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MEMORY_DB = PROJECT_ROOT / "memory" / "kimi_memory.db"
STATE_FILE = PROJECT_ROOT / "memory" / "gk_sync_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_synced_rowid": 0, "total_synced": 0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


async def sync():
    from memory.graph_kernel_client import get_graph_kernel_client, KnowledgeTriple

    state = load_state()
    last_rowid = state.get("last_synced_rowid", 0)

    # Get only new triples
    conn = sqlite3.connect(MEMORY_DB)
    triples = conn.execute(
        "SELECT rowid, subject, predicate, object, confidence FROM knowledge_graph WHERE rowid > ? ORDER BY rowid",
        (last_rowid,)
    ).fetchall()
    conn.close()

    if not triples:
        print(f"  No new triples (last sync: rowid {last_rowid})")
        return

    print(f"  {len(triples)} new triples to sync (after rowid {last_rowid})")

    client = get_graph_kernel_client()
    if not await client.health_check():
        print("  Graph Kernel not available, skipping")
        return

    print("  Graph Kernel online ✓")

    # Sync in chunks
    chunk_size = 50
    synced = 0
    max_rowid = last_rowid

    for i in range(0, len(triples), chunk_size):
        chunk = triples[i:i + chunk_size]
        kt_list = [
            KnowledgeTriple(
                subject=t[1], predicate=t[2], object=t[3],
                confidence=t[4], source="kimi-pipeline"
            )
            for t in chunk
        ]

        try:
            resp = await client.client.post(
                f"{client.base_url}/api/knowledge/batch",
                json=[
                    {"subject": t.subject, "predicate": t.predicate,
                     "object": t.object, "confidence": t.confidence,
                     "source": t.source}
                    for t in kt_list
                ],
                timeout=60.0
            )
            if resp.status_code == 200:
                data = resp.json()
                batch_count = data.get("added", 0) + data.get("updated", 0)
                synced += batch_count
                max_rowid = max(max_rowid, chunk[-1][0])
                print(f"    Batch {i // chunk_size + 1}: +{data.get('added', 0)} new, {data.get('updated', 0)} updated")
            else:
                print(f"    Batch {i // chunk_size + 1}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"    Batch {i // chunk_size + 1}: ERROR {e}")
            break  # Stop on error, save progress

    # Save progress
    state["last_synced_rowid"] = max_rowid
    state["total_synced"] = state.get("total_synced", 0) + synced
    save_state(state)

    print(f"  Synced {synced} triples → Supabase (rowid up to {max_rowid})")


def main():
    asyncio.run(sync())


if __name__ == "__main__":
    main()
