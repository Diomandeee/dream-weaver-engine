#!/usr/bin/env python3
"""Standalone auto-dispatch runner — can be called by cron or manually.

Scans the idea vault for undispatched bloomed dreams, classifies them,
generates execution plans, and routes to appropriate Discord channels.

Also processes the Discord dispatch queue (sends queued messages).

Usage:
  python3 run-auto-dispatch.py              # Full dispatch cycle
  python3 run-auto-dispatch.py --dry-run    # Preview without sending
  python3 run-auto-dispatch.py --status     # Show dispatch status
  python3 run-auto-dispatch.py --flush      # Flush Discord queue
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Ensure we can import the dream engine
sys.path.insert(0, str(Path(__file__).parent.parent))

from dream_engine.auto_dispatch import (
    process_bloomed_dreams,
    show_status,
    load_dispatch_state,
)

STATE_DIR = Path.home() / ".clawdbot" / "state"
QUEUE_FILE = STATE_DIR / "discord-dispatch-queue.json"


def flush_discord_queue(dry_run: bool = False) -> int:
    """Send queued Discord messages via clawdbot CLI.
    
    Returns number of messages sent.
    """
    if not QUEUE_FILE.exists():
        return 0
    
    try:
        with open(QUEUE_FILE) as f:
            queue = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0
    
    pending = [m for m in queue if not m.get("delivered")]
    if not pending:
        return 0
    
    sent = 0
    for msg in pending:
        channel_id = msg.get("channel_id")
        message = msg.get("message", "")
        thread_name = msg.get("thread_name")
        
        if dry_run:
            print(f"  [DRY RUN] Would send to {msg.get('channel_name', channel_id)}: {message[:80]}...")
            msg["delivered"] = True
            sent += 1
            continue
        
        try:
            # Use clawdbot's message tool via the gateway API
            # For now, write to a file that the Clawdbot session picks up
            outbox_file = STATE_DIR / "dispatch-outbox.json"
            outbox = []
            if outbox_file.exists():
                try:
                    with open(outbox_file) as f:
                        outbox = json.load(f)
                except (json.JSONDecodeError, IOError):
                    outbox = []
            
            outbox.append({
                "channel_id": channel_id,
                "message": message,
                "thread_name": thread_name,
                "task_id": msg.get("task_id"),
                "pending": True,
            })
            
            with open(outbox_file, "w") as f:
                json.dump(outbox, f, indent=2)
            
            msg["delivered"] = True
            sent += 1
            print(f"  ✉️ Queued for #{msg.get('channel_name', '?')}: {msg.get('task_id', '?')}")
            
        except Exception as e:
            print(f"  ❌ Failed to queue message: {e}")
    
    # Save updated queue
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)
    
    return sent


def main():
    if "--status" in sys.argv:
        show_status()
        return
    
    dry_run = "--dry-run" in sys.argv
    flush_only = "--flush" in sys.argv
    
    if flush_only:
        sent = flush_discord_queue(dry_run=dry_run)
        print(f"Flushed {sent} messages from queue")
        return
    
    # Run full dispatch cycle
    print("🌸→⚡ Auto-Dispatch Bridge")
    print("=" * 40)
    
    result = process_bloomed_dreams(dry_run=dry_run)
    
    print(f"\nScanned: {result.get('scanned', 0)} ideas")
    print(f"Dispatched: {result.get('dispatched', 0)} dreams")
    
    # Flush the Discord queue
    if not dry_run and result.get("dispatched", 0) > 0:
        print("\nFlushing Discord queue...")
        sent = flush_discord_queue()
        print(f"Queued {sent} messages for delivery")
    
    # Print dispatch details
    for record in result.get("records", []):
        print(f"\n  🌸 {record.get('title', '?')}")
        print(f"     Action: {record.get('action')} | Priority: {record.get('priority')}")
        print(f"     → #{record.get('channel')} | Task: {record.get('task_id')}")
        print(f"     Confidence: {record.get('confidence', 0):.2f} | {record.get('reasoning', '')}")


if __name__ == "__main__":
    main()
