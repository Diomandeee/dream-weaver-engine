#!/usr/bin/env python3
"""
Full Knowledge Pipeline
=======================
1. Sync Clawdbot sessions → kimi_memory.db messages
2. Extract knowledge triples → kimi_memory.db knowledge_graph
3. Incremental sync → Graph Kernel / Supabase (only new triples)

Run: python3 ~/projects/dream-weaver-engine/scripts/run_pipeline.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VENV_PYTHON = str(PROJECT_ROOT / ".venv" / "bin" / "python3")
SCRIPTS = PROJECT_ROOT / "scripts"


def run_step(name: str, script: str, timeout: int = 60):
    """Run a pipeline step as a subprocess for isolation."""
    print(f"\n[{name}]")
    try:
        result = subprocess.run(
            [VENV_PYTHON, str(SCRIPTS / script)],
            cwd=str(PROJECT_ROOT),
            timeout=timeout,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.returncode != 0:
            print(f"  ⚠ Step exited with code {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ⚠ Step timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"  ⚠ Step failed: {e}")
        return False


def main():
    print("=" * 60)
    print("  Kimi Knowledge Pipeline")
    print("=" * 60)

    # Step 1: Sync sessions → messages
    run_step("1/3 Sync sessions → messages", "sync_sessions.py", timeout=60)

    # Step 2: Extract knowledge triples
    run_step("2/3 Extract knowledge triples", "extract_knowledge_local.py", timeout=120)

    # Step 3: Incremental sync to Graph Kernel
    run_step("3/3 Sync to Graph Kernel (incremental)", "sync_to_graph_kernel.py", timeout=120)

    # Final stats
    import sqlite3
    MEMORY_DB = PROJECT_ROOT / "memory" / "kimi_memory.db"
    conn = sqlite3.connect(MEMORY_DB)
    msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    kg_count = conn.execute("SELECT COUNT(*) FROM knowledge_graph").fetchone()[0]
    conn.close()

    import json
    state_file = PROJECT_ROOT / "memory" / "gk_sync_state.json"
    gk_synced = 0
    if state_file.exists():
        gk_synced = json.loads(state_file.read_text()).get("last_synced_rowid", 0)

    print("\n" + "=" * 60)
    print(f"  Messages:          {msg_count}")
    print(f"  Knowledge triples: {kg_count}")
    print(f"  GK synced up to:   rowid {gk_synced}")
    print("=" * 60)


if __name__ == "__main__":
    main()
