"""Sync dream garden state to Supabase noosphere_dreams table.

Bi-directional sync:
- Upload: local dream state → Supabase (after each evolution cycle)
- Download: Supabase → local (for multi-device consistency)

Uses the existing noosphere_dreams schema:
  id, seed_idea, keywords[], status, connections[], connection_strength,
  synthesis(jsonb), approaches(jsonb), pollinated_by[], pollinated[],
  metamorphosis(jsonb), created_at, updated_at, synced_from,
  title, essence, patterns[], connection_count, last_evolved_at
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Dream, GardenState


def sync_garden_to_supabase(state: "GardenState", source_device: str = "github-actions") -> dict:
    """Push all dreams to Supabase noosphere_dreams table.

    Uses upsert (ON CONFLICT id) so it's safe to call repeatedly.

    Returns: {"synced": count, "errors": count}
    """
    url, key = _get_credentials()
    if not url or not key:
        return {"synced": 0, "errors": 0, "reason": "no credentials"}

    results = {"synced": 0, "errors": 0}

    for dream_id, dream in state.dreams.items():
        row = _dream_to_row(dream, source_device)
        try:
            _upsert_dream(url, key, row)
            results["synced"] += 1
        except Exception as e:
            print(f"[SupaSync] Error syncing {dream.title}: {e}")
            results["errors"] += 1

    print(f"[SupaSync] Synced {results['synced']}/{len(state.dreams)} dreams to Supabase")
    return results


def sync_dispatched_status(dream_id: str, task_id: str, status: str = "actuating") -> bool:
    """Update a specific dream's dispatch status in Supabase."""
    url, key = _get_credentials()
    if not url or not key:
        return False

    import urllib.request
    import urllib.error

    api_url = f"{url}/rest/v1/noosphere_dreams?id=eq.{dream_id}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    payload = json.dumps({
        "status": status,
        "metamorphosis": json.dumps({
            "dispatched_task_id": task_id,
            "dispatched_at": datetime.utcnow().isoformat() + "Z",
        }),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }).encode("utf-8")

    req = urllib.request.Request(api_url, data=payload, headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        print(f"[SupaSync] Failed to update dispatch status: {e}")
        return False


def _dream_to_row(dream: "Dream", source_device: str) -> dict:
    """Convert a Dream model to a noosphere_dreams row."""
    # Build synthesis JSON from evolution data
    synthesis = {
        "evolution_count": dream.evolution_count,
        "evolution_notes": list(dream.evolution_notes[-10:]) if dream.evolution_notes else [],
        "dispatched_task_id": dream.dispatched_task_id,
        "dispatched_at": dream.dispatched_at.isoformat() + "Z" if dream.dispatched_at else None,
        "shipped_at": dream.shipped_at.isoformat() + "Z" if dream.shipped_at else None,
    }

    # Build approaches from tags
    approaches = {
        "tags": list(dream.tags),
        "source": dream.source,
        "enriched": dream.enriched,
    }

    return {
        "id": dream.id,
        "seed_idea": dream.essence[:500] if dream.essence else "",
        "keywords": list(dream.tags)[:20],
        "status": dream.stage.value if hasattr(dream.stage, "value") else str(dream.stage),
        "connections": list(dream.connections) if dream.connections else [],
        "connection_strength": round(dream.strength, 4),
        "synthesis": json.dumps(synthesis),
        "approaches": json.dumps(approaches),
        "pollinated_by": [],
        "pollinated": [],
        "synced_from": source_device,
        "title": dream.title,
        "essence": dream.essence,
        "patterns": list(dream.tags)[:10],
        "connection_count": len(dream.connections) if dream.connections else 0,
        "last_evolved_at": dream.last_evolved.isoformat() + "Z" if dream.last_evolved else None,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


def _upsert_dream(url: str, key: str, row: dict):
    """Upsert a single dream row to Supabase."""
    import urllib.request
    import urllib.error

    api_url = f"{url}/rest/v1/noosphere_dreams"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal,resolution=merge-duplicates",
    }

    payload = json.dumps(row).encode("utf-8")
    req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=10):
        pass


def _get_credentials() -> tuple[str, str]:
    """Get Supabase URL and service key from env or .env file."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        env_file = Path.home() / "projects" / "Comp-Core" / ".env"
        if env_file.exists():
            try:
                for line in env_file.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and v:
                            os.environ.setdefault(k, v)
            except Exception:
                pass
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    return url, key
