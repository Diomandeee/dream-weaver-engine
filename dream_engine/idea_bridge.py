"""Auto-bridge bloomed dreams to the Idea Vault.

When a dream reaches BLOOM stage (strength >= 0.8), creates a structured
idea file in ~/.clawdbot/state/idea-vault/ and logs the event.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Dream

IDEA_VAULT_DIR = Path.home() / ".clawdbot" / "state" / "idea-vault"
BRIDGE_LOG_FILE = Path.home() / ".clawdbot" / "state" / "bridge-log.json"


def bridge_to_idea_vault(dream: "Dream") -> bool:
    """Bridge a bloomed dream to the idea vault.

    Creates a structured JSON file in the vault and appends to the bridge log.
    Returns True if the idea was bridged, False if skipped (already exists or not bloom-ready).
    """
    from .models import DreamStage

    # Guard: only bridge actual blooms
    if dream.strength < 0.8 or dream.stage != DreamStage.BLOOM:
        return False

    # Ensure directories exist
    IDEA_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    BRIDGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    idea_file = IDEA_VAULT_DIR / f"{dream.id}.json"

    now_iso = datetime.utcnow().isoformat() + "Z"

    idea = {
        "id": dream.id,
        "title": dream.title,
        "essence": dream.essence,
        "source": "dream-weaver",
        "status": "inbox",
        "confidence": round(dream.strength, 3),
        "tags": list(dream.tags),
        "evolution_count": dream.evolution_count,
        "bloom_date": now_iso,
        "synthesis_notes": list(dream.evolution_notes[-5:]) if dream.evolution_notes else [],
        "created_at": now_iso,
    }

    # Write idea (overwrite if re-bloomed with updated data)
    with open(idea_file, "w") as f:
        json.dump(idea, f, indent=2)

    # Append to bridge log
    log_entry = {
        "dream_id": dream.id,
        "title": dream.title,
        "strength": round(dream.strength, 3),
        "action": "bridged",
        "idea_file": str(idea_file),
        "timestamp": now_iso,
    }
    _append_bridge_log(log_entry)

    print(f"[IdeaBridge] Bridged '{dream.title}' → {idea_file}")
    return True


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
