"""Dream Action Dispatcher — converts bloomed dreams into executable mac_tasks.

When a dream reaches BLOOM stage (strength >= 0.8), this module:
1. Generates an actionable task plan from the dream's essence + evolution notes
2. Inserts it as a mac_task in Supabase for mesh node pickup
3. Tracks dispatch state to prevent double-dispatch
4. Updates the dream status to ACTUATING

This is the missing bridge between "dream evolved" and "code gets written."
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Dream, GardenState

# Supabase connection
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Local state tracking
DISPATCH_STATE_FILE = Path.home() / ".clawdbot" / "state" / "dream-action-dispatch.json"

# Project path mapping — dreams map to project directories
PROJECT_HINTS = {
    "voice": "~/Desktop/Comp-Core",
    "cc-speak": "~/Desktop/Comp-Core",
    "cc-dj": "~/Desktop/Comp-Core",
    "graph": "~/projects/Comp-Core",
    "rag": "~/projects/Comp-Core",
    "nko": "~/projects/Comp-Core",
    "sigil": "~/projects/Comp-Core",
    "mobile": "~/Desktop/OpenClawHub",
    "hub": "~/Desktop/OpenClawHub",
    "watch": "~/Desktop/SecuriClaw-Claude",
    "haptic": "~/Desktop/SecuriClaw-Claude",
    "card": "~/Desktop/Comp-Core",
    "mfp": "~/Desktop/Comp-Core",
    "portfolio": "~/Desktop/Comp-Core",
    "dashboard": "~/Desktop/Comp-Core",
    "pulse": "~/Desktop/Comp-Core",
    "agent": "~/Desktop/Comp-Core",
    "infra": "~/Desktop/Comp-Core",
    "milk": "~/Desktop/Comp-Core",
    "koatji": "~/Desktop/Comp-Core",
    "keyboard": "~/Desktop/SpeakFlow",
    "spore": "~/projects/dream-weaver-engine",
    "dream": "~/projects/dream-weaver-engine",
    "sensor": "~/Desktop/Comp-Core",
    "motion": "~/Desktop/Comp-Core",
    "migration": "~/Desktop/Comp-Core",
    "spatial": "~/Desktop/Comp-Core",
}

# Default project for unmatched dreams
DEFAULT_PROJECT = "~/Desktop/Comp-Core"


def dispatch_dream_action(
    dream: "Dream",
    dry_run: bool = False,
    priority: int = 5,
) -> Optional[dict]:
    """Convert a bloomed dream into an executable mac_task.

    Args:
        dream: The dream that reached bloom
        dry_run: Preview without inserting into Supabase
        priority: Task priority (1=highest, 10=lowest). Blooms default to 5.

    Returns:
        Dict with task_id and details, or None if skipped.
    """
    from .models import DreamStage

    # Guard: only dispatch blooms or high-strength dreams
    if dream.strength < 0.7 and dream.stage not in (DreamStage.BLOOM, DreamStage.FLOWERING):
        return None

    # Check if already dispatched
    dispatch_state = _load_dispatch_state()
    dream_hash = _dream_content_hash(dream)
    if dream.id in dispatch_state and dispatch_state[dream.id].get("content_hash") == dream_hash:
        print(f"[ActionDispatch] Already dispatched: {dream.title}")
        return None

    # Build the task content from dream data
    task_content = _build_task_content(dream)
    project_path = _infer_project_path(dream)

    # Adjust priority based on dream strength
    if dream.strength >= 0.9:
        priority = max(1, priority - 2)  # High-strength → higher priority
    elif dream.strength >= 0.8:
        priority = max(2, priority - 1)

    task_record = {
        "task_content": task_content,
        "project_path": project_path,
        "source": "dream-weaver",
        "status": "pending",
        "task_type": "dream-action",
        "priority": priority,
        "plan_mode": True,  # Start in plan mode so agent researches first
        "media_context": json.dumps({
            "dream_id": dream.id,
            "dream_title": dream.title,
            "dream_strength": round(dream.strength, 3),
            "dream_stage": dream.stage.value if hasattr(dream.stage, "value") else str(dream.stage),
            "evolution_count": dream.evolution_count,
            "tags": list(dream.tags)[:20],
        }),
    }

    if dry_run:
        print(f"[ActionDispatch] DRY RUN would dispatch: {dream.title}")
        print(f"  Project: {project_path}")
        print(f"  Priority: {priority}")
        print(f"  Task length: {len(task_content)} chars")
        return {"dry_run": True, "task": task_record}

    # Insert into Supabase mac_tasks
    task_id = _insert_mac_task(task_record)
    if not task_id:
        print(f"[ActionDispatch] Failed to insert task for: {dream.title}")
        return None

    # Track dispatch
    dispatch_state[dream.id] = {
        "task_id": task_id,
        "content_hash": dream_hash,
        "dispatched_at": datetime.utcnow().isoformat() + "Z",
        "dream_title": dream.title,
        "dream_strength": round(dream.strength, 3),
        "project_path": project_path,
    }
    _save_dispatch_state(dispatch_state)

    print(f"[ActionDispatch] Dispatched: {dream.title} → mac_tasks/{task_id}")
    return {"task_id": task_id, "project_path": project_path, **task_record}


def dispatch_bloomed_dreams(
    state: "GardenState",
    max_dispatch: int = 3,
    dry_run: bool = False,
    min_strength: float = 0.75,
) -> list[dict]:
    """Scan garden for bloom-ready dreams and dispatch actions for them.

    Args:
        state: Current garden state
        max_dispatch: Max tasks to create per cycle (avoid flooding the queue)
        dry_run: Preview mode
        min_strength: Minimum strength to consider for dispatch

    Returns:
        List of dispatch results.
    """
    from .models import DreamStage

    results = []
    dispatch_state = _load_dispatch_state()

    # Get bloom-ready dreams sorted by strength (strongest first)
    candidates = [
        d for d in state.dreams.values()
        if d.strength >= min_strength
        and d.stage in (DreamStage.BLOOM, DreamStage.FLOWERING)
        and d.id not in dispatch_state
    ]
    candidates.sort(key=lambda d: d.strength, reverse=True)

    if not candidates:
        print(f"[ActionDispatch] No undispatched bloom-ready dreams (min_strength={min_strength})")
        return results

    print(f"[ActionDispatch] {len(candidates)} bloom-ready dreams, dispatching up to {max_dispatch}")

    for dream in candidates[:max_dispatch]:
        result = dispatch_dream_action(dream, dry_run=dry_run)
        if result:
            results.append(result)

    return results


def get_dispatch_stats() -> dict:
    """Get dispatch statistics."""
    state = _load_dispatch_state()
    return {
        "total_dispatched": len(state),
        "dreams": [
            {
                "id": did,
                "title": info.get("dream_title", "?"),
                "strength": info.get("dream_strength", 0),
                "dispatched_at": info.get("dispatched_at", "?"),
                "task_id": info.get("task_id", "?"),
            }
            for did, info in state.items()
        ],
    }


# ---------------------------------------------------------------------------
# Task content generation
# ---------------------------------------------------------------------------

def _build_task_content(dream: "Dream") -> str:
    """Build an actionable task prompt from a dream's accumulated knowledge.

    This is the key transformation: dream essence + evolution notes → executable task.
    """
    # Collect evolution insights (last 5, most recent and relevant)
    insights = ""
    if dream.evolution_notes:
        recent_notes = dream.evolution_notes[-5:]
        insights = "\n".join(f"- {note[:300]}" for note in recent_notes if note)

    # Build tag context for scope
    tag_context = ", ".join(dream.tags[:10]) if dream.tags else "general"

    # Connection context
    connection_ctx = ""
    if dream.connections:
        connection_ctx = f"\nRelated systems: {', '.join(dream.connections[:5])}"

    task = f"""DREAM-TO-ACTION: {dream.title}

## Objective
{dream.essence}

## Context
{dream.context if hasattr(dream, 'context') and dream.context else 'No additional context.'}
{connection_ctx}

## Evolution Insights
The Dream Garden evolved this idea through {dream.evolution_count} cycles. Key findings:
{insights if insights else '- No evolution notes yet.'}

## Scope
Domain tags: {tag_context}
Dream strength: {dream.strength:.2f} (high confidence — this idea has been validated through evolution)

## Instructions
1. Research the current state of related code in this project
2. Create a concrete implementation plan with specific files to create/modify
3. Implement the core functionality (start with MVP, not full scope)
4. Write tests for critical paths
5. Commit with message referencing dream ID: {dream.id}

Source: Dream Garden (auto-dispatched at strength {dream.strength:.2f})"""

    return task


def _infer_project_path(dream: "Dream") -> str:
    """Infer the best project path for a dream based on its tags and title."""
    # Check tags first
    for tag in dream.tags:
        tag_lower = tag.lower()
        for hint_key, path in PROJECT_HINTS.items():
            if hint_key in tag_lower:
                return path

    # Check title
    title_lower = dream.title.lower()
    for hint_key, path in PROJECT_HINTS.items():
        if hint_key in title_lower:
            return path

    # Check essence
    if hasattr(dream, "essence"):
        essence_lower = dream.essence.lower()
        for hint_key, path in PROJECT_HINTS.items():
            if hint_key in essence_lower:
                return path

    return DEFAULT_PROJECT


# ---------------------------------------------------------------------------
# Supabase integration
# ---------------------------------------------------------------------------

def _insert_mac_task(task: dict) -> Optional[str]:
    """Insert a task into Supabase mac_tasks table. Returns task UUID or None."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        # Fallback: try loading from .env
        env_file = Path.home() / "projects" / "Comp-Core" / ".env"
        if env_file.exists():
            _load_env(env_file)

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        print("[ActionDispatch] No Supabase credentials — cannot insert task")
        return None

    import urllib.request
    import urllib.error

    api_url = f"{url}/rest/v1/mac_tasks"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    payload = json.dumps(task).encode("utf-8")
    req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if isinstance(result, list) and result:
                return result[0].get("id")
            return None
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"[ActionDispatch] Supabase error {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"[ActionDispatch] Insert failed: {e}")
        return None


def _load_env(env_file: Path):
    """Load .env file into os.environ (simple key=value parser)."""
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and value:
                    os.environ.setdefault(key, value)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Local dispatch state
# ---------------------------------------------------------------------------

def _load_dispatch_state() -> dict:
    """Load dispatch tracking state."""
    if DISPATCH_STATE_FILE.exists():
        try:
            with open(DISPATCH_STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_dispatch_state(state: dict):
    """Save dispatch tracking state."""
    DISPATCH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DISPATCH_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _dream_content_hash(dream: "Dream") -> str:
    """Hash dream content for change detection."""
    content = f"{dream.title}|{dream.essence}|{dream.strength:.2f}|{dream.evolution_count}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
