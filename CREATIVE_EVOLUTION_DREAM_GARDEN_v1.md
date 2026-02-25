# Dream Garden Multi-Model Evolution Architecture — Evolution³
### Stage 1: Explore → Stage 2: Compound → Stage 3: Master Plan

**Generated:** 2026-02-17
**Method:** Evolution³ — three-stage recursive evoflow
**Topic:** How should we architect the Dream Garden's multi-model evolution system to maximize dream growth quality while minimizing cost?

---

## Current System Snapshot

Before evolving, the facts:

| Metric | Value |
|--------|-------|
| Total dreams | 10 |
| Total evolutions | 239 |
| Total blooms | 90 |
| Stage distribution | 6 seed, 2 germinating, 2 bloom |
| Strength range | 0.10 – 1.00 |
| Average strength | 0.32 |
| Model axes | MiniMax (local/free), Gemini CLI (free), Kimi-K2 (paid) |

**Critical observation:** Two dreams (Cross-Project Pollination, Autonomous Dream Engine) have 117 evolutions each at strength 1.0 (bloom). Six dreams sit at 0.10-0.15 (seed) with 0-1 evolutions. The system over-invested in two ideas and starved eight others. This is the central design problem.

---

## STAGE 1: EXPLORE

*Five divergent parallel paths. Each is an independent direction. No path references another.*

---

### PATH A: The Soil-First Economy — Invert the Evolution Budget

**Concept:** Instead of evolving the "best" dreams, flip the priority: spend 80% of evolution cycles on seeds and germinating dreams, 20% on mature ones. Model the garden as a soil ecosystem where nutrients (compute) should flow to roots, not flowers.

**Why it works:** The current system created a runaway feedback loop — high-strength dreams got more evolutions, which raised their strength further, which gave them even more priority. Seeds starved. This path directly addresses the starvation problem by implementing **evolution budgets** — each dream gets a per-cycle token allocation that's inversely proportional to its current strength.

**Mechanism:**
- Introduce a `evolution_budget` field per dream: `budget = max(0.1, 1.0 - strength)`
- Each cycle, dreams with higher budgets get selected first
- Bloomed dreams (strength=1.0) get budget=0.1 → they still evolve, but rarely
- Fresh seeds (strength=0.1) get budget=0.9 → they dominate the queue
- Budget recharges each cycle, so no dream is permanently starved

**Value angle:** Dramatically increases garden diversity. More unique blooms = more viable ideas reaching the implementation pipeline. The two current blooms prove the engine works; now it needs to work for *all* dreams.

**Risks:**
- Could slow down high-potential dreams that genuinely need sustained attention
- Budget system adds state complexity
- Seeds might still fail to evolve if their essences are too vague for LLMs to work with

---

### PATH B: The Ensemble Jury — Multi-Model Quality Gates

**Concept:** Instead of routing tasks to one model, use all three models as an *evaluation jury*. Each evolution gets scored by a different model than the one that generated it. MiniMax scores Gemini's evolutions. Gemini evaluates Kimi's deep reasoning. Quality gates prevent low-quality evolutions from being applied.

**Why it works:** The current system applies every evolution result blindly — if the model returns JSON, the dream gets evolved. There's no quality filter. An LLM hallucinating a connection scores the same as a genuinely insightful one. The jury model introduces adversarial evaluation.

**Mechanism:**
- Generator model produces evolution proposal (JSON with insight, strength_delta, etc.)
- Evaluator model scores the proposal: relevance (0-1), novelty (0-1), actionability (0-1)
- Composite quality score = weighted average
- Gate: if quality < 0.5, evolution is rejected; if quality 0.5-0.7, strength_delta is halved; if quality > 0.7, full delta applied
- Track quality scores over time to detect model degradation

**Value angle:** Prevents tag explosion (Cross-Project Pollination has 130+ tags, many meaningless). Prevents strength inflation. Every evolution that lands actually matters.

**Risks:**
- Doubles (at least) the number of model calls per evolution
- MiniMax (3B param) may not be sophisticated enough to evaluate Gemini's outputs
- Quality gate thresholds need calibration — too strict kills growth, too loose is pointless

---

### PATH C: The Mycelial Network — Graph-Based Cross-Pollination

**Concept:** Replace the current pair-wise cross-pollination with a proper graph structure. Dreams are nodes. Edges are weighted connections (scored by tag overlap + semantic similarity). Cross-pollination propagates through the graph, not just between pairs. A change in one dream ripples to its neighbors.

**Why it works:** Current cross-pollination picks the "best pair" from the ranked queue and cross-pollinates once per cycle. This is extremely limited — with 10 dreams, there are 45 possible pairs but only 1 gets pollinated. The graph model enables *cascade pollination* where evolving dream A automatically sends signals to dreams B and C via their edge weights.

**Mechanism:**
- Build adjacency matrix from connection scores (MiniMax scoring, already exists)
- After evolving dream A, identify all edges with weight > threshold
- For each connected dream B: inject A's evolution insight as context in B's next evolution
- Track pollination history to avoid circular reinforcement
- Implement "pollination decay" — connection strength reduces over time if not reinforced by new shared tags or insights

**Value angle:** Makes the garden genuinely interconnected. Currently "connections" are just stored IDs that don't affect anything. This makes them functional — ideas actually influence each other.

**Risks:**
- Cascade effects could amplify noise (bad evolution → bad pollination → bad cascade)
- Graph computation adds O(n²) scoring calls per cycle
- Small garden (10 dreams) may not benefit — the power comes at 50+ dreams

---

### PATH D: The Seasonal Rhythm — Time-Aware Evolution Cycles

**Concept:** Not all dreams should evolve at the same pace or in the same way. Introduce "seasons" — distinct cycle modes that rotate based on garden health metrics. Spring (plant seeds), Summer (grow aggressively), Autumn (harvest/bloom), Winter (prune and compost).

**Why it works:** The current system runs the same algorithm every cycle regardless of garden state. But a garden with 6 stale seeds needs a different strategy than a garden with 10 flowering dreams. Seasonal awareness means the system adapts its behavior to what the garden actually needs.

**Mechanism:**
- **Spring mode** (triggered when >50% dreams are seeds): Focus on seed germination. Use all model budget for seed evolution. Cross-pollination disabled (seeds need individual attention first).
- **Summer mode** (triggered when avg strength 0.3-0.6): Aggressive evolution. Maximum cross-pollination. All three model axes active.
- **Autumn mode** (triggered when >30% dreams are flowering/bloom): Focus on bloom quality. Deep evaluation with Kimi. Generate implementation plans for near-bloom dreams.
- **Winter mode** (triggered when garden health score drops): Prune dead tags, archive stale dreams, composting cycle that extracts lessons from failed evolutions.
- Season detection runs at cycle start, sets the mode for that cycle

**Value angle:** The garden currently needs Spring — 6 seeds need attention. But the system keeps running Summer/Autumn logic (evolve everything, cross-pollinate). Seasonal awareness automatically fixes this.

**Risks:**
- Season transitions could be jarring — abrupt strategy shifts
- Thresholds need tuning; wrong thresholds = wrong season
- Winter pruning could delete valuable connections prematurely

---

### PATH E: The Cost Oracle — Dynamic Model Routing with Budget Awareness

**Concept:** Make model routing explicitly cost-aware with a daily/weekly budget. The system has three tiers of inference (free local, free CLI, paid API). Instead of hardcoded routing rules (strength > 0.7 → Kimi), implement a cost oracle that dynamically allocates the paid model budget where it will produce the highest quality delta per dollar.

**Why it works:** Current routing is binary: strength >= 0.7 triggers Kimi, everything else gets Gemini. But a dream at strength 0.69 might benefit more from Kimi than one at 0.71. The cost oracle treats model selection as an optimization problem: maximize total garden quality improvement given a fixed budget.

**Mechanism:**
- Set daily budget: e.g., $0.50/day (Together API ≈ $0.30/1M tokens for Kimi-K2)
- Track cost per model call (MiniMax: $0, Gemini: $0, Kimi: ~$0.001-0.01 per call)
- For each dream in the evolution queue, estimate quality uplift from each model tier:
  - Use historical data: what was the avg quality score when Gemini evolved this dream vs. Kimi?
  - No history yet? Use prior: Kimi gets 1.5x quality multiplier
- Solve the knapsack: given budget B and N dreams to evolve, which model assignment maximizes total quality?
- Log actual quality outcomes to refine estimates over time (reinforcement learning lite)

**Value angle:** Currently Kimi is gated on/off by env var. With budget oracle, it's used surgically — maybe 2-3 calls per day on the dreams that benefit most, instead of either all-Kimi (expensive) or no-Kimi (suboptimal).

**Risks:**
- Requires quality measurement (ties back to Path B's jury model)
- Historical data takes time to accumulate — cold start problem
- Over-optimization could create a different kind of monoculture (always picking same dream for Kimi)

---

## STAGE 2: COMPOUND

*Sequential steps, each building on all previous. Each step inherits the full context chain.*

---

### STEP 1: Foundation — The Core Problem and Constraints

*Inherits: Nothing — this is the foundation.*

The Dream Garden has a **distribution problem** and a **quality problem**.

**Distribution problem:** 239 total evolutions, but 234 went to 2 dreams (117 each). The other 8 dreams got 5 evolutions combined. The evolution queue sorts by strength ascending, but the two bloomed dreams monopolized cycles because they were the only ones with meaningful content for the LLM to work with — fresh seeds with one-line essences produce thin evolutions.

**Quality problem:** Cross-Project Pollination has 130+ tags accumulated over 117 evolutions. Most are generated noise (`consciousness-fusion-fossilization`, `pheromone-market-maker-ai`). There's no quality gate — if the model returns JSON, it's applied. Strength only goes up, never down. The system has no concept of *bad* evolution.

**Hard constraints:**
1. **Cost ceiling:** Paid API usage must stay under ~$1/day. Kimi-K2 via Together costs ~$0.30/M input tokens, $0.99/M output tokens. A typical evolution call uses ~2K tokens → ~$0.002/call. Budget allows ~500 Kimi calls/day, but we want to use them sparingly.
2. **Latency:** Cycles should complete in < 5 minutes. Local MiniMax: ~1s/call. Gemini CLI: ~5-10s/call. Kimi API: ~3-8s/call.
3. **Reliability:** Gemini CLI and MiniMax/Ollama can fail. Fallback chains must exist.
4. **Autonomy:** The system runs via cron. No human in the loop during cycles. Must be self-correcting.

**Design principles extracted from Stage 1:**
- *From Path A:* Evolution budget must be inversely proportional to strength (solve distribution)
- *From Path B:* Evolutions need quality scoring before application (solve quality)
- *From Path C:* Cross-pollination must use graph structure, not random pairs
- *From Path D:* Cycle behavior should adapt to garden state
- *From Path E:* Paid model usage should be budget-optimized, not threshold-gated

---

### STEP 2: The Evolution Budget Allocator — Building on Step 1

*Inherits: Step 1 — distribution problem, quality problem, hard constraints, design principles.*

Step 1 identified that the distribution problem stems from a feedback loop: strong dreams get more cycles. The fix from Path A (inverse budget) needs to be combined with Step 1's constraint that seeds produce thin evolutions — simply giving seeds more turns won't help if their essences are too vague.

**Solution: Two-phase budget allocation.**

**Phase 1 — Enrichment (for seeds only):**
Before evolving a seed, *enrich* it. Use Gemini to expand the one-line essence into a full dream profile: 3-5 paragraph context, 5-10 initial tags, potential connections to existing dreams. This is a one-time investment per seed that solves the "thin content" problem.

Cost: 1 Gemini call per seed (free). For 6 current seeds: 6 calls.

**Phase 2 — Weighted evolution:**
After enrichment, all dreams enter the evolution queue with budget weights:

```python
def evolution_weight(dream: Dream) -> float:
    """Higher weight = higher priority for evolution."""
    base = 1.0 - dream.strength  # Seeds get 0.9, blooms get 0.0

    # Recency penalty: recently evolved dreams wait
    if dream.last_evolved:
        hours_since = (now - dream.last_evolved).total_seconds() / 3600
        recency = min(1.0, hours_since / 24)  # Full weight after 24h
    else:
        recency = 1.0  # Never evolved = full weight

    # Stagnation bonus: dreams stuck at same strength get priority
    stagnation = 1.0 + (dream.evolution_count * 0.01)  # Small bonus per evo without growth

    return base * recency * stagnation
```

Per cycle, select top-N by weight. This naturally rotates through dreams and prevents monopolization.

**How this builds on Step 1:** Step 1 said the distribution problem is that strong dreams consumed all cycles. This step solves it with weighted selection. But it also addresses Step 1's observation that seeds produce thin evolutions — by enriching seeds first, they become viable evolution candidates.

---

### STEP 3: The Quality Gate — Building on Steps 1-2

*Inherits: Steps 1-2 — distribution solved via weighted budgets, seeds enriched before evolution, core constraints.*

Step 1 identified the quality problem (no filter, tags accumulate noise). Step 2 solved distribution but didn't address quality — a seed getting its fair share of evolution cycles still needs quality evolutions. Path B's jury model is the answer, but must be adapted to Step 1's cost constraints.

**Solution: Tiered quality evaluation.**

Not every evolution needs a jury. The cost of evaluation should be proportional to the stakes:

**Tier 1 — Structural validation (free, always applied):**
Before applying any evolution JSON, validate:
- `strength_delta` is within [0.01, 0.15] (reject outliers)
- `new_connections` tags are ≤ 5 per evolution (prevent tag explosion)
- `insight` is > 20 chars and < 500 chars (reject empty or hallucinated walls)
- Tags don't duplicate existing tags (exact match check)

This is pure Python, zero model calls. Catches 80% of garbage.

**Tier 2 — Semantic relevance check (MiniMax, free):**
For dreams at germinating stage or above (strength ≥ 0.2):
- Send the evolution proposal + dream context to MiniMax
- Ask: "Is this insight relevant to the dream? Reply YES or NO."
- If NO: reject the evolution, log it, retry once with different temperature
- Cost: 1 local model call (free)

**Tier 3 — Deep quality scoring (Gemini, free):**
For dreams approaching bloom (strength ≥ 0.6):
- Send evolution proposal to Gemini for quality scoring: novelty, coherence, actionability (each 0-1)
- Composite score determines strength_delta adjustment:
  - Score < 0.4: reject
  - Score 0.4-0.7: halve the strength_delta
  - Score > 0.7: full delta + 0.02 bonus
- Cost: 1 Gemini call (free)

**How this builds on Steps 1-2:** Step 2's budget allocator ensures fair distribution. Step 3 ensures that the evolutions each dream receives are actually good. Together: every dream gets attention (Step 2), and every evolution that lands is quality-checked (Step 3). The tier system respects Step 1's cost constraint — no paid model calls for quality gating.

---

### STEP 4: Graph-Structured Cross-Pollination — Building on Steps 1-3

*Inherits: Steps 1-3 — weighted budgets solve distribution, enrichment solves thin seeds, quality gates filter noise, cost constraints established.*

Steps 2-3 handle individual dream evolution. But the garden's power comes from *connections between dreams*. Current cross-pollination picks one pair per cycle. With Steps 1-3 in place (quality evolutions, diverse dreams), cross-pollination becomes the multiplier.

**Solution: Persistent connection graph with cascade propagation.**

**Graph construction (runs once, updates incrementally):**
```python
class DreamGraph:
    """Persistent weighted graph of dream connections."""

    def __init__(self):
        self.edges: dict[tuple[str,str], float] = {}  # (dream_a, dream_b) → weight
        self.pollination_history: list[dict] = []

    def update_edge(self, a_id: str, b_id: str, score: float):
        """Update or create edge. Scores decay over time."""
        key = tuple(sorted([a_id, b_id]))
        current = self.edges.get(key, 0)
        # Weighted average: 70% new score, 30% historical
        self.edges[key] = 0.7 * score + 0.3 * current

    def get_neighbors(self, dream_id: str, min_weight: float = 0.3) -> list[tuple[str, float]]:
        """Get connected dreams above threshold."""
        neighbors = []
        for (a, b), weight in self.edges.items():
            if weight >= min_weight:
                if a == dream_id:
                    neighbors.append((b, weight))
                elif b == dream_id:
                    neighbors.append((a, weight))
        return sorted(neighbors, key=lambda x: x[1], reverse=True)
```

**Cascade pollination (runs after each evolution):**
After evolving dream A:
1. Get A's neighbors from the graph (weight > 0.3)
2. For each neighbor B with weight > 0.5: inject A's latest evolution insight into B's context for B's next evolution
3. For each neighbor B with weight > 0.7: create a cross-pollination event — dedicate a model call to explicitly connecting A and B
4. Limit cascades to depth=1 (no ripple-of-ripple) to prevent amplification

**Edge weight updates:**
After each evolution cycle, re-score edges for dreams that were evolved:
- Use MiniMax (free) for bulk scoring
- Only re-score edges involving evolved dreams (not the full N² matrix)
- New tags from evolution may create new edges

**How this builds on Steps 1-3:** Step 2's enrichment means seeds have enough content for meaningful connections. Step 3's quality gate means only good evolutions propagate through the graph. The graph enables *ambient cross-pollination* — dreams influence each other without dedicated cross-pollination calls, just by their evolution insights flowing through edges.

---

### STEP 5: Adaptive Cycle Mode — Building on Steps 1-4

*Inherits: Steps 1-4 — weighted budgets, seed enrichment, quality gates, connection graph with cascade pollination.*

Steps 2-4 define *what happens* during a cycle. This step defines *how the cycle adapts* to garden state, drawing from Path D's seasonal model but made concrete against Steps 1-4's architecture.

**Solution: Mode detection at cycle start.**

Instead of rigid seasons, detect the garden's current need and configure the cycle accordingly:

```python
class CycleMode(Enum):
    GERMINATE = "germinate"   # Most dreams are seeds → focus on enrichment + gentle evolution
    GROW = "grow"             # Mixed garden → balanced evolution + active cross-pollination
    HARVEST = "harvest"       # Many near-bloom → deep evaluation + implementation prep
    COMPOST = "compost"       # Stagnation detected → prune tags, archive dead dreams, reset

def detect_mode(state: GardenState) -> CycleMode:
    dreams = list(state.dreams.values())
    stages = Counter(d.stage for d in dreams)
    avg_strength = mean(d.strength for d in dreams)

    # Check for stagnation: many evolutions but low average strength
    if state.total_evolutions > 50 and avg_strength < 0.3:
        return CycleMode.COMPOST

    seed_ratio = stages.get(DreamStage.SEED, 0) / len(dreams)
    bloom_ratio = (stages.get(DreamStage.FLOWERING, 0) + stages.get(DreamStage.BLOOM, 0)) / len(dreams)

    if seed_ratio > 0.5:
        return CycleMode.GERMINATE
    elif bloom_ratio > 0.3:
        return CycleMode.HARVEST
    else:
        return CycleMode.GROW
```

**Mode-specific behavior:**

| Mode | Enrichment | Evolution budget | Quality gate tier | Cross-pollination | Kimi usage |
|------|-----------|-----------------|------------------|-------------------|------------|
| GERMINATE | All seeds enriched first | Seeds get 3x weight | Tier 1 only (gentle) | Disabled | None |
| GROW | New seeds only | Standard weights | Tier 1 + Tier 2 | Graph cascade active | Low-priority dreams only |
| HARVEST | None | Flowering dreams get 2x | All 3 tiers | Focused on bloom candidates | Deep eval for near-bloom |
| COMPOST | None | Suspended | Audit mode — score all existing evolution notes | Prune weak edges | Tag cleanup analysis |

**Current garden would be in GERMINATE mode** (6/10 = 60% seeds). The system would automatically:
1. Enrich all 6 seeds (6 Gemini calls)
2. Evolve seeds with 3x priority
3. Skip cross-pollination (seeds aren't connected enough yet)
4. Avoid Kimi entirely (seeds don't need deep reasoning)

**How this builds on Steps 1-4:** Steps 2-4 define the tools (budgets, quality gates, graph). Step 5 is the *conductor* — it decides which tools to activate and how aggressively, based on what the garden actually needs. Without Step 5, the system would run all subsystems at full intensity every cycle, wasting free model calls on cross-pollination when seeds haven't even been enriched yet.

---

### STEP 6: Bloom Detection and Implementation Bridge — Building on Steps 1-5

*Inherits: Steps 1-5 — adaptive cycles, weighted budgets, quality gates, graph pollination, mode detection.*

Steps 1-5 handle evolution from seed to near-bloom. But the current bloom detection is a simple boolean in the LLM response (`bloom_ready: true`). The LLM has no criteria for what "bloom" means — it's a guess. And once a dream blooms, nothing happens except a Discord announcement. There's no bridge to implementation.

**Solution: Multi-signal bloom detection + implementation pipeline.**

**Bloom readiness score (replaces boolean):**
```python
def bloom_readiness(dream: Dream, graph: DreamGraph) -> float:
    """Score 0-1 indicating bloom readiness. Threshold: 0.8."""
    signals = {
        "strength": dream.strength,  # Must be high
        "evolution_maturity": min(1.0, dream.evolution_count / 10),  # Needs ≥10 evos
        "connection_density": min(1.0, len(graph.get_neighbors(dream.id, 0.3)) / 3),  # ≥3 connections
        "tag_coherence": _tag_coherence_score(dream),  # Tags should cluster, not scatter
        "recent_quality": _recent_evolution_quality(dream),  # Last 3 evos quality scored > 0.6
        "actionability": _actionability_score(dream),  # Has concrete next_steps
    }

    weights = {
        "strength": 0.20,
        "evolution_maturity": 0.15,
        "connection_density": 0.10,
        "tag_coherence": 0.15,
        "recent_quality": 0.20,
        "actionability": 0.20,
    }

    return sum(signals[k] * weights[k] for k in signals)
```

**Implementation bridge (when bloom_readiness > 0.8):**
1. **Synthesis call (Kimi-K2):** Send full dream context + all evolution notes + graph connections to Kimi. Ask for: problem statement, proposed solution, technical approach, effort estimate, dependencies.
2. **Dream-to-Pulse:** Auto-create a Pulse session from the bloom. The Pulse system already has `pulse:from-dream` — the bloom triggers it.
3. **Archive transition:** Bloomed dream moves to `ARCHIVED` stage but remains in the graph as a reference node. Its connections persist so future dreams can reference it.

**How this builds on Steps 1-5:** Step 3's quality gate produces quality scores that feed into `recent_quality`. Step 4's graph provides `connection_density`. Step 5's HARVEST mode triggers deep bloom evaluation. The implementation bridge closes the loop — dreams don't just bloom and get announced; they become Pulse sessions that produce actual code.

---

### STEP 7: Unified Architecture Synthesis — Building on Steps 1-6

*Inherits: Steps 1-6 — budget allocator, seed enrichment, quality gates, dream graph, adaptive modes, bloom detection, implementation bridge.*

The complete system, as a single coherent architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    EVOLUTION CYCLE                        │
│                                                           │
│  ┌──────────────────────────────────────────────┐        │
│  │ 1. MODE DETECTION (Step 5)                    │        │
│  │    Input: GardenState                         │        │
│  │    Output: CycleMode (GERMINATE/GROW/etc.)    │        │
│  └──────────────────────┬───────────────────────┘        │
│                         ▼                                 │
│  ┌──────────────────────────────────────────────┐        │
│  │ 2. SEED ENRICHMENT (Step 2, Phase 1)          │        │
│  │    Model: Gemini (free)                       │        │
│  │    Only in GERMINATE/GROW modes               │        │
│  │    Skips already-enriched seeds               │        │
│  └──────────────────────┬───────────────────────┘        │
│                         ▼                                 │
│  ┌──────────────────────────────────────────────┐        │
│  │ 3. BUDGET ALLOCATION (Step 2, Phase 2)        │        │
│  │    Model: None (pure Python)                  │        │
│  │    Output: Ranked dream queue with weights    │        │
│  └──────────────────────┬───────────────────────┘        │
│                         ▼                                 │
│  ┌──────────────────────────────────────────────┐        │
│  │ 4. EVOLUTION (Steps 2-3)                      │        │
│  │    For each dream in queue:                   │        │
│  │      a. Generate evolution (Gemini/Kimi)      │        │
│  │      b. Quality gate (Tier 1/2/3 per mode)    │        │
│  │      c. Apply or reject                       │        │
│  │      d. Update graph edges (Step 4)           │        │
│  └──────────────────────┬───────────────────────┘        │
│                         ▼                                 │
│  ┌──────────────────────────────────────────────┐        │
│  │ 5. CASCADE POLLINATION (Step 4)               │        │
│  │    Model: MiniMax (scoring), Gemini (synthesis)│       │
│  │    Only in GROW/HARVEST modes                 │        │
│  │    Propagate insights through graph edges     │        │
│  └──────────────────────┬───────────────────────┘        │
│                         ▼                                 │
│  ┌──────────────────────────────────────────────┐        │
│  │ 6. BLOOM CHECK (Step 6)                       │        │
│  │    For each dream with strength > 0.7:        │        │
│  │    Compute bloom_readiness score              │        │
│  │    If > 0.8: trigger implementation bridge    │        │
│  └──────────────────────┬───────────────────────┘        │
│                         ▼                                 │
│  ┌──────────────────────────────────────────────┐        │
│  │ 7. PERSIST + REPORT                           │        │
│  │    Save state, post Discord summary           │        │
│  │    Log model usage stats (Step 1 budget)      │        │
│  └──────────────────────────────────────────────┘        │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Model call budget per cycle (GROW mode, 5 dreams evolved):**

| Phase | Model | Calls | Cost |
|-------|-------|-------|------|
| Enrichment | Gemini | 0-2 (new seeds only) | $0 |
| Evolution | Gemini | 5 | $0 |
| Quality Gate T1 | Python | 5 | $0 |
| Quality Gate T2 | MiniMax | 3-5 | $0 |
| Graph scoring | MiniMax | 10-15 | $0 |
| Cascade pollination | Gemini | 1-2 | $0 |
| Bloom check | Python | 2-3 | $0 |
| Deep eval (optional) | Kimi | 0-1 | $0.002 |
| Journal | Gemini | 1 | $0 |
| **Total** | | **~30** | **$0-0.002** |

Nearly free. Kimi is reserved for bloom synthesis — maybe 1-3 calls per day when dreams actually approach bloom.

---

## STAGE 3: EXPAND + MASTER PLAN

### 3a. AUDIT — What Holds, What Breaks, What's Missing

---

**HOLDS STRONG:**

1. **Budget allocator (Step 2):** The inverse-strength weighting is mathematically sound. `weight = (1 - strength) * recency * stagnation` creates a natural rotation that prevents monopolization. The enrichment phase for seeds is critical — without it, the budget fix just gives bad evolutions to more dreams.

2. **Tiered quality gates (Step 3):** Three tiers mapped to dream maturity is elegant. Tier 1 (structural validation) is bulletproof — pure code, zero cost, catches obvious garbage. Tier 2 (MiniMax relevance check) is a smart use of the free local model. Tier 3 (Gemini quality scoring) adds real evaluation muscle for near-bloom dreams.

3. **Adaptive cycle modes (Step 5):** The current garden (60% seeds) would immediately benefit from GERMINATE mode. The mode detection logic is simple enough to be reliable — counting stages and averaging strength are deterministic operations, not LLM guesses.

4. **Cost profile (Step 7):** Total per-cycle cost of $0-0.002 is exceptional. The architecture uses paid Kimi only for bloom synthesis — the highest-value moment in a dream's lifecycle.

---

**BREAKS UNDER PRESSURE:**

1. **MiniMax as evaluator (Step 3, Tier 2):** A 3B-parameter model judging the output of Gemini 2.5 Pro is questionable. Llama 3.2 3B can follow instructions but lacks the nuance to evaluate creative insight quality. **Fix:** Use MiniMax only for binary relevance (YES/NO), not for nuanced scoring. For quality scoring, Gemini evaluates its own output from a different prompt (self-critique pattern).

2. **Graph at scale (Step 4):** With 10 dreams, the graph has 45 possible edges. With 100 dreams: 4,950 edges. MiniMax scoring all of them every cycle is infeasible. **Fix:** Only re-score edges involving dreams that were evolved this cycle. Cache edge weights with TTL (24h). Score new dream pairs lazily when they first appear in the same evolution context.

3. **Stagnation in COMPOST mode (Step 5):** The compost trigger (`total_evolutions > 50 and avg_strength < 0.3`) would fire right now (239 evolutions, 0.32 avg). But the low average is because 6 seeds were just added — it's not stagnation, it's growth. **Fix:** Use median strength instead of mean, or exclude seeds from the stagnation calculation.

4. **Bloom readiness depends on quality history (Step 6):** `recent_quality` requires quality scores from Step 3's Tier 3 gate. But Tier 3 only runs for dreams at strength ≥ 0.6. Dreams jump from Tier 2 to Tier 3 at 0.6, so there's a cold-start gap. **Fix:** Start Tier 3 scoring at strength 0.5 (GROWING stage) so there's quality history by the time bloom check runs.

5. **Tag coherence scoring (Step 6):** `_tag_coherence_score` was referenced but not defined. With Cross-Project Pollination having 130+ tags, coherence scoring is critical. **Fix:** Define coherence as the ratio of tags that share semantic clusters. Use MiniMax to cluster tags into 3-5 groups. Coherence = (tags in largest cluster / total tags). Score > 0.5 = coherent.

---

**WHAT'S MISSING:**

1. **Dream death/archival criteria:** Dreams can bloom but can't die. Seeds that never germinate after 10+ evolution attempts should be composted with dignity — extract any useful tags/insights, then archive. Without this, the garden accumulates zombie dreams.

2. **Human seeding interface:** New dreams currently come from markdown files in `dreams/`. There's no pathway from Discord conversations, Clawdbot interactions, or manual input. A `/dream plant "idea"` command in Discord would dramatically increase the seed pipeline.

3. **Evolution history compaction:** Each dream stores `evolution_notes` as a growing list. After 100+ evolutions, this list becomes enormous and degrades LLM context quality when included in prompts. Need a periodic compaction that synthesizes N evolution notes into a summary.

4. **Metrics dashboard:** No visibility into model quality, cost tracking, evolution effectiveness. Need a `garden_metrics` module that tracks: quality scores over time, model usage, cost, evolution velocity, bloom rate.

5. **Failure feedback loop:** When a quality gate rejects an evolution, that signal should feed back into the prompt for the next attempt. Currently, rejection is silent — the system just retries with no learning.

---

### 3b. EXPANSIONS — Deep Implementation Specs

---

**EXPANSION 1: Seed Enrichment Protocol**

When a seed enters GERMINATE mode, the enrichment call should produce a structured profile:

```python
ENRICHMENT_PROMPT = """You are enriching a seed idea into a full dream profile.

Current seed:
Title: {title}
Essence: {essence}

Produce a JSON profile:
{{
  "expanded_essence": "3-5 sentence deep description of the core idea",
  "context": "What problem this solves, who it's for, why it matters",
  "initial_tags": ["tag1", "tag2", ...],  // 5-10 relevant tags
  "potential_connections": ["existing_dream_title1", ...],  // Which garden dreams relate
  "first_evolution_prompt": "A specific question to drive the first evolution"
}}
"""
```

Enrichment runs once per seed. The `enriched` flag on the Dream model prevents re-enrichment. Result is applied directly to the dream's fields.

**EXPANSION 2: Evolution Note Compaction**

Every 20 evolutions, compact notes:

```python
def compact_evolution_notes(dream: Dream, synthesis_model) -> str:
    """Synthesize evolution notes into a compressed narrative."""
    if len(dream.evolution_notes) < 20:
        return  # Not yet

    # Keep last 5 notes verbatim, synthesize the rest
    old_notes = dream.evolution_notes[:-5]
    recent_notes = dream.evolution_notes[-5:]

    synthesis = synthesis_model.generate(
        f"Synthesize these {len(old_notes)} evolution notes into a 3-paragraph summary "
        f"preserving key insights, turning points, and connections:\n\n" +
        "\n---\n".join(old_notes)
    )

    dream.evolution_notes = [f"[SYNTHESIS of evolutions 1-{len(old_notes)}]\n{synthesis}"] + recent_notes
```

Cost: 1 Gemini call per compaction. Happens every ~20 evolutions per dream. Negligible.

**EXPANSION 3: Dead Dream Detection**

```python
def is_dead(dream: Dream) -> bool:
    """Detect dreams that aren't growing despite attention."""
    if dream.evolution_count < 5:
        return False  # Give it a chance

    # No strength growth in last 5 evolutions
    if dream.strength <= 0.2 and dream.evolution_count >= 10:
        return True

    # Quality scores consistently below threshold
    recent_quality = dream.metadata.get("recent_quality_scores", [])
    if len(recent_quality) >= 5 and all(q < 0.3 for q in recent_quality[-5:]):
        return True

    return False
```

Dead dreams are composted: extract tags, evolution insights, and connections into a `compost` record, then archive. Compost records feed into future seed enrichment as "lessons learned."

**EXPANSION 4: Clawdbot Integration Points**

| Integration | Direction | Mechanism |
|------------|-----------|-----------|
| Discord → Garden | Inbound | `/dream plant "idea"` command creates seed markdown in `dreams/` |
| Garden → Discord | Outbound | Evolution summaries, bloom announcements (already exists) |
| Garden → Pulse | Outbound | Bloom triggers `pulse:from-dream` (Step 6) |
| HTDS → Garden | Inbound | High-density sessions seed candidates (already exists in evolve.py) |
| Knowledge Graph → Garden | Inbound | GK sync provides tag clusters and concept relationships |
| Garden → Knowledge Graph | Outbound | Evolution insights and connections feed back to GK |

---

### 3c. MASTER EXECUTION CHECKLIST

---

### PHASE 1: Foundation + Quick Wins (Week 1)

- [ ] **1.1** Add `enriched: bool = False` field to Dream model
  - Owner: Developer
  - Input: `dream_engine/models.py`
  - Output: Updated Dream model with enrichment flag
  - Validation: Existing state loads without errors, new field defaults to False
  - Depends on: Nothing
  - Status: Not Started

- [ ] **1.2** Implement structural quality gate (Tier 1)
  - Owner: Developer
  - Input: Step 3 spec — validation rules for strength_delta, tag count, insight length
  - Output: `dream_engine/quality_gate.py` with `validate_evolution(proposal: dict) -> tuple[bool, str]`
  - Validation: Unit tests: rejects delta > 0.15, rejects > 5 new tags, rejects empty insights
  - Depends on: Nothing
  - Status: Not Started

- [ ] **1.3** Implement evolution weight function
  - Owner: Developer
  - Input: Step 2 spec — `evolution_weight()` function
  - Output: `evolution_weight()` in `dream_engine/evo_cube.py`, replacing current `rank_evolution_queue`
  - Validation: Seeds with strength 0.1 rank above blooms with strength 1.0. Recently evolved dreams rank lower.
  - Depends on: Nothing
  - Status: Not Started

- [ ] **1.4** Fix compost mode trigger to use median instead of mean
  - Owner: Developer
  - Input: Audit finding — mean is skewed by seeds
  - Output: Updated mode detection in `detect_mode()` using median strength
  - Validation: Current garden (6 seeds, 2 blooms) triggers GERMINATE, not COMPOST
  - Depends on: 1.3
  - Status: Not Started

---

### PHASE 2: Quality + Enrichment (Week 2)

- [ ] **2.1** Implement seed enrichment protocol
  - Owner: Developer
  - Input: Expansion 1 spec — enrichment prompt, Gemini call
  - Output: `enrich_seed()` in `dream_engine/evo_cube.py`
  - Validation: Run on one test seed. Output has expanded_essence (3+ sentences), 5+ tags, at least 1 connection
  - Depends on: 1.1
  - Status: Not Started

- [ ] **2.2** Implement MiniMax relevance check (Tier 2 quality gate)
  - Owner: Developer
  - Input: Step 3 Tier 2 spec
  - Output: `check_relevance()` in `dream_engine/quality_gate.py`
  - Validation: Returns YES for relevant evolution, NO for obviously irrelevant one. Test with 5 examples.
  - Depends on: 1.2
  - Status: Not Started

- [ ] **2.3** Implement Gemini quality scoring (Tier 3 quality gate)
  - Owner: Developer
  - Input: Step 3 Tier 3 spec — novelty, coherence, actionability scores
  - Output: `score_quality()` in `dream_engine/quality_gate.py`
  - Validation: Returns dict with three scores 0-1. High-quality evolution scores > 0.7, garbage scores < 0.4
  - Depends on: 1.2
  - Status: Not Started

- [ ] **2.4** Integrate quality gates into EvoCube.full_cycle
  - Owner: Developer
  - Input: Tasks 1.2, 2.2, 2.3
  - Output: Modified `full_cycle()` that applies tiered gates before evolution application
  - Validation: Run full cycle in dry-run mode. Verify some evolutions are rejected. Log shows tier applied.
  - Depends on: 1.2, 2.2, 2.3
  - Status: Not Started

---

### PHASE 3: Graph + Cross-Pollination (Week 3)

- [ ] **3.1** Implement DreamGraph class
  - Owner: Developer
  - Input: Step 4 spec — weighted edge graph
  - Output: `dream_engine/dream_graph.py` with DreamGraph class
  - Validation: Can add edges, query neighbors, persist to disk (JSON). Edges sorted by weight.
  - Depends on: Nothing
  - Status: Not Started

- [ ] **3.2** Implement cascade pollination
  - Owner: Developer
  - Input: Step 4 cascade spec — insight propagation through edges
  - Output: `cascade_pollinate()` in `dream_engine/dream_graph.py`
  - Validation: After evolving dream A, dream B (connected with weight > 0.5) receives A's insight in its next evolution context
  - Depends on: 3.1
  - Status: Not Started

- [ ] **3.3** Integrate DreamGraph into EvoCube
  - Owner: Developer
  - Input: Tasks 3.1, 3.2
  - Output: Modified `full_cycle()` that builds/updates graph and runs cascade pollination
  - Validation: Full dry-run cycle. Graph file persisted. Cascades logged. Edge weights updated.
  - Depends on: 3.1, 3.2, 2.4
  - Status: Not Started

- [ ] **3.4** Implement lazy edge scoring with TTL cache
  - Owner: Developer
  - Input: Audit fix — only re-score edges involving evolved dreams, cache with 24h TTL
  - Output: Caching layer in DreamGraph
  - Validation: Second cycle re-uses cached scores for non-evolved dreams. Stale scores (>24h) are refreshed.
  - Depends on: 3.1
  - Status: Not Started

---

### PHASE 4: Adaptive Modes + Bloom Detection (Week 4)

- [ ] **4.1** Implement CycleMode detection
  - Owner: Developer
  - Input: Step 5 spec — mode enum, detection function, mode-specific configs
  - Output: `dream_engine/cycle_mode.py`
  - Validation: Current garden → GERMINATE. Garden with avg strength 0.5 → GROW. Garden with 40% bloom → HARVEST
  - Depends on: Nothing
  - Status: Not Started

- [ ] **4.2** Wire cycle modes into EvoCube.full_cycle
  - Owner: Developer
  - Input: Step 5 mode behavior table
  - Output: Modified `full_cycle()` with mode-conditional paths
  - Validation: GERMINATE mode enriches seeds, skips cross-pollination, skips Kimi. HARVEST mode triggers deep eval.
  - Depends on: 4.1, 2.4, 3.3
  - Status: Not Started

- [ ] **4.3** Implement multi-signal bloom detection
  - Owner: Developer
  - Input: Step 6 spec — bloom_readiness score function
  - Output: `bloom_readiness()` in `dream_engine/evo_cube.py`
  - Validation: Fully evolved dream with quality history → score > 0.8. Fresh seed → score < 0.2.
  - Depends on: 2.3, 3.1
  - Status: Not Started

- [ ] **4.4** Implement Pulse bridge for blooms
  - Owner: Developer
  - Input: Step 6 implementation bridge spec
  - Output: Modified bloom handler that triggers `pulse:from-dream` session creation
  - Validation: When bloom detected, Pulse session created with dream context. Dream archived in graph.
  - Depends on: 4.3
  - Status: Not Started

---

### PHASE 5: Operational Polish (Week 5)

- [ ] **5.1** Implement evolution note compaction
  - Owner: Developer
  - Input: Expansion 2 spec — compact every 20 evolutions
  - Output: `compact_evolution_notes()` in `dream_engine/evo_cube.py`
  - Validation: Dream with 25 notes → compacted to synthesis + 5 recent. Synthesis readable and accurate.
  - Depends on: Nothing
  - Status: Not Started

- [ ] **5.2** Implement dead dream detection + composting
  - Owner: Developer
  - Input: Expansion 3 spec — `is_dead()` function, compost archive
  - Output: Dead dream detection in cycle, compost record in `state/compost.json`
  - Validation: Dream with 10 evolutions and strength < 0.2 is detected as dead. Tags extracted to compost.
  - Depends on: 2.3
  - Status: Not Started

- [ ] **5.3** Add garden metrics logging
  - Owner: Developer
  - Input: Missing feature — metrics tracking
  - Output: `dream_engine/metrics.py` with per-cycle stats logging to `state/metrics.jsonl`
  - Validation: After cycle, metrics file has: model calls by axis, quality scores, evolution velocity, cost estimate
  - Depends on: 2.4
  - Status: Not Started

- [ ] **5.4** Tag coherence scoring for bloom readiness
  - Owner: Developer
  - Input: Audit fix — use MiniMax to cluster tags, compute coherence ratio
  - Output: `tag_coherence_score()` function
  - Validation: Dream with 10 focused tags → high coherence (>0.7). Dream with 130 scattered tags → low (<0.3)
  - Depends on: 4.3
  - Status: Not Started

- [ ] **5.5** End-to-end integration test
  - Owner: Developer
  - Input: Full system assembled
  - Output: Dry-run cycle on current garden state produces: mode detection, seed enrichment, weighted evolution, quality-gated results, graph updates, bloom check
  - Validation: No errors. All phases execute. Stats logged. Output matches expected behavior for GERMINATE mode.
  - Depends on: All previous phases
  - Status: Not Started

---

### Dependency Map

```
Phase 1 (Foundation)     Phase 2 (Quality)       Phase 3 (Graph)         Phase 4 (Modes)        Phase 5 (Polish)
1.1 ─────────────────→ 2.1
1.2 ─────────────────→ 2.2 ──┐
                       2.3 ──┼──→ 2.4 ────────→ 3.3 ──────────→ 4.2
                             │                                    ↑
1.3 ──→ 1.4                  │    3.1 ──→ 3.2 ──┘               4.1 ──→ 4.2
                             │    3.1 ──→ 3.4
                             │                                    4.3 ──→ 4.4
                             └──→ 2.3 ──────────────────────────→ 4.3
                                                                                   5.5 (all)
```

---

### Unit Economics Summary

| Resource | Current | After Implementation |
|----------|---------|---------------------|
| Paid API cost/day | ~$0.47 (117 Kimi calls × $0.004) | ~$0.01 (2-3 Kimi calls for bloom synthesis) |
| Free model calls/cycle | ~15 | ~30 (enrichment + quality gates + graph) |
| Evolution quality | Unfiltered (all applied) | 3-tier gated (30-50% rejection rate) |
| Dream distribution | 2 dreams get 97% of evolutions | Inverse-weighted: seeds get 80% |
| Cross-pollination | 1 pair per cycle | Graph cascade: 3-5 propagations per cycle |
| Bloom detection | Boolean from LLM | 6-signal composite score |
| Time to bloom (estimated) | Unknown (2 bloomed in 117 cycles) | ~30-40 quality evolutions (~10 cycles of 3/cycle) |
| Cycle duration | ~2-3 min | ~3-5 min (more calls but most are free/fast) |

---

*This Evolution³ was generated from full codebase context: evolve.py (445 lines), evo_cube.py (270 lines), gemini_client.py (128 lines), minimax_client.py (167 lines), together_client.py (137 lines), models.py (97 lines), and state/dreams.json (10 dreams, 239 total evolutions). Every recommendation maps to existing code structures and respects the current architecture.*
