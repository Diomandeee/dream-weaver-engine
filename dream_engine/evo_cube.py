"""
Evo Cube — Multi-Model Dream Evolution Architecture

The cube has 3 dimensions, each powered by a different model:

  AXIS 1: SCORING (MiniMax/Llama local — free, fast)
    → Connection strength scoring
    → Evolution priority ranking
    → Tag overlap analysis

  AXIS 2: SYNTHESIS (Gemini CLI — free, creative)
    → Dream evolution narratives
    → Cross-pollination insights
    → Bloom announcements

  AXIS 3: DEPTH (Kimi-K2 via Together — deep reasoning, paid)
    → Deep philosophical connections
    → Research pipeline
    → Journal synthesis

The cube routes each task to the optimal model:
- Cheap/fast scoring → local MiniMax
- Creative synthesis → Gemini (free CLI)
- Deep reasoning → Kimi-K2 (only when needed)
"""

import json
from datetime import datetime
from typing import Optional
from enum import Enum

from .models import Dream, GardenState, DreamStage
from .quality_gate import validate_evolution


class ModelAxis(Enum):
    """Which axis of the evo cube to use."""
    SCORING = "scoring"      # MiniMax local — fast, free
    SYNTHESIS = "synthesis"   # Gemini CLI — creative, free
    DEPTH = "depth"          # Kimi-K2 — deep, paid


class EvoCube:
    """Multi-model evolution orchestrator.

    Routes tasks to the optimal model based on cost/capability:
    - Scoring/ranking → local model (free, fast)
    - Creative evolution → Gemini CLI (free, medium)
    - Deep reasoning → Kimi-K2 Together (paid, slow)
    """

    def __init__(self, enable_depth: bool = True):
        self._scoring = None
        self._synthesis = None
        self._depth = None
        self.enable_depth = enable_depth
        self.stats = {
            "scoring_calls": 0,
            "synthesis_calls": 0,
            "depth_calls": 0,
            "total_cost": 0.0,  # Only depth axis costs money
        }

    @property
    def scoring(self):
        """Lazy-load MiniMax client."""
        if self._scoring is None:
            from .minimax_client import MiniMaxClient
            self._scoring = MiniMaxClient()
        return self._scoring

    @property
    def synthesis(self):
        """Lazy-load Gemini client."""
        if self._synthesis is None:
            from .gemini_client import GeminiClient
            self._synthesis = GeminiClient()
        return self._synthesis

    @property
    def depth(self):
        """Lazy-load Kimi client (only when needed)."""
        if self._depth is None:
            if not self.enable_depth:
                return None
            try:
                from .together_client import KimiClient
                self._depth = KimiClient()
            except (ValueError, ImportError):
                print("  ⚠️ Kimi-K2 unavailable (no TOGETHER_API_KEY), using Gemini for depth")
                return None
        return self._depth

    def score_connections(self, dream: Dream, candidates: list[Dream]) -> list[tuple[Dream, float]]:
        """Score connection strength between a dream and candidates. Uses local model (free)."""
        self.stats["scoring_calls"] += 1
        scored = []
        for candidate in candidates:
            if candidate.id == dream.id:
                continue
            score = self.scoring.score_connection(
                dream.tags, candidate.tags,
                dream.essence, candidate.essence
            )
            scored.append((candidate, score))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    @staticmethod
    def evolution_weight(dream: Dream, now: Optional[datetime] = None) -> float:
        """Calculate evolution priority weight for a dream.

        weight = (1 - strength) * (1 / (evolution_count + 1)) * recency_penalty

        Seeds (low strength, few evos) naturally rank above blooms
        (high strength, many evos). The recency penalty throttles dreams
        that were evolved recently so the garden stays diverse.
        """
        if now is None:
            now = datetime.utcnow()

        if dream.last_evolved is not None:
            hours_since = (now - dream.last_evolved).total_seconds() / 3600.0
        else:
            hours_since = float("inf")  # Never evolved → max priority

        recency_penalty = min(1.0, hours_since / 6.0)

        return (1 - dream.strength) * (1 / (dream.evolution_count + 1)) * recency_penalty

    def rank_evolution_queue(self, state: GardenState, max_count: int = 5) -> list[Dream]:
        """Rank which dreams should evolve next using evolution_weight (no model call)."""
        now = datetime.utcnow()
        active = [
            d for d in state.dreams.values()
            if d.stage != DreamStage.ARCHIVED
        ]

        if not active:
            return []

        ranked = sorted(active, key=lambda d: self.evolution_weight(d, now), reverse=True)
        return ranked[:max_count]

    def evolve_dream(self, dream: Dream, garden_context: str) -> dict:
        """Evolve a dream. Uses Gemini (free) for creative synthesis."""
        self.stats["synthesis_calls"] += 1
        return self.synthesis.evolve_dream(
            dream_context=dream.to_prompt_context(),
            garden_context=garden_context
        )

    def cross_pollinate(self, dream_a: Dream, dream_b: Dream) -> dict:
        """Find cross-pollination between two dreams. Uses Gemini (free)."""
        self.stats["synthesis_calls"] += 1
        return self.synthesis.cross_pollinate(
            dream_a=dream_a.to_prompt_context(),
            dream_b=dream_b.to_prompt_context()
        )

    def deep_evolve(self, dream: Dream, garden_context: str) -> dict:
        """Deep evolution for high-strength dreams approaching bloom. Uses Kimi-K2 (paid)."""
        if self.depth:
            self.stats["depth_calls"] += 1
            return self.depth.evolve_dream(
                dream_context=dream.to_prompt_context(),
                garden_context=garden_context
            )
        else:
            # Fallback to Gemini
            return self.evolve_dream(dream, garden_context)

    def generate_bloom_announcement(self, dream: Dream) -> str:
        """Generate bloom announcement. Uses Gemini (free)."""
        self.stats["synthesis_calls"] += 1
        return self.synthesis.generate_bloom_announcement(dream.to_prompt_context())

    def generate_journal_entry(self, garden_summary: str, evolutions: list[dict]) -> str:
        """Generate journal entry. Uses depth model if available, else Gemini."""
        if self.depth:
            self.stats["depth_calls"] += 1
            return self.depth.generate_journal_entry(garden_summary, evolutions)
        else:
            self.stats["synthesis_calls"] += 1
            return self.synthesis.generate_journal_entry(garden_summary, evolutions)

    def full_cycle(self, state: GardenState, max_dreams: int = 5) -> dict:
        """Run a full evo cube cycle:

        1. SCORING AXIS: Rank dreams by evolution priority (local, free)
        2. SCORING AXIS: Score cross-connections for each dream (local, free)
        3. SYNTHESIS AXIS: Evolve each dream with Gemini (free)
        4. DEPTH AXIS: Deep evolve high-strength dreams with Kimi (paid, optional)
        5. SYNTHESIS AXIS: Cross-pollinate top-scoring pairs (free)

        Returns evolution results.
        """
        print("  🧊 Evo Cube: multi-model evolution cycle")

        # 1. Rank (local, free)
        print("    📊 Axis 1 (Scoring): Ranking evolution queue...")
        ranked = self.rank_evolution_queue(state, max_count=max_dreams)
        if not ranked:
            return {"evolutions": [], "blooms": [], "cross_pollinations": [], "cube_stats": self.stats}

        print(f"    → {len(ranked)} dreams queued for evolution")

        evolutions = []
        blooms = []
        cross_pollinations = []

        for dream in ranked:
            # 2. Score connections (local, free)
            all_others = [d for d in state.dreams.values() if d.id != dream.id]
            scored_connections = self.score_connections(dream, all_others[:10])
            top_connections = [d for d, score in scored_connections if score > 0.3]
            garden_context = "\n\n".join([d.to_prompt_context() for d in top_connections[:3]])

            # 3. Evolve (Gemini, free) — or deep evolve for high-strength
            use_depth = dream.strength >= 0.7 and self.depth is not None
            if use_depth:
                print(f"    🔬 Axis 3 (Depth): Deep evolving '{dream.title}'")
                result = self.deep_evolve(dream, garden_context)
            else:
                print(f"    ✨ Axis 2 (Synthesis): Evolving '{dream.title}'")
                result = self.evolve_dream(dream, garden_context)

            # Quality gate — reject bad proposals before mutating the dream
            passed, reason = validate_evolution(result)
            if not passed:
                print(f"    ⛔ Gate rejected '{dream.title}': {reason}")
                continue

            # Apply evolution
            old_strength = dream.strength
            old_stage = dream.stage
            dream.strength = min(1.0, dream.strength + result.get("strength_delta", 0.05))
            dream.evolution_count += 1
            dream.last_evolved = datetime.utcnow()
            dream.evolution_notes.append(result.get("insight", "")[:500])

            for tag in result.get("new_connections", []):
                if tag not in dream.tags:
                    dream.tags.append(tag)

            dream.update_stage()

            evolution_record = {
                "dream_id": dream.id,
                "dream_title": dream.title,
                "old_strength": old_strength,
                "new_strength": dream.strength,
                "strength_delta": dream.strength - old_strength,
                "insight": result.get("insight", ""),
                "stage_change": old_stage != dream.stage,
                "model_used": "kimi-k2" if use_depth else "gemini",
            }
            evolutions.append(evolution_record)

            # Check for bloom
            if result.get("bloom_ready") and dream.stage == DreamStage.BLOOM:
                announcement = self.generate_bloom_announcement(dream)
                blooms.append({"dream_id": dream.id, "dream_title": dream.title, "announcement": announcement})

        # 5. Cross-pollinate top pairs (Gemini, free)
        if len(ranked) >= 2:
            # Find the highest-scoring pair
            best_pair = None
            best_score = 0
            for i, d1 in enumerate(ranked):
                for d2 in ranked[i+1:]:
                    all_others = [d for d in state.dreams.values() if d.id != d1.id]
                    for d, score in self.score_connections(d1, [d2]):
                        if score > best_score:
                            best_score = score
                            best_pair = (d1, d2)

            if best_pair and best_score > 0.4:
                print(f"    🔗 Axis 2 (Synthesis): Cross-pollinating '{best_pair[0].title}' × '{best_pair[1].title}'")
                cp_result = self.cross_pollinate(best_pair[0], best_pair[1])
                cross_pollinations.append({
                    "dream_a": best_pair[0].title,
                    "dream_b": best_pair[1].title,
                    "synergy_score": cp_result.get("synergy_score", 0),
                    "connection": cp_result.get("connection", ""),
                    "merged_concept": cp_result.get("merged_concept", ""),
                })

        print(f"    🧊 Cube cycle complete: {len(evolutions)} evolved, {len(blooms)} bloomed, {len(cross_pollinations)} cross-pollinated")
        print(f"    📊 Model usage: scoring={self.stats['scoring_calls']}, synthesis={self.stats['synthesis_calls']}, depth={self.stats['depth_calls']}")

        return {
            "evolutions": evolutions,
            "blooms": blooms,
            "cross_pollinations": cross_pollinations,
            "cube_stats": self.stats,
        }
