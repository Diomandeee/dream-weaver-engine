"""Main evolution cycle logic."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Dream, GardenState, DreamStage
from .together_client import KimiClient
from .discord import DiscordNotifier


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
) -> dict:
    """Run a single evolution cycle."""
    
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
    
    # Get dreams ready for evolution
    dreams_to_evolve = state.get_dreams_for_evolution(max_dreams)
    
    if not dreams_to_evolve:
        print("No dreams ready for evolution.")
        return {"evolutions": [], "blooms": []}
    
    print(f"Evolving {len(dreams_to_evolve)} dreams...")
    
    # Initialize clients
    kimi = KimiClient()
    discord = DiscordNotifier()
    
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
        
        # Check for bloom
        if result.get("bloom_ready") and dream.stage == DreamStage.BLOOM:
            print(f"  🌸 BLOOM: {dream.title}")
            announcement = kimi.generate_bloom_announcement(dream.to_prompt_context())
            blooms.append({
                "dream": dream,
                "announcement": announcement
            })
            
            if not dry_run:
                discord.announce_bloom(dream.title, dream.essence, announcement)
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
    
    print(f"✅ Evolution complete: {len(evolutions)} evolved, {len(blooms)} bloomed")
    
    return {
        "evolutions": evolutions,
        "blooms": blooms,
        "total_dreams": len(state.dreams),
    }


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    result = run_evolution_cycle(dry_run=dry_run)
    print(json.dumps(result, indent=2, default=str))
