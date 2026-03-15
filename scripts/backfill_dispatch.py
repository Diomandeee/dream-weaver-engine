#!/usr/bin/env python3
"""Backfill action dispatch for existing bloomed dreams.

Scans dreams_v2.json (the noosphere source) and dispatches any
bloom-ready dreams that haven't been dispatched yet.

Usage:
  python3 backfill_dispatch.py              # dispatch for real
  python3 backfill_dispatch.py --dry-run    # preview only
  python3 backfill_dispatch.py --stats      # show dispatch stats
"""

import json
import sys
from pathlib import Path

# Add parent to path for dream_engine imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dream_engine.action_dispatcher import dispatch_dream_action, get_dispatch_stats
from dream_engine.models import Dream, DreamStage


DREAMS_V2_FILE = Path.home() / ".claude" / "noosphere" / "dreams_v2.json"


def load_v2_dreams() -> list[Dream]:
    """Load dreams from the noosphere dreams_v2.json format."""
    if not DREAMS_V2_FILE.exists():
        print(f"dreams_v2.json not found at {DREAMS_V2_FILE}")
        return []

    with open(DREAMS_V2_FILE) as f:
        data = json.load(f)

    dreams = []
    for raw in data.get("dreams", []):
        # Map v2 format to Dream model
        stage_map = {
            "spore": DreamStage.SEED,
            "germinating": DreamStage.GERMINATING,
            "growing": DreamStage.GROWING,
            "budding": DreamStage.GROWING,
            "blooming": DreamStage.FLOWERING,
            "fruiting": DreamStage.BLOOM,
            "bloom": DreamStage.BLOOM,
        }
        raw_status = raw.get("status", "spore")
        stage = stage_map.get(raw_status, DreamStage.SEED)

        dream = Dream(
            id=raw.get("id", "unknown"),
            title=raw.get("spore", "Untitled"),
            essence=raw.get("spore", ""),
            context="; ".join(raw.get("keywords", [])),
            strength=raw.get("current_strength", 0.0),
            stage=stage,
            tags=raw.get("keywords", []),
            connections=raw.get("pollinates", []) + raw.get("symbiotic_with", []),
        )

        # Add evolution notes from journal
        for entry in raw.get("journal", []):
            details = entry.get("details", {})
            if isinstance(details, dict):
                note = details.get("growth_insight", details.get("guidance", ""))
                if note:
                    dream.evolution_notes.append(str(note)[:300])
            dream.evolution_count += 1

        # Add lucid guidance as evolution context
        for lg in raw.get("lucid_guidance", []):
            guidance = lg.get("guidance", "")
            if guidance:
                dream.evolution_notes.append(f"Guidance: {guidance}")

        # Add synthesis if present
        if raw.get("synthesis"):
            synth = raw["synthesis"]
            if isinstance(synth, dict):
                synth = json.dumps(synth)
            dream.evolution_notes.append(f"Synthesis: {str(synth)[:300]}")

        dreams.append(dream)

    return dreams


def main():
    dry_run = "--dry-run" in sys.argv
    stats_only = "--stats" in sys.argv

    if stats_only:
        stats = get_dispatch_stats()
        print(f"Total dispatched: {stats['total_dispatched']}")
        for d in stats.get("dreams", []):
            print(f"  {d['title'][:60]:60} | str={d['strength']:.2f} | task={d['task_id'][:8]}...")
        return

    dreams = load_v2_dreams()
    print(f"Loaded {len(dreams)} dreams from {DREAMS_V2_FILE}")

    # Filter to bloom-ready
    bloom_ready = [
        d for d in dreams
        if d.strength >= 0.75
        and d.stage in (DreamStage.BLOOM, DreamStage.FLOWERING)
    ]
    print(f"Bloom-ready (strength >= 0.75): {len(bloom_ready)}")

    if not bloom_ready:
        print("No dreams ready for dispatch.")
        return

    # Sort by strength descending
    bloom_ready.sort(key=lambda d: d.strength, reverse=True)

    dispatched = 0
    for dream in bloom_ready:
        print(f"\n{'[DRY] ' if dry_run else ''}Dispatching: {dream.title}")
        print(f"  Stage: {dream.stage.value} | Strength: {dream.strength:.2f} | Evolutions: {dream.evolution_count}")
        result = dispatch_dream_action(dream, dry_run=dry_run)
        if result:
            dispatched += 1
            if not dry_run:
                print(f"  → Task ID: {result.get('task_id', '?')}")

    print(f"\n{'[DRY RUN] Would have dispatched' if dry_run else 'Dispatched'}: {dispatched}/{len(bloom_ready)} dreams")


if __name__ == "__main__":
    main()
