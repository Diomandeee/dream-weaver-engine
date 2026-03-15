"""Main evolution cycle logic."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Dream, GardenState, DreamStage
from .together_client import KimiClient
from .discord import DiscordNotifier
from .notifier import Notifier
from .idea_bridge import bridge_to_idea_vault
from .garden_viz import generate_garden_html
from .quality_gate import validate_evolution
from .action_dispatcher import dispatch_bloomed_dreams
from .supabase_sync import sync_garden_to_supabase


STATE_FILE = Path("state/dreams.json")
DREAMS_DIR = Path("dreams")


def load_state() -> GardenState:
    """Load garden state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            data = json.load(f)
            return GardenState(**data)
    return GardenState()


def save_state(state: GardenState):
    """Save garden state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state.model_dump(mode="json"), f, indent=2, default=str)


def load_dream_files() -> list[Dream]:
    """Load dreams from individual markdown files."""
    dreams = []
    if not DREAMS_DIR.exists():
        DREAMS_DIR.mkdir(parents=True)
        return dreams
    
    for file in DREAMS_DIR.glob("*.md"):
        try:
            content = file.read_text()
            # Parse frontmatter-style dream file
            dream = parse_dream_file(content, file.stem)
            if dream:
                dreams.append(dream)
        except Exception as e:
            print(f"Failed to parse {file}: {e}")
    
    return dreams


def parse_dream_file(content: str, file_id: str) -> Optional[Dream]:
    """Parse a dream from markdown content."""
    lines = content.strip().split("\n")
    
    title = ""
    essence = ""
    context = ""
    tags = []
    
    current_section = None
    
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## Essence"):
            current_section = "essence"
        elif line.startswith("## Context"):
            current_section = "context"
        elif line.startswith("## Tags"):
            current_section = "tags"
        elif line.startswith("## "):
            current_section = None
        elif current_section == "essence":
            essence += line + "\n"
        elif current_section == "context":
            context += line + "\n"
        elif current_section == "tags" and line.strip():
            tags.extend([t.strip() for t in line.split(",") if t.strip()])
    
    if title and essence:
        return Dream(
            id=file_id,
            title=title,
            essence=essence.strip(),
            context=context.strip(),
            tags=tags,
            source="file"
        )
    return None


def sync_dreams_to_state(state: GardenState, file_dreams: list[Dream]):
    """Sync dreams from files into state, preserving evolution data."""
    for dream in file_dreams:
        if dream.id in state.dreams:
            # Update content but preserve evolution data
            existing = state.dreams[dream.id]
            existing.title = dream.title
            existing.essence = dream.essence
            existing.context = dream.context
            existing.tags = list(set(existing.tags + dream.tags))
        else:
            # New dream
            state.add_dream(dream)


def run_evolution_cycle(
    max_dreams: int = 5,
    dry_run: bool = False,
    use_evo_cube: bool = True,
) -> dict:
    """Run a single evolution cycle.
    
    Args:
        max_dreams: Max dreams to evolve per cycle
        dry_run: If True, don't save state or post to Discord
        use_evo_cube: If True, use multi-model Evo Cube architecture (Gemini + MiniMax + Kimi)
                      If False, use legacy single-model Kimi path
    """
    
    print("🌱 Starting evolution cycle...")
    
    # Load state
    state = load_state()
    
    # Sync dreams from files
    file_dreams = load_dream_files()
    sync_dreams_to_state(state, file_dreams)
    
    # HTDS integration: inject high-density sessions as seed candidates
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "synthesis"))
        from htds_integration import get_dream_seeds_from_htds
        htds_seeds = get_dream_seeds_from_htds(limit=5)
        if htds_seeds and not htds_seeds[0].get("error"):
            print(f"  📊 HTDS: {len(htds_seeds)} high-density sessions available for seeding")
            state.htds_seed_candidates = htds_seeds  # Store for cross-pollination context
    except Exception as e:
        print(f"  HTDS unavailable: {e}")
    
    # === EVO CUBE PATH (multi-model, free) ===
    if use_evo_cube:
        return _run_evo_cube_cycle(state, max_dreams, dry_run)
    
    # === LEGACY PATH (single-model Kimi) ===
    # Get dreams ready for evolution
    dreams_to_evolve = state.get_dreams_for_evolution(max_dreams)
    
    if not dreams_to_evolve:
        print("No dreams ready for evolution.")
        return {"evolutions": [], "blooms": []}
    
    print(f"Evolving {len(dreams_to_evolve)} dreams...")
    
    # Initialize clients
    kimi = KimiClient()
    discord = Notifier()
    
    evolutions = []
    blooms = []
    
    for dream in dreams_to_evolve:
        print(f"  Evolving: {dream.title}")
        
        # Get cross-pollination context
        connections = state.get_potential_connections(dream)
        garden_context = "\n\n".join([d.to_prompt_context() for d in connections])
        
        # Call Kimi-K2 for evolution
        result = kimi.evolve_dream(
            dream_context=dream.to_prompt_context(),
            garden_context=garden_context
        )
        
        # Quality gate — reject bad proposals before mutating the dream
        passed, reason = validate_evolution(result)
        if not passed:
            print(f"  ⛔ Gate rejected '{dream.title}': {reason}")
            continue

        # Apply evolution
        old_strength = dream.strength
        dream.strength = min(1.0, dream.strength + result.get("strength_delta", 0.05))
        dream.evolution_count += 1
        dream.last_evolved = datetime.utcnow()
        dream.evolution_notes.append(result.get("insight", "")[:500])
        
        # Add new connections
        for tag in result.get("new_connections", []):
            if tag not in dream.tags:
                dream.tags.append(tag)
        
        # Update stage
        old_stage = dream.stage
        dream.update_stage()
        
        evolution_record = {
            "dream_id": dream.id,
            "dream_title": dream.title,
            "old_strength": old_strength,
            "new_strength": dream.strength,
            "strength_delta": dream.strength - old_strength,
            "insight": result.get("insight", ""),
            "stage_change": old_stage != dream.stage,
        }
        evolutions.append(evolution_record)
        
        # Notify stage changes (all channels)
        if old_stage != dream.stage and not dry_run:
            discord.announce_stage_change(
                dream.title,
                old_stage.value if hasattr(old_stage, 'value') else old_stage,
                dream.stage.value if hasattr(dream.stage, 'value') else dream.stage,
                dream.strength,
            )

        # Notify evolution milestones (every 10)
        if dream.evolution_count > 0 and dream.evolution_count % 10 == 0 and not dry_run:
            discord.announce_evolution_milestone(dream.title, dream.evolution_count, dream.strength)

        # Check for bloom
        if result.get("bloom_ready") and dream.stage == DreamStage.BLOOM:
            print(f"  🌸 BLOOM: {dream.title}")
            announcement = kimi.generate_bloom_announcement(dream.to_prompt_context())
            blooms.append({
                "dream": dream,
                "announcement": announcement
            })
            
            if not dry_run:
                discord.announce_bloom(dream.title, dream.essence, announcement, strength=dream.strength)
                bridge_to_idea_vault(dream)
                state.total_blooms += 1
    
    # Update state
    state.last_evolution = datetime.utcnow()
    state.total_evolutions += len(evolutions)
    
    if not dry_run:
        # Save state
        save_state(state)
        
        # Post evolution summary
        discord.post_evolution_summary(evolutions, len(state.dreams))
        
        # Generate and post journal entry
        if evolutions:
            garden_summary = f"{len(state.dreams)} dreams, {state.total_blooms} blooms total"
            journal_entry = kimi.generate_journal_entry(garden_summary, evolutions)
            discord.post_journal_entry(journal_entry)
        
        # Regenerate visual garden
        try:
            generate_garden_html(state)
        except Exception as e:
            print(f"  [GardenViz] HTML generation skipped: {e}")
    
    # === RESEARCH PIPELINE INTEGRATION ===
    # Trigger research for dreams that crossed thresholds
    if not dry_run and evolutions:
        try:
            from research.engine import ResearchEngine, ResearchTrigger
            from research.discord_reporter import ResearchDiscordReporter
            
            research_engine = ResearchEngine()
            discord_research = ResearchDiscordReporter()
            research_results = []
            
            for evo in evolutions:
                dream = state.dreams.get(evo["dream_id"])
                if not dream:
                    continue
                
                # Determine trigger type
                trigger = ResearchTrigger.BLOOM if evo.get("stage_change") and dream.stage == DreamStage.BLOOM else ResearchTrigger.EVOLUTION
                if evo.get("stage_change"):
                    trigger = ResearchTrigger.STAGE_CHANGE
                
                should, depth = research_engine.should_research(
                    dream_id=dream.id,
                    dream_strength=dream.strength,
                    trigger=trigger,
                    stage=dream.stage.value,
                )
                
                if should:
                    connections_ctx = [
                        {"title": d.title, "essence": d.essence, "tags": d.tags}
                        for d in state.get_potential_connections(dream, max_count=3)
                    ]
                    
                    report = research_engine.research_dream(
                        dream_id=dream.id,
                        dream_title=dream.title,
                        dream_essence=dream.essence,
                        dream_context=dream.context,
                        dream_tags=dream.tags,
                        dream_strength=dream.strength,
                        connections=connections_ctx,
                        depth=depth,
                        trigger=trigger,
                    )
                    
                    # Post to Discord
                    discord_research.post_research_report(
                        dream_title=dream.title,
                        report=report,
                        depth=depth.value,
                        dream_id=dream.id,
                    )
                    
                    # Plant seeds back
                    new_seeds = report.get("new_seeds", [])
                    if new_seeds:
                        research_engine.plant_research_seeds(new_seeds, dream.id)
                    
                    # Apply research-recommended strength boost
                    rec_delta = report.get("recommended_strength_delta", 0)
                    if 0 < rec_delta <= 0.2:
                        dream.strength = min(1.0, dream.strength + rec_delta)
                        dream.update_stage()
                    
                    research_results.append({
                        "dream_id": dream.id,
                        "depth": depth.value,
                        "seeds": len(new_seeds),
                    })
            
            if research_results:
                print(f"  🔬 Research: {len(research_results)} dreams researched, "
                      f"{sum(r['seeds'] for r in research_results)} seeds planted")
                # Save state again with research-modified strength
                save_state(state)
                
        except Exception as e:
            print(f"  [Research] Pipeline skipped: {e}")
    # === END RESEARCH PIPELINE ===

    # === ACTION DISPATCH — convert blooms to executable tasks ===
    dispatched = []
    if not dry_run:
        try:
            dispatched = dispatch_bloomed_dreams(state, max_dispatch=3, min_strength=0.75)
            if dispatched:
                print(f"  🚀 Action Dispatch: {len(dispatched)} dreams → mac_tasks queue")
                # Update dream stages for dispatched dreams
                for d_result in dispatched:
                    dream_id = d_result.get("media_context", {})
                    if isinstance(dream_id, str):
                        import json as _json
                        dream_id = _json.loads(dream_id)
                    did = dream_id.get("dream_id") if isinstance(dream_id, dict) else None
                    if did and did in state.dreams:
                        state.dreams[did].dispatched_task_id = d_result.get("task_id")
                        state.dreams[did].dispatched_at = datetime.utcnow()
                save_state(state)
        except Exception as e:
            print(f"  [ActionDispatch] Skipped: {e}")
    # === END ACTION DISPATCH ===

    # === SUPABASE SYNC ===
    if not dry_run:
        try:
            sync_result = sync_garden_to_supabase(state)
            if sync_result.get("synced"):
                print(f"  ☁️ Supabase: {sync_result['synced']} dreams synced")
        except Exception as e:
            print(f"  [SupaSync] Skipped: {e}")

    print(f"✅ Evolution complete: {len(evolutions)} evolved, {len(blooms)} bloomed, {len(dispatched)} dispatched")

    return {
        "evolutions": evolutions,
        "blooms": blooms,
        "dispatched": dispatched,
        "total_dreams": len(state.dreams),
    }


def _run_evo_cube_cycle(state: GardenState, max_dreams: int, dry_run: bool) -> dict:
    """Run evolution using the Evo Cube multi-model architecture.
    
    Model routing:
    - Scoring/ranking → MiniMax local (free, fast)
    - Creative evolution → Gemini CLI (free, medium)
    - Deep reasoning → Kimi-K2 Together (paid, only for high-strength dreams)
    """
    from .evo_cube import EvoCube
    
    print("  🧊 Using Evo Cube multi-model architecture")
    
    # Check if Kimi depth axis is available
    enable_depth = bool(os.environ.get("TOGETHER_API_KEY"))
    if enable_depth:
        print("  ✅ Depth axis (Kimi-K2) available for high-strength dreams")
    else:
        print("  ⚠️ Depth axis disabled (no TOGETHER_API_KEY) — Gemini handles all synthesis")
    
    cube = EvoCube(enable_depth=enable_depth)
    discord = Notifier()
    
    # Run full cube cycle
    result = cube.full_cycle(state, max_dreams=max_dreams)
    
    evolutions = result.get("evolutions", [])
    blooms = result.get("blooms", [])
    cross_pollinations = result.get("cross_pollinations", [])
    
    if not evolutions:
        print("No dreams ready for evolution.")
        return result
    
    # Update state
    state.last_evolution = datetime.utcnow()
    state.total_evolutions += len(evolutions)
    
    # Handle blooms
    for bloom in blooms:
        state.total_blooms += 1
        if not dry_run:
            dream = state.dreams.get(bloom["dream_id"])
            if dream:
                discord.announce_bloom(dream.title, dream.essence, bloom["announcement"], strength=dream.strength)
                bridge_to_idea_vault(dream)
    
    if not dry_run:
        # Save state
        save_state(state)
        
        # Post evolution summary
        discord.post_evolution_summary(evolutions, len(state.dreams))
        
        # Generate and post journal entry
        if evolutions:
            garden_summary = f"{len(state.dreams)} dreams, {state.total_blooms} blooms total"
            journal_entry = cube.generate_journal_entry(garden_summary, evolutions)
            discord.post_journal_entry(journal_entry)
        
        # Regenerate visual garden
        try:
            generate_garden_html(state)
        except Exception as e:
            print(f"  [GardenViz] HTML generation skipped: {e}")
    
    # === RESEARCH PIPELINE (same as legacy) ===
    if not dry_run and evolutions:
        try:
            from research.engine import ResearchEngine, ResearchTrigger
            from research.discord_reporter import ResearchDiscordReporter
            
            research_engine = ResearchEngine()
            discord_research = ResearchDiscordReporter()
            
            for evo in evolutions:
                dream = state.dreams.get(evo["dream_id"])
                if not dream:
                    continue
                
                trigger = ResearchTrigger.BLOOM if evo.get("stage_change") and dream.stage == DreamStage.BLOOM else ResearchTrigger.EVOLUTION
                if evo.get("stage_change"):
                    trigger = ResearchTrigger.STAGE_CHANGE
                
                should, depth = research_engine.should_research(
                    dream_id=dream.id, dream_strength=dream.strength,
                    trigger=trigger, stage=dream.stage.value,
                )
                
                if should:
                    connections_ctx = [
                        {"title": d.title, "essence": d.essence, "tags": d.tags}
                        for d in state.get_potential_connections(dream, max_count=3)
                    ]
                    report = research_engine.research_dream(
                        dream_id=dream.id, dream_title=dream.title,
                        dream_essence=dream.essence, dream_context=dream.context,
                        dream_tags=dream.tags, dream_strength=dream.strength,
                        connections=connections_ctx, depth=depth, trigger=trigger,
                    )
                    discord_research.post_research_report(
                        dream_title=dream.title, report=report,
                        depth=depth.value, dream_id=dream.id,
                    )
                    new_seeds = report.get("new_seeds", [])
                    if new_seeds:
                        research_engine.plant_research_seeds(new_seeds, dream.id)
                    rec_delta = report.get("recommended_strength_delta", 0)
                    if 0 < rec_delta <= 0.2:
                        dream.strength = min(1.0, dream.strength + rec_delta)
                        dream.update_stage()
            
            save_state(state)
        except Exception as e:
            print(f"  [Research] Pipeline skipped: {e}")

    # === ACTION DISPATCH — convert blooms to executable tasks ===
    dispatched = []
    if not dry_run:
        try:
            dispatched = dispatch_bloomed_dreams(state, max_dispatch=3, min_strength=0.75)
            if dispatched:
                print(f"  🚀 Action Dispatch: {len(dispatched)} dreams → mac_tasks queue")
                for d_result in dispatched:
                    dream_id = d_result.get("media_context", {})
                    if isinstance(dream_id, str):
                        dream_id = json.loads(dream_id)
                    did = dream_id.get("dream_id") if isinstance(dream_id, dict) else None
                    if did and did in state.dreams:
                        state.dreams[did].dispatched_task_id = d_result.get("task_id")
                        state.dreams[did].dispatched_at = datetime.utcnow()
                save_state(state)
        except Exception as e:
            print(f"  [ActionDispatch] Skipped: {e}")
    # === END ACTION DISPATCH ===

    result["dispatched"] = dispatched

    # === SUPABASE SYNC ===
    if not dry_run:
        try:
            sync_result = sync_garden_to_supabase(state)
            if sync_result.get("synced"):
                print(f"  ☁️ Supabase: {sync_result['synced']} dreams synced")
        except Exception as e:
            print(f"  [SupaSync] Skipped: {e}")

    print(f"✅ Evo Cube cycle complete: {len(evolutions)} evolved, {len(blooms)} bloomed, {len(dispatched)} dispatched")

    return result


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    legacy = "--legacy" in sys.argv
    result = run_evolution_cycle(dry_run=dry_run, use_evo_cube=not legacy)
    print(json.dumps(result, indent=2, default=str))
