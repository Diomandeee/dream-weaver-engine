"""Auto-bridge bloomed dreams to the Idea Vault v2.

When a dream reaches BLOOM stage (strength >= 0.8), creates a structured
idea file in ~/.clawdbot/state/idea-vault/ and logs the event.

v2 additions:
- Retroactive sync: bridge_all_bloomed() for existing blooms
- Richer idea metadata (evolution trail, connections, tags)
- Bridge stats and deduplication
- Claim extraction from evolution notes
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .models import Dream, GardenState

IDEA_VAULT_DIR = Path.home() / ".clawdbot" / "state" / "idea-vault"
BRIDGE_LOG_FILE = Path.home() / ".clawdbot" / "state" / "bridge-log.json"
BRIDGE_STATS_FILE = Path.home() / ".clawdbot" / "state" / "bridge-stats.json"


def bridge_to_idea_vault(dream: "Dream") -> bool:
    """Bridge a bloomed dream to the idea vault.

    Creates a structured JSON file in the vault and appends to the bridge log.
    Returns True if the idea was bridged, False if skipped.
    """
    from .models import DreamStage

    # Guard: only bridge actual blooms (relaxed — bloom OR strength >= 0.8)
    if dream.strength < 0.8 and dream.stage != DreamStage.BLOOM:
        return False

    # Ensure directories exist
    IDEA_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    BRIDGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    idea_file = IDEA_VAULT_DIR / f"{dream.id}.json"
    now_iso = datetime.utcnow().isoformat() + "Z"

    # Extract claims from evolution notes
    claims = _extract_claims(dream.evolution_notes) if dream.evolution_notes else []

    idea = {
        "id": dream.id,
        "title": dream.title,
        "essence": dream.essence,
        "context": dream.context if hasattr(dream, 'context') else "",
        "source": "dream-weaver",
        "status": "inbox",
        "confidence": round(dream.strength, 3),
        "tags": list(dream.tags),
        "connections": list(dream.connections) if dream.connections else [],
        "evolution_count": dream.evolution_count,
        "evolution_trail": list(dream.evolution_notes[-10:]) if dream.evolution_notes else [],
        "claims": claims,
        "bloom_date": now_iso,
        "created_at": dream.created_at.isoformat() + "Z" if dream.created_at else now_iso,
        "bridged_at": now_iso,
        "content_hash": _content_hash(dream),
    }

    # Check for existing — only overwrite if content changed
    if idea_file.exists():
        try:
            with open(idea_file) as f:
                existing = json.load(f)
            if existing.get("content_hash") == idea["content_hash"]:
                return False  # No change, skip
        except (json.JSONDecodeError, IOError):
            pass

    # Write idea
    with open(idea_file, "w") as f:
        json.dump(idea, f, indent=2)

    # Append to bridge log
    log_entry = {
        "dream_id": dream.id,
        "title": dream.title,
        "strength": round(dream.strength, 3),
        "action": "bridged",
        "idea_file": str(idea_file),
        "claims_extracted": len(claims),
        "timestamp": now_iso,
    }
    _append_bridge_log(log_entry)

    # Update stats
    _update_stats(dream)

    print(f"[IdeaBridge] Bridged '{dream.title}' → {idea_file} ({len(claims)} claims)")
    return True


def bridge_all_bloomed(state: "GardenState") -> dict:
    """Retroactively bridge all bloomed dreams in the garden.

    Useful for bootstrapping the vault from an existing garden with blooms.
    Returns stats dict.
    """
    from .models import DreamStage

    results = {"bridged": 0, "skipped": 0, "errors": 0}

    for dream_id, dream in state.dreams.items():
        if dream.strength >= 0.8 or dream.stage == DreamStage.BLOOM:
            try:
                if bridge_to_idea_vault(dream):
                    results["bridged"] += 1
                else:
                    results["skipped"] += 1
            except Exception as e:
                print(f"[IdeaBridge] Error bridging {dream.title}: {e}")
                results["errors"] += 1
        else:
            results["skipped"] += 1

    print(f"[IdeaBridge] Retroactive sync: {results['bridged']} bridged, "
          f"{results['skipped']} skipped, {results['errors']} errors")
    return results


def get_bridge_stats() -> dict:
    """Read current bridge stats."""
    if BRIDGE_STATS_FILE.exists():
        try:
            with open(BRIDGE_STATS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"total_bridged": 0, "total_claims": 0, "last_bridge": None}


def _extract_claims(notes: list[str]) -> list[dict]:
    """Extract falsifiable claims from evolution notes.

    Looks for patterns like:
    - "Key insight: ..."
    - Sentences with "could", "should", "enables", "allows"
    - Quantitative claims (numbers, percentages)
    """
    claims = []
    import re

    for note in notes:
        if not note:
            continue

        # Key insight pattern
        insight_match = re.findall(r"(?:Key insight|Insight|Finding):\s*(.+?)(?:\.|$)", note, re.I)
        for m in insight_match:
            claims.append({
                "text": m.strip(),
                "type": "insight",
                "source_note": note[:100],
            })

        # Quantitative claims
        quant_match = re.findall(r"([^.]*\d+[\d.,]*%?[^.]*\.)", note)
        for m in quant_match:
            if len(m.strip()) > 20:  # Skip trivial matches
                claims.append({
                    "text": m.strip(),
                    "type": "quantitative",
                    "source_note": note[:100],
                })

        # "Could/should/enables" pattern (limited to avoid noise)
        potential_match = re.findall(
            r"([^.]*(?:could|should|enables|allows|proves|demonstrates)[^.]{10,}\.)", note, re.I
        )
        for m in potential_match[:2]:  # Max 2 per note
            claims.append({
                "text": m.strip(),
                "type": "hypothesis",
                "source_note": note[:100],
            })

    # Deduplicate by text
    seen = set()
    unique_claims = []
    for c in claims:
        key = c["text"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_claims.append(c)

    return unique_claims[:20]  # Cap at 20 claims per dream


def _content_hash(dream: "Dream") -> str:
    """Generate a content hash for deduplication."""
    content = f"{dream.title}|{dream.essence}|{dream.strength}|{dream.evolution_count}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _append_bridge_log(entry: dict):
    """Append an entry to the bridge log JSON array."""
    log: list = []
    if BRIDGE_LOG_FILE.exists():
        try:
            with open(BRIDGE_LOG_FILE) as f:
                log = json.load(f)
            if not isinstance(log, list):
                log = []
        except (json.JSONDecodeError, IOError):
            log = []

    log.append(entry)

    with open(BRIDGE_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def _update_stats(dream: "Dream"):
    """Update bridge stats."""
    stats = get_bridge_stats()
    stats["total_bridged"] = stats.get("total_bridged", 0) + 1
    stats["last_bridge"] = datetime.utcnow().isoformat() + "Z"
    stats["last_dream"] = dream.title

    BRIDGE_STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BRIDGE_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)
