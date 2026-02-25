#!/usr/bin/env python3
"""Bloom Event Dispatcher — reads bloom-events.json and dispatches via Clawdbot.

This script is called by Clawdbot cron (every 5 min) to pick up bloom events
written by the Dream Weaver engine and deliver them to Telegram/WhatsApp/iMessage.

Usage:
  python3 bloom-dispatcher.py              # dispatch all pending events
  python3 bloom-dispatcher.py --dry-run    # preview without sending
  python3 bloom-dispatcher.py --stats      # show dispatch stats
"""

import json
import sys
from datetime import datetime
from pathlib import Path

BLOOM_EVENTS_FILE = Path.home() / ".clawdbot" / "state" / "bloom-events.json"
DISPATCH_LOG_FILE = Path.home() / ".clawdbot" / "state" / "bloom-dispatch-log.json"

# Event type → message formatter
EVENT_FORMATTERS = {
    "bloom": lambda e: (
        f"🌺 Dream Bloom!\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🌙 {e['title']}\n\n"
        f"{e['essence']}\n\n"
        f"Strength: {e['strength']:.2f}\n"
        f"🌰→🌱→🌿→🌸→🌺 Complete!\n"
        f"━━━━━━━━━━━━━━━━"
    ),
    "stage_change": lambda e: (
        f"🌙 Dream Stage Change\n"
        f"{e['title']}\n"
        f"{e['essence']}"
    ),
    "milestone": lambda e: (
        f"🔄 Evolution Milestone\n"
        f"{e['title']}: {e['essence']}\n"
        f"Strength: {e['strength']:.2f}"
    ),
    "new_seed": lambda e: (
        f"🌰 New Dream Seed\n"
        f"{e['title']}\n"
        f"{e['essence']}"
    ),
    "digest": lambda e: e["essence"],  # Pre-formatted
}


def load_events() -> list[dict]:
    """Load pending bloom events."""
    if not BLOOM_EVENTS_FILE.exists():
        return []
    try:
        with open(BLOOM_EVENTS_FILE) as f:
            events = json.load(f)
        return events if isinstance(events, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def dispatch_events(dry_run: bool = False) -> dict:
    """Dispatch all undelivered bloom events.

    Returns stats dict with counts.
    """
    events = load_events()
    pending = [e for e in events if not e.get("delivered")]

    if not pending:
        print("[Dispatcher] No pending bloom events")
        return {"pending": 0, "dispatched": 0}

    print(f"[Dispatcher] {len(pending)} pending events")

    dispatched = 0
    for event in pending:
        event_type = event.get("type", "bloom")
        channel = event.get("channel", "telegram")
        formatter = EVENT_FORMATTERS.get(event_type, EVENT_FORMATTERS["bloom"])
        msg = formatter(event)

        if dry_run:
            print(f"  [DRY RUN] Would send to {channel}: {msg[:80]}...")
            event["delivered"] = True
            dispatched += 1
            continue

        # Write dispatch instruction for Clawdbot to pick up
        instruction = {
            "channel": channel,
            "message": msg,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "dream_title": event.get("title", ""),
        }

        # Write to dispatch queue
        _write_dispatch(instruction)
        event["delivered"] = True
        dispatched += 1
        print(f"  [Dispatcher] Queued for {channel}: {event.get('title', '?')}")

    # Save updated events (with delivered flags)
    with open(BLOOM_EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=2)

    # Clean up old delivered events (keep last 50)
    _cleanup_events()

    print(f"[Dispatcher] {dispatched}/{len(pending)} dispatched")
    return {"pending": len(pending), "dispatched": dispatched}


def _write_dispatch(instruction: dict):
    """Append dispatch instruction to log."""
    DISPATCH_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log: list = []
    if DISPATCH_LOG_FILE.exists():
        try:
            with open(DISPATCH_LOG_FILE) as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = []

    log.append(instruction)
    with open(DISPATCH_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def _cleanup_events():
    """Remove old delivered events, keeping last 50."""
    events = load_events()
    delivered = [e for e in events if e.get("delivered")]
    pending = [e for e in events if not e.get("delivered")]

    # Keep last 50 delivered + all pending
    trimmed = pending + delivered[-50:]
    with open(BLOOM_EVENTS_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)


def show_stats():
    """Show dispatch statistics."""
    events = load_events()
    pending = sum(1 for e in events if not e.get("delivered"))
    delivered = sum(1 for e in events if e.get("delivered"))

    log: list = []
    if DISPATCH_LOG_FILE.exists():
        try:
            with open(DISPATCH_LOG_FILE) as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    print(f"Bloom Dispatch Stats:")
    print(f"  Pending: {pending}")
    print(f"  Delivered: {delivered}")
    print(f"  Total dispatched (all time): {len(log)}")
    if log:
        last = log[-1]
        print(f"  Last dispatch: {last.get('timestamp', '?')} → {last.get('channel', '?')}: {last.get('dream_title', '?')}")


if __name__ == "__main__":
    if "--stats" in sys.argv:
        show_stats()
    elif "--dry-run" in sys.argv:
        dispatch_events(dry_run=True)
    else:
        dispatch_events()
