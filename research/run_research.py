"""
Research Runner — Entry point for the research pipeline.

Called by GitHub Actions after evolution cycles or on manual trigger.
Can also run standalone for specific dreams.

Usage:
  python -m research.run_research                       # Auto-research dreams that need it
  python -m research.run_research --dream-id <id>       # Research specific dream
  python -m research.run_research --all-blooms           # Research all bloomed dreams
  python -m research.run_research --depth heavy          # Force depth level
  python -m research.run_research --dry-run              # Preview what would be researched
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dream_engine.models import GardenState, DreamStage
from research.engine import ResearchEngine, ResearchDepth, ResearchTrigger
from research.discord_reporter import ResearchDiscordReporter


STATE_FILE = Path("state/dreams.json")


def load_garden_state() -> GardenState:
    """Load garden state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return GardenState(**json.load(f))
    return GardenState()


def run_research_cycle(
    dream_id: str = None,
    depth_override: str = None,
    all_blooms: bool = False,
    dry_run: bool = False,
    trigger: str = "evolution",
) -> dict:
    """
    Run research on dreams that need it.
    
    Returns summary of research performed.
    """
    print("🔬 Starting research cycle...")
    
    # Load state
    state = load_garden_state()
    
    if not state.dreams:
        print("No dreams in garden.")
        return {"researched": [], "skipped": [], "seeds_planted": 0}
    
    # Initialize engines
    try:
        research = ResearchEngine()
    except ValueError as e:
        print(f"❌ Cannot start research engine: {e}")
        print("  Ensure BRAVE_API_KEY and TOGETHER_API_KEY are set.")
        return {"error": str(e)}
    
    discord = ResearchDiscordReporter()
    
    # Determine which dreams to research
    dreams_to_research = []
    
    if dream_id:
        # Specific dream
        if dream_id in state.dreams:
            dream = state.dreams[dream_id]
            depth = ResearchDepth(depth_override) if depth_override else ResearchDepth.HEAVY
            dreams_to_research.append((dream, depth, ResearchTrigger.MANUAL))
        else:
            print(f"Dream {dream_id} not found.")
            return {"error": f"Dream {dream_id} not found"}
    
    elif all_blooms:
        # All bloomed dreams
        depth = ResearchDepth(depth_override) if depth_override else ResearchDepth.HEAVY
        for dream in state.dreams.values():
            if dream.stage == DreamStage.BLOOM:
                dreams_to_research.append((dream, depth, ResearchTrigger.BLOOM))
    
    else:
        # Auto-detect: research dreams that pass the threshold
        for dream in state.dreams.values():
            if dream.stage == DreamStage.ARCHIVED:
                continue
            
            should, depth = research.should_research(
                dream_id=dream.id,
                dream_strength=dream.strength,
                trigger=ResearchTrigger(trigger),
                stage=dream.stage.value,
            )
            
            if should:
                if depth_override:
                    depth = ResearchDepth(depth_override)
                dreams_to_research.append((dream, depth, ResearchTrigger(trigger)))
    
    if not dreams_to_research:
        print("No dreams need research right now.")
        return {"researched": [], "skipped": [], "seeds_planted": 0}
    
    print(f"Researching {len(dreams_to_research)} dreams...")
    
    if dry_run:
        print("\n--- DRY RUN ---")
        for dream, depth, trig in dreams_to_research:
            print(f"  Would research: {dream.title} [{depth.value}] (trigger: {trig.value})")
        return {
            "dry_run": True,
            "would_research": [
                {"id": d.id, "title": d.title, "depth": dep.value, "trigger": t.value}
                for d, dep, t in dreams_to_research
            ]
        }
    
    # Execute research
    researched = []
    total_seeds_planted = 0
    
    for dream, depth, trig in dreams_to_research:
        try:
            # Get connections for context
            connections = [
                {"title": d.title, "essence": d.essence, "tags": d.tags}
                for d in state.get_potential_connections(dream, max_count=3)
            ]
            
            # Run research
            report = research.research_dream(
                dream_id=dream.id,
                dream_title=dream.title,
                dream_essence=dream.essence,
                dream_context=dream.context,
                dream_tags=dream.tags,
                dream_strength=dream.strength,
                connections=connections,
                depth=depth,
                trigger=trig,
            )
            
            # Post to Discord
            discord.post_research_report(
                dream_title=dream.title,
                report=report,
                depth=depth.value,
                dream_id=dream.id,
            )
            
            # Plant new seeds back into the garden
            new_seeds = report.get("new_seeds", [])
            if new_seeds:
                planted = research.plant_research_seeds(new_seeds, dream.id)
                total_seeds_planted += len(planted)
            
            # Apply recommended strength delta from research
            rec_delta = report.get("recommended_strength_delta", 0)
            if rec_delta > 0 and rec_delta <= 0.2:
                dream.strength = min(1.0, dream.strength + rec_delta)
                dream.update_stage()
            
            # Add recommended tags
            for tag in report.get("recommended_tags", []):
                if tag not in dream.tags:
                    dream.tags.append(tag)
            
            researched.append({
                "id": dream.id,
                "title": dream.title,
                "depth": depth.value,
                "feasibility": report.get("feasibility", {}),
                "seeds": len(new_seeds),
                "sources": len(report.get("sources", [])),
                "report_path": report.get("report_path", ""),
            })
            
        except Exception as e:
            print(f"  ❌ Failed to research {dream.title}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save updated state (with strength/tag modifications from research)
    from dream_engine.evolve import save_state
    save_state(state)
    
    # Post research cycle summary
    discord.post_research_summary(researched)
    
    print(f"\n✅ Research cycle complete:")
    print(f"   Dreams researched: {len(researched)}")
    print(f"   Seeds planted: {total_seeds_planted}")
    
    return {
        "researched": researched,
        "seeds_planted": total_seeds_planted,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dream Research Pipeline")
    parser.add_argument("--dream-id", help="Research specific dream by ID")
    parser.add_argument("--depth", choices=["scout", "deep", "heavy"], help="Force research depth")
    parser.add_argument("--all-blooms", action="store_true", help="Research all bloomed dreams")
    parser.add_argument("--trigger", default="evolution", 
                       choices=["evolution", "bloom", "stage_change", "manual", "seed", "synthesis"],
                       help="Research trigger type")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    
    args = parser.parse_args()
    
    result = run_research_cycle(
        dream_id=args.dream_id,
        depth_override=args.depth,
        all_blooms=args.all_blooms,
        dry_run=args.dry_run,
        trigger=args.trigger,
    )
    
    print(json.dumps(result, indent=2, default=str))
