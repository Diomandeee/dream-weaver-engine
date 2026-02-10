#!/usr/bin/env python3
"""
Full Knowledge Pipeline
=======================
1. Sync Clawdbot sessions → kimi_memory.db messages
2. Extract knowledge triples → kimi_memory.db knowledge_graph
3. Sync knowledge_graph → Graph Kernel (when /api/knowledge available)

Run: python3 ~/projects/dream-weaver-engine/scripts/run_pipeline.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

def main():
    print("=" * 60)
    print("  Kimi Knowledge Pipeline")
    print("=" * 60)
    
    # Step 1: Sync sessions
    print("\n[1/3] Syncing Clawdbot sessions → messages...")
    from sync_sessions import main as sync_main
    sync_main()
    
    # Step 2: Extract knowledge locally
    print("\n[2/3] Extracting knowledge triples...")
    from extract_knowledge_local import main as extract_main
    extract_main()
    
    # Step 3: Try syncing to Graph Kernel
    print("\n[3/3] Syncing to Graph Kernel...")
    import sqlite3
    import asyncio
    
    MEMORY_DB = PROJECT_ROOT / "memory" / "kimi_memory.db"
    conn = sqlite3.connect(MEMORY_DB)
    
    triples = conn.execute("""
        SELECT subject, predicate, object, confidence 
        FROM knowledge_graph
    """).fetchall()
    conn.close()
    
    if not triples:
        print("  No triples to sync")
        return
    
    async def try_graph_kernel_sync():
        try:
            from memory.graph_kernel_client import get_graph_kernel_client, KnowledgeTriple
            client = get_graph_kernel_client()
            
            healthy = await client.health_check()
            if not healthy:
                print("  Graph Kernel not available")
                return 0
            
            print(f"  Graph Kernel is online ✓")
            
            kt_list = [
                KnowledgeTriple(
                    subject=t[0], predicate=t[1], object=t[2], 
                    confidence=t[3], source="kimi-pipeline"
                )
                for t in triples
            ]
            
            synced = await client.add_knowledge_batch(kt_list)
            print(f"  Synced {synced} triples to Graph Kernel")
            return synced
        except Exception as e:
            print(f"  Graph Kernel sync failed: {e}")
            print(f"  (Graph Kernel may not have /api/knowledge endpoints yet)")
            return 0
    
    asyncio.run(try_graph_kernel_sync())
    
    print("\n" + "=" * 60)
    
    # Final stats
    conn = sqlite3.connect(MEMORY_DB)
    msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    kg_count = conn.execute("SELECT COUNT(*) FROM knowledge_graph").fetchone()[0]
    conn.close()
    
    print(f"  Messages:         {msg_count}")
    print(f"  Knowledge triples: {kg_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
