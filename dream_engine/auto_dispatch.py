"""Auto-Dispatch Bridge — Bloomed dreams → Classified → Executed.

When a dream blooms (strength >= 0.8), this module:
1. Classifies the dream type (code, content, research, business, creative)
2. Generates an actionable execution plan
3. Routes to the appropriate execution surface:
   - Code tasks → #forge thread + Pulse session spawn
   - Content → generation queue (Serenity/MFP/BWB pipelines)
   - Research → #research channel + research engine deep dive
   - Business → CRM action or outreach task
   - Creative → #workshop for TIE/evoflow exploration
4. Posts dispatch confirmation to #dream-weave and #bridge
5. Tracks execution status for bidirectional feedback

Bidirectional: execution results feed BACK into the dream,
enriching it or spawning daughter dreams from what was learned.

HEF Integration: Uses HEF-style task decomposition with instance
tracking, generation counting, and priority routing.
"""

import json
import os
import subprocess
import hashlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# ─── Paths ───────────────────────────────────────────────────────────

STATE_DIR = Path.home() / ".clawdbot" / "state"
DISPATCH_STATE_FILE = STATE_DIR / "auto-dispatch-state.json"
DISPATCH_LOG_FILE = STATE_DIR / "auto-dispatch-log.json"
IDEA_VAULT_DIR = STATE_DIR / "idea-vault"
FEEDBACK_DIR = STATE_DIR / "dispatch-feedback"

# Discord channel IDs (NUMU FARE)
CHANNELS = {
    "bridge": "1475191380757446808",
    "forge": "1479124848339976293",  # Forum channel — needs thread_create, not send
    "garden": "1478410304017666141",
    "dream_weave": "1479124944175759523",
    "research": "1475191451485733127",
    "workshop": "1475191428358602812",
    "pulse_control": "1475191391276634227",
    "pulse_feed": "1475191395927986176",
    "garden": "1478410304017666141",
    "numu_alerts": "1479124802420609174",
}


class DreamAction(str, Enum):
    """What kind of action a dream needs."""
    CODE = "code"           # Build something — Pulse session / forge thread
    CONTENT = "content"     # Create content — video, article, social post
    RESEARCH = "research"   # Deep research — academic, market, technical
    BUSINESS = "business"   # Business action — CRM, outreach, sales
    CREATIVE = "creative"   # Creative exploration — TIE/evoflow/workshop
    INFRA = "infra"         # Infrastructure — tools, pipelines, config
    HYBRID = "hybrid"       # Multiple action types needed


class DispatchPriority(str, Enum):
    """HEF-style priority levels."""
    EMBER = "ember"       # Low — background, whenever
    SPARK = "spark"       # Medium — do this soon
    FORGE = "forge"       # Standard — active work
    INFERNO = "inferno"   # Urgent — drop everything


# ─── Classification ──────────────────────────────────────────────────

# Keyword-based fast classification (no LLM needed for obvious cases)
ACTION_KEYWORDS = {
    DreamAction.CODE: [
        "app", "build", "ios", "swift", "react", "api", "endpoint", "database",
        "cli", "tool", "pipeline", "deploy", "integration", "module", "engine",
        "compiler", "parser", "server", "client", "sdk", "plugin", "script",
        "xcode", "expo", "node", "python", "typescript", "shopify",
    ],
    DreamAction.CONTENT: [
        "video", "article", "blog", "social", "youtube", "tiktok", "instagram",
        "substack", "newsletter", "script", "narration", "meditation", "audio",
        "podcast", "reel", "thumbnail", "content", "publish", "post",
    ],
    DreamAction.RESEARCH: [
        "research", "study", "analyze", "compare", "survey", "academic",
        "paper", "literature", "data", "statistics", "trend", "market",
        "competitor", "landscape", "deep dive", "investigation",
    ],
    DreamAction.BUSINESS: [
        "sales", "crm", "lead", "outreach", "pitch", "pricing", "revenue",
        "customer", "retail", "b2b", "delivery", "invoice", "contract",
        "partnership", "wholesale", "distribution", "koji", "koatji",
    ],
    DreamAction.CREATIVE: [
        "brainstorm", "explore", "experiment", "prototype", "concept",
        "aesthetic", "design", "art", "music", "sound", "visual", "narrative",
        "story", "mythology", "lore", "dream", "vision", "imagination",
    ],
    DreamAction.INFRA: [
        "infrastructure", "monitoring", "ci/cd", "devops", "tailscale",
        "docker", "launchctl", "cron", "health check", "logging", "metrics",
        "grafana", "prometheus", "backup", "migration",
    ],
}

# Project mapping for routing
PROJECT_KEYWORDS = {
    "bwb": ["bwb", "brews", "coffee", "barista", "pos", "kiosk", "square"],
    "koji": ["koji", "koatji", "oat milk", "milkmen", "delivery"],
    "mfp": ["mfp", "meaning", "trading card", "wisdom card", "power card"],
    "serenity": ["serenity", "soother", "meditation", "therapeutic", "calm"],
    "eternal": ["eternal", "litrpg", "odyssey", "mythology", "game"],
    "nko": ["nko", "n'ko", "manding", "bambara", "cross-script", "griot"],
    "claw": ["claw", "agent", "clawdbot", "openclaw", "dream weaver"],
    "speak": ["speak", "voice", "transcription", "whisper", "speakflow"],
}


def classify_dream(dream_data: dict) -> dict:
    """Classify a bloomed dream into action type + priority + project.
    
    Uses keyword matching first (fast, free), falls back to
    LLM classification for ambiguous cases.
    
    Returns:
        {
            "action": DreamAction,
            "priority": DispatchPriority,
            "project": str or None,
            "confidence": float,
            "reasoning": str,
            "sub_actions": list[DreamAction],  # For hybrid
        }
    """
    text = f"{dream_data.get('title', '')} {dream_data.get('essence', '')} {dream_data.get('context', '')}".lower()
    tags = [t.lower() for t in dream_data.get("tags", [])]
    
    # Score each action type
    scores = {}
    for action, keywords in ACTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        # Tag bonus
        score += sum(0.5 for tag in tags if any(kw in tag for kw in keywords))
        scores[action] = score
    
    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_action = ranked[0][0] if ranked[0][1] > 0 else DreamAction.CREATIVE
    top_score = ranked[0][1]
    
    # Detect hybrid (multiple strong signals)
    strong_actions = [a for a, s in ranked if s >= top_score * 0.6 and s > 0]
    is_hybrid = len(strong_actions) > 1
    
    # Determine priority based on dream strength + evolution count
    strength = dream_data.get("confidence", dream_data.get("strength", 0.5))
    evo_count = dream_data.get("evolution_count", 0)
    
    if strength >= 0.95 and evo_count >= 20:
        priority = DispatchPriority.INFERNO
    elif strength >= 0.9 or evo_count >= 15:
        priority = DispatchPriority.FORGE
    elif strength >= 0.8:
        priority = DispatchPriority.SPARK
    else:
        priority = DispatchPriority.EMBER
    
    # Detect project
    project = None
    for proj, keywords in PROJECT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            project = proj
            break
    
    confidence = min(1.0, top_score / 5.0) if top_score > 0 else 0.3
    
    return {
        "action": DreamAction.HYBRID if is_hybrid else top_action,
        "priority": priority,
        "project": project,
        "confidence": confidence,
        "reasoning": f"Top signals: {', '.join(f'{a.value}({s:.1f})' for a, s in ranked[:3] if s > 0)}",
        "sub_actions": [a for a in strong_actions] if is_hybrid else [top_action],
    }


# ─── Execution Plan Generation ──────────────────────────────────────

def generate_execution_plan(dream_data: dict, classification: dict) -> dict:
    """Generate a concrete execution plan from a classified dream.
    
    Returns a HEF-style task structure with:
    - Task tree (hierarchical steps)
    - Resource requirements
    - Estimated effort
    - Success criteria
    """
    action = classification["action"]
    project = classification["project"]
    title = dream_data.get("title", "Untitled Dream")
    essence = dream_data.get("essence", "")
    
    # Generate task ID (HEF-style)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    task_hash = hashlib.md5(f"{title}{timestamp}".encode()).hexdigest()[:6]
    task_id = f"dream_{timestamp}_{task_hash}"
    
    plan = {
        "task_id": task_id,
        "dream_id": dream_data.get("id"),
        "title": title,
        "essence": essence,
        "action": action.value if isinstance(action, DreamAction) else action,
        "priority": classification["priority"].value if isinstance(classification["priority"], DispatchPriority) else classification["priority"],
        "project": project,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "status": "planned",
        "steps": [],
        "success_criteria": [],
        "estimated_effort": "medium",
    }
    
    # Generate steps based on action type
    if action == DreamAction.CODE or action == DreamAction.INFRA:
        plan["steps"] = [
            {"step": 1, "action": "scaffold", "desc": f"Create project structure for: {title}"},
            {"step": 2, "action": "implement", "desc": f"Build core functionality: {essence[:100]}"},
            {"step": 3, "action": "test", "desc": "Write tests and verify"},
            {"step": 4, "action": "integrate", "desc": f"Integrate with {'project ' + project if project else 'ecosystem'}"},
            {"step": 5, "action": "deploy", "desc": "Deploy and verify in production"},
        ]
        plan["execution_surface"] = "pulse"
        plan["estimated_effort"] = "high"
        plan["success_criteria"] = ["Code compiles", "Tests pass", "Deployed successfully"]
        
    elif action == DreamAction.CONTENT:
        plan["steps"] = [
            {"step": 1, "action": "outline", "desc": f"Create content outline for: {title}"},
            {"step": 2, "action": "draft", "desc": "Generate first draft"},
            {"step": 3, "action": "refine", "desc": "Edit and polish"},
            {"step": 4, "action": "produce", "desc": "Generate final media (video/audio/text)"},
            {"step": 5, "action": "publish", "desc": "Publish to target platform"},
        ]
        plan["execution_surface"] = "content_pipeline"
        plan["estimated_effort"] = "medium"
        plan["success_criteria"] = ["Content created", "Quality review passed", "Published"]
        
    elif action == DreamAction.RESEARCH:
        plan["steps"] = [
            {"step": 1, "action": "scope", "desc": f"Define research scope: {title}"},
            {"step": 2, "action": "gather", "desc": "Collect sources and data"},
            {"step": 3, "action": "analyze", "desc": "Synthesize findings"},
            {"step": 4, "action": "report", "desc": "Generate research report"},
            {"step": 5, "action": "seed", "desc": "Plant new dream seeds from findings"},
        ]
        plan["execution_surface"] = "research_engine"
        plan["estimated_effort"] = "medium"
        plan["success_criteria"] = ["Research report generated", "Key insights extracted", "Seeds planted"]
        
    elif action == DreamAction.BUSINESS:
        plan["steps"] = [
            {"step": 1, "action": "assess", "desc": f"Assess business opportunity: {title}"},
            {"step": 2, "action": "plan", "desc": "Create action plan"},
            {"step": 3, "action": "execute", "desc": "Execute business action (CRM/outreach/etc)"},
            {"step": 4, "action": "follow_up", "desc": "Set follow-up reminders"},
        ]
        plan["execution_surface"] = "crm"
        plan["estimated_effort"] = "low"
        plan["success_criteria"] = ["Action taken", "Logged in CRM", "Follow-up scheduled"]
        
    elif action == DreamAction.CREATIVE:
        plan["steps"] = [
            {"step": 1, "action": "explore", "desc": f"Divergent exploration: {title}"},
            {"step": 2, "action": "synthesize", "desc": "Converge on strongest threads"},
            {"step": 3, "action": "prototype", "desc": "Create tangible prototype"},
            {"step": 4, "action": "evolve", "desc": "Run through TIE techniques"},
        ]
        plan["execution_surface"] = "workshop"
        plan["estimated_effort"] = "medium"
        plan["success_criteria"] = ["New ideas generated", "Prototype created", "Evolution path defined"]
        
    elif action == DreamAction.HYBRID:
        # Combine steps from sub-actions
        plan["steps"] = [
            {"step": 1, "action": "decompose", "desc": f"Break down hybrid dream: {title}"},
        ]
        for i, sub in enumerate(classification.get("sub_actions", [])[:3], start=2):
            plan["steps"].append({
                "step": i,
                "action": f"execute_{sub.value}",
                "desc": f"Execute {sub.value} track",
            })
        plan["steps"].append({
            "step": len(plan["steps"]) + 1,
            "action": "converge",
            "desc": "Merge results from all tracks",
        })
        plan["execution_surface"] = "multi"
        plan["estimated_effort"] = "high"
        plan["success_criteria"] = ["All tracks executed", "Results merged", "Feedback loop closed"]
    
    return plan


# ─── Dispatchers ─────────────────────────────────────────────────────

def dispatch_to_forge(plan: dict, dream_data: dict) -> dict:
    """Dispatch a code/infra task to the #forge forum as a thread."""
    title = plan["title"]
    priority = plan["priority"]
    project = plan.get("project", "general")
    
    # Build the forge post
    steps_text = "\n".join(f"  {s['step']}. **{s['action']}** — {s['desc']}" for s in plan["steps"])
    criteria_text = "\n".join(f"  ✓ {c}" for c in plan["success_criteria"])
    
    message = (
        f"⚡ **Auto-Dispatched from Dream Garden**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌸 **Dream:** {title}\n"
        f"📋 **Task ID:** `{plan['task_id']}`\n"
        f"🎯 **Type:** {plan['action']} | **Priority:** {priority}\n"
        f"📂 **Project:** {project or 'unassigned'}\n\n"
        f"**Essence:**\n> {dream_data.get('essence', '')[:300]}\n\n"
        f"**Execution Plan:**\n{steps_text}\n\n"
        f"**Success Criteria:**\n{criteria_text}\n\n"
        f"**Strength:** {dream_data.get('confidence', dream_data.get('strength', '?'))}\n"
        f"**Evolutions:** {dream_data.get('evolution_count', '?')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    return {"channel": "forge", "message": message, "thread_name": f"🌸 {title[:80]}"}


def dispatch_to_research(plan: dict, dream_data: dict) -> dict:
    """Dispatch a research task to #research."""
    message = (
        f"🔬 **Dream → Research Auto-Dispatch**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌸 **Dream:** {plan['title']}\n"
        f"📋 **Task ID:** `{plan['task_id']}`\n\n"
        f"> {dream_data.get('essence', '')[:400]}\n\n"
        f"**Research Scope:**\n"
        f"  Tags: {', '.join(dream_data.get('tags', [])[:10])}\n"
        f"  Depth: {'deep' if dream_data.get('confidence', 0) > 0.9 else 'standard'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return {"channel": "research", "message": message}


def dispatch_to_workshop(plan: dict, dream_data: dict) -> dict:
    """Dispatch a creative task to #workshop."""
    message = (
        f"🎨 **Dream → Creative Workshop**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌸 **Dream:** {plan['title']}\n"
        f"📋 **Task ID:** `{plan['task_id']}`\n\n"
        f"> {dream_data.get('essence', '')[:400]}\n\n"
        f"**Exploration Path:**\n"
        f"  Suggested TIE techniques: G01 (Brainstorm), G11 (Perspective Shift), R04 (Refine)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return {"channel": "workshop", "message": message}


def dispatch_to_content(plan: dict, dream_data: dict) -> dict:
    """Dispatch a content task to the generation queue."""
    message = (
        f"📝 **Dream → Content Pipeline**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌸 **Dream:** {plan['title']}\n"
        f"📋 **Task ID:** `{plan['task_id']}`\n\n"
        f"> {dream_data.get('essence', '')[:400]}\n\n"
        f"**Content Plan:**\n"
        + "\n".join(f"  {s['step']}. {s['desc']}" for s in plan["steps"])
        + f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return {"channel": "bridge", "message": message}


def dispatch_to_business(plan: dict, dream_data: dict) -> dict:
    """Dispatch a business action."""
    message = (
        f"💼 **Dream → Business Action**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌸 **Dream:** {plan['title']}\n"
        f"📋 **Task ID:** `{plan['task_id']}`\n"
        f"📂 **Project:** {plan.get('project', 'general')}\n\n"
        f"> {dream_data.get('essence', '')[:400]}\n\n"
        f"**Action Items:**\n"
        + "\n".join(f"  {s['step']}. {s['desc']}" for s in plan["steps"])
        + f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return {"channel": "bridge", "message": message}


# Route map
DISPATCHERS = {
    DreamAction.CODE: dispatch_to_forge,
    DreamAction.INFRA: dispatch_to_forge,
    DreamAction.RESEARCH: dispatch_to_research,
    DreamAction.CREATIVE: dispatch_to_workshop,
    DreamAction.CONTENT: dispatch_to_content,
    DreamAction.BUSINESS: dispatch_to_business,
    DreamAction.HYBRID: dispatch_to_forge,  # Default hybrid to forge
}


# ─── Core Dispatch Logic ────────────────────────────────────────────

def load_dispatch_state() -> dict:
    """Load auto-dispatch state."""
    if DISPATCH_STATE_FILE.exists():
        try:
            with open(DISPATCH_STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "dispatched_dreams": {},  # dream_id -> dispatch record
        "total_dispatches": 0,
        "last_run": None,
    }


def save_dispatch_state(state: dict):
    """Save auto-dispatch state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(DISPATCH_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def log_dispatch(record: dict):
    """Append to dispatch log."""
    DISPATCH_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log = []
    if DISPATCH_LOG_FILE.exists():
        try:
            with open(DISPATCH_LOG_FILE) as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = []
    log.append(record)
    # Keep last 200
    log = log[-200:]
    with open(DISPATCH_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, default=str)


def process_bloomed_dreams(dry_run: bool = False) -> dict:
    """Main entry point: scan idea vault for undispatched blooms, classify and dispatch.
    
    Returns stats dict.
    """
    state = load_dispatch_state()
    dispatched_ids = set(state.get("dispatched_dreams", {}).keys())
    
    # Scan idea vault for bloomed dreams
    if not IDEA_VAULT_DIR.exists():
        print("[AutoDispatch] No idea vault found")
        return {"scanned": 0, "dispatched": 0}
    
    ideas = []
    for f in IDEA_VAULT_DIR.glob("*.json"):
        try:
            with open(f) as fh:
                idea = json.load(fh)
                ideas.append(idea)
        except (json.JSONDecodeError, IOError):
            continue
    
    # Filter: only inbox status, not already dispatched
    pending = [
        i for i in ideas
        if i.get("status") == "inbox"
        and i.get("id") not in dispatched_ids
        and i.get("confidence", i.get("strength", 0)) >= 0.8
    ]
    
    if not pending:
        print(f"[AutoDispatch] {len(ideas)} ideas scanned, 0 pending dispatch")
        return {"scanned": len(ideas), "dispatched": 0}
    
    print(f"[AutoDispatch] {len(pending)} bloomed dreams ready for dispatch")
    
    dispatched = []
    for dream_data in pending:
        dream_id = dream_data.get("id", "unknown")
        print(f"  Processing: {dream_data.get('title', dream_id)}")
        
        # 1. Classify
        classification = classify_dream(dream_data)
        print(f"    → {classification['action'].value} (confidence: {classification['confidence']:.2f})")
        
        # 2. Generate execution plan
        plan = generate_execution_plan(dream_data, classification)
        
        # 3. Dispatch to appropriate surface
        dispatcher = DISPATCHERS.get(classification["action"], dispatch_to_forge)
        dispatch_msg = dispatcher(plan, dream_data)
        
        if dry_run:
            print(f"    [DRY RUN] Would dispatch to #{dispatch_msg['channel']}")
            print(f"    Message preview: {dispatch_msg['message'][:120]}...")
        else:
            # Actually send via clawdbot message tool (write instruction file)
            _queue_discord_dispatch(dispatch_msg, plan)
            
            # Update idea vault status
            _update_idea_status(dream_id, "dispatched", plan["task_id"])
        
        # Record dispatch
        record = {
            "dream_id": dream_id,
            "title": dream_data.get("title"),
            "action": classification["action"].value if isinstance(classification["action"], DreamAction) else classification["action"],
            "priority": classification["priority"].value if isinstance(classification["priority"], DispatchPriority) else classification["priority"],
            "project": classification.get("project"),
            "task_id": plan["task_id"],
            "channel": dispatch_msg["channel"],
            "dispatched_at": datetime.utcnow().isoformat() + "Z",
            "confidence": classification["confidence"],
            "reasoning": classification["reasoning"],
        }
        
        state["dispatched_dreams"][dream_id] = record
        state["total_dispatches"] = state.get("total_dispatches", 0) + 1
        dispatched.append(record)
        
        log_dispatch(record)
    
    state["last_run"] = datetime.utcnow().isoformat() + "Z"
    
    if not dry_run:
        save_dispatch_state(state)
    
    print(f"[AutoDispatch] {len(dispatched)}/{len(pending)} dispatched")
    return {"scanned": len(ideas), "dispatched": len(dispatched), "records": dispatched}


def _queue_discord_dispatch(dispatch_msg: dict, plan: dict):
    """Queue a Discord message for delivery via Clawdbot.
    
    Writes to a dispatch queue file that gets picked up by the
    bloom-dispatcher or a cron hook.
    """
    queue_file = STATE_DIR / "discord-dispatch-queue.json"
    queue = []
    if queue_file.exists():
        try:
            with open(queue_file) as f:
                queue = json.load(f)
        except (json.JSONDecodeError, IOError):
            queue = []
    
    queue.append({
        "channel_id": CHANNELS.get(dispatch_msg["channel"], dispatch_msg["channel"]),
        "channel_name": dispatch_msg["channel"],
        "message": dispatch_msg["message"],
        "thread_name": dispatch_msg.get("thread_name"),
        "task_id": plan["task_id"],
        "queued_at": datetime.utcnow().isoformat() + "Z",
        "delivered": False,
    })
    
    with open(queue_file, "w") as f:
        json.dump(queue, f, indent=2)


def _update_idea_status(dream_id: str, new_status: str, task_id: str):
    """Update the idea vault entry status."""
    idea_file = IDEA_VAULT_DIR / f"{dream_id}.json"
    if not idea_file.exists():
        return
    
    try:
        with open(idea_file) as f:
            idea = json.load(f)
        idea["status"] = new_status
        idea["dispatch_task_id"] = task_id
        idea["dispatched_at"] = datetime.utcnow().isoformat() + "Z"
        with open(idea_file, "w") as f:
            json.dump(idea, f, indent=2)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [Warning] Failed to update idea status: {e}")


# ─── Feedback Loop (Bidirectional) ──────────────────────────────────

def record_execution_feedback(task_id: str, result: dict):
    """Record execution results back to the dream for bidirectional feedback.
    
    Called when a dispatched task completes (success or failure).
    Feeds results back into the dream engine for learning.
    """
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    
    feedback = {
        "task_id": task_id,
        "result": result,
        "recorded_at": datetime.utcnow().isoformat() + "Z",
    }
    
    feedback_file = FEEDBACK_DIR / f"{task_id}.json"
    with open(feedback_file, "w") as f:
        json.dump(feedback, f, indent=2)
    
    # If successful, check if we should spawn daughter dreams
    if result.get("status") == "success":
        learnings = result.get("learnings", [])
        if learnings:
            _spawn_daughter_dreams(task_id, learnings)


def _spawn_daughter_dreams(parent_task_id: str, learnings: list):
    """Spawn new dream seeds from execution learnings.
    
    This is the bidirectional part — what we learned from executing
    a dream feeds back into new seeds for the garden.
    """
    from .models import Dream
    from .evolve import load_state, save_state
    
    state = load_state()
    
    for i, learning in enumerate(learnings[:3]):  # Cap at 3 daughter dreams
        seed = Dream(
            title=f"Daughter: {learning.get('title', f'Learning #{i+1}')}",
            essence=learning.get("insight", ""),
            context=f"Spawned from execution of task {parent_task_id}",
            tags=learning.get("tags", []) + ["daughter-dream", "execution-feedback"],
            source="auto-dispatch-feedback",
        )
        state.add_dream(seed)
        print(f"  🌰 Daughter dream planted: {seed.title}")
    
    save_state(state)


# ─── CLI ─────────────────────────────────────────────────────────────

def show_status():
    """Show auto-dispatch status."""
    state = load_dispatch_state()
    dispatched = state.get("dispatched_dreams", {})
    
    print("🌸→⚡ Auto-Dispatch Bridge Status")
    print(f"  Total dispatches: {state.get('total_dispatches', 0)}")
    print(f"  Last run: {state.get('last_run', 'never')}")
    print(f"  Dreams tracked: {len(dispatched)}")
    
    if dispatched:
        print("\n  Recent dispatches:")
        recent = sorted(dispatched.values(), key=lambda x: x.get("dispatched_at", ""), reverse=True)[:5]
        for d in recent:
            print(f"    [{d.get('action', '?')}] {d.get('title', '?')[:50]} → #{d.get('channel', '?')} ({d.get('priority', '?')})")


if __name__ == "__main__":
    import sys
    
    if "--status" in sys.argv:
        show_status()
    elif "--dry-run" in sys.argv:
        process_bloomed_dreams(dry_run=True)
    elif "--feedback" in sys.argv:
        # Example: python auto_dispatch.py --feedback <task_id> <status>
        idx = sys.argv.index("--feedback")
        if len(sys.argv) > idx + 2:
            record_execution_feedback(sys.argv[idx + 1], {"status": sys.argv[idx + 2]})
    else:
        process_bloomed_dreams()
