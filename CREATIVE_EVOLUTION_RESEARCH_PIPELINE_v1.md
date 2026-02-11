# Dream Research Automation Pipeline — Evolution³
### Stage 1: Explore → Stage 2: Compound → Stage 3: Master Plan

**Generated:** 2026-02-11
**Method:** Evolution³ — three-stage recursive evoflow
**Subject:** Full-loop autonomous research triggered by dream evolution

---

## STAGE 1: EXPLORE

### Core Question
How do we build an autonomous research engine that makes the dream garden self-sustaining — where dreams don't just grow through LLM reflection but through real-world knowledge acquisition, competitive intelligence, and market validation?

---

### Path A: The Living Library — Research as Dream Nourishment

**Concept:** Research isn't a separate pipeline — it's the soil. Every dream draws nutrients from a continuously-updated knowledge base. Instead of triggering research per-dream, build a persistent knowledge graph that dreams passively absorb during evolution.

**Why it works:** Dreams currently evolve in a vacuum — Kimi-K2 reflects on the dream's essence but has no grounding in reality. A living library means every evolution cycle is informed by real-world context without explicit research triggers.

**Value angle:**
- Dreams converge on viable ideas faster (grounded in real data)
- Cross-pollination becomes knowledge-driven, not random
- The library appreciates over time — early research benefits later dreams

**Risks:**
- Knowledge staleness (library needs freshness management)
- Token cost of injecting library context into every evolution
- Complexity of maintaining a semantic index

---

### Path B: The Research Swarm — Parallel Multi-Agent Investigation

**Concept:** When a dream crosses a threshold, spawn multiple specialized research agents simultaneously: one for technical feasibility, one for competitive landscape, one for market sizing, one for implementation patterns, one for academic papers. Each agent has a narrow focus and returns structured findings. A synthesis agent merges everything.

**Why it works:** Different research dimensions need different search strategies. A market analysis query looks nothing like a technical architecture query. Specialized agents produce higher-quality results than one generalist.

**Value angle:**
- Dramatically faster (parallel execution)
- Higher quality per dimension (specialized prompts/queries)
- Natural fit for the existing dual-dispatch sub-agent infrastructure
- Each dimension can have its own depth/budget

**Risks:**
- API cost multiplication (5 agents × N queries each)
- Synthesis quality depends on merging heterogeneous outputs
- Coordination complexity

---

### Path C: The Bloom Accelerator — Research as Growth Catalyst

**Concept:** Don't research all dreams equally. Focus heavy research only on dreams approaching bloom (strength > 0.7). But instead of just reporting findings, use research to actively accelerate the dream — injecting specific findings into the dream's evolution prompt, adding discovered competitors to the dream's context, updating tags with market-validated keywords.

**Why it works:** Most dreams die in germination. Investing heavy research in early-stage dreams wastes resources. But a dream approaching bloom NEEDS validation before it becomes a project. This creates a natural funnel.

**Value angle:**
- Cost-efficient (research only what matters)
- Research findings directly modify dream evolution trajectory
- Creates a "last mile" validation before bloom → project conversion
- Natural quality gate

**Risks:**
- Early-stage dreams miss potentially pivotal research
- Bloom threshold is arbitrary — some gems might never reach it
- Creates a rich-get-richer dynamic in the garden

---

### Path D: The Reverse Flow — External Signals as Dream Seeds

**Concept:** Flip the loop. Instead of dreams triggering research, set up continuous monitoring of external signals — trending topics, new papers on arXiv, Product Hunt launches, Hacker News discussions, industry reports — and auto-generate dream seeds from what's happening in the world. The garden becomes a living mirror of the innovation landscape.

**Why it works:** Most ideas don't come from internal reflection — they come from seeing what's happening and connecting it to what you know. This makes the garden responsive to the world, not just to its own navel-gazing.

**Value angle:**
- Discovers opportunities you never would have dreamed
- Garden stays fresh and relevant
- Creates a competitive intelligence feed as a side effect
- Seeds are pre-validated (they emerged from real signals)

**Risks:**
- Signal-to-noise ratio (lots of noise in trend monitoring)
- Garden could become reactive instead of visionary
- Needs careful filtering to avoid drowning in mediocre seeds
- External monitoring is a separate infrastructure challenge

---

### Path E: The Research Network — Dreams Research Each Other

**Concept:** Instead of external research, create an internal research dynamic. When dreams share tags or connections, they "investigate" each other — one dream's evolution considers how it relates to, competes with, or complements other dreams. Cross-pollination becomes cross-investigation. Add a "challenge" mechanism where dreams can critique each other's feasibility.

**Why it works:** The garden already has cross-pollination. This deepens it from "these dreams share tags" to "Dream A investigated Dream B's approach and found a flaw / synergy / merger opportunity." Internal research is free (no API calls) and creates emergent garden intelligence.

**Value angle:**
- Zero additional API cost (uses existing evolution prompts)
- Creates genuinely emergent behavior
- Dreams that survive internal challenges are stronger
- Natural consolidation — weak dreams merge into stronger ones

**Risks:**
- Echo chamber (garden only knows what it already knows)
- No external validation
- Could lead to dream consolidation that kills diversity
- Needs careful balance between challenge and nurture

---

### Path F: The Hugo Pipeline — Research at Scale with Event-Driven Architecture

**Concept:** Build a full event-driven research system. Every state change in the garden emits an event (seed_planted, evolved, stage_changed, bloomed, connection_formed). A research orchestrator subscribes to these events and dispatches appropriate research tasks based on configurable rules. Use a priority queue so heavy research doesn't block evolution cycles. Results flow back as events that the garden processes asynchronously.

**Why it works:** The current synchronous approach (research runs inside evolution) creates bottleneck risk. Event-driven architecture decouples research from evolution, allows prioritization, enables retry/backoff, and scales independently. This is the "Hugo scale" approach — built for throughput.

**Value angle:**
- Scales to hundreds of dreams without blocking evolution
- Configurable rules mean easy tuning without code changes
- Retry/backoff handles API failures gracefully
- Event log creates a complete audit trail
- Can add new research dimensions without touching core pipeline

**Risks:**
- Infrastructure complexity (event bus, queue, workers)
- Debugging event-driven systems is harder
- Eventual consistency (dream may evolve before research arrives)
- Overkill for current garden size (2 dreams)

---

## STAGE 2: COMPOUND

### Step 1: Foundation — The Research-Enhanced Dream Model

*Inherits: Stage 1 analysis of all six paths*

The core insight from Stage 1 is that research should be **both reactive (triggered by dreams) AND proactive (feeding the garden from outside)**. Paths A, C, and D aren't competing — they're layers. Path F is the architecture that makes it scale.

**Decision:** The Dream model needs to natively understand research. Currently, dreams have:
- `strength`, `stage`, `tags`, `connections`, `evolution_notes`

We need to add:
- `research_state`: tracking what's been researched and when
- `knowledge_anchors`: specific facts/data points from research that ground the dream
- `competitive_context`: known competitors/alternatives discovered
- `feasibility_scores`: technical, market, novelty, complexity (from research)
- `external_signals`: trending topics, papers, launches that relate to this dream
- `research_depth_reached`: scout/deep/heavy — what level has been done

This transforms the dream from a pure idea-object into a **knowledge-enriched entity** that carries its own research context into every evolution.

**Why this matters:** When Kimi-K2 evolves a dream, it currently only sees the dream's essence and garden connections. With research state embedded, evolution becomes *informed evolution* — the model knows what competitors exist, what's technically feasible, what the market looks like. Every evolution after research is fundamentally different from evolution before research.

---

### Step 2: The Event System — Building on Step 1's Enhanced Model

*Inherits: Step 1 — research-enriched Dream model with knowledge anchors and feasibility scores*

With the enriched Dream model from Step 1, we need an event system that reacts to state changes and dispatches research appropriately. This directly implements Path F from Stage 1.

**Events emitted by the garden:**

| Event | Trigger | Research Action |
|-------|---------|----------------|
| `dream.planted` | New seed created | Scout research (3 queries, quick scan) |
| `dream.evolved` | Strength increased | Check if threshold crossed for deeper research |
| `dream.stage_changed` | Stage transition | Deep research at growing→flowering, Heavy at flowering→bloom |
| `dream.bloomed` | Reached bloom | Full heavy research + implementation validation |
| `dream.connected` | New connection formed | Cross-reference research between connected dreams |
| `dream.research_completed` | Research finished | Inject findings into dream model (Step 1's fields) |
| `garden.external_signal` | Trend detected | Match against existing dreams + generate new seeds |

**Priority queue:** Events are prioritized by dream strength × trigger importance. A bloom event on a 0.95-strength dream goes before a planted event on a 0.1 seed. This prevents research backlog from blocking important investigations.

**Implementation:** GitHub Actions already gives us the event dispatch (workflow_run triggers). For more sophisticated queuing, we can use the existing state/research.json to track pending research and process them in priority order within a single workflow run.

**Connection to Step 1:** Every `dream.research_completed` event writes results into Step 1's enriched Dream fields. The dream's `knowledge_anchors` grow with each research cycle. Its `feasibility_scores` update. The next evolution cycle reads this richer context.

---

### Step 3: The Research Dimensions — Building on Steps 1+2's Event-Driven Enriched Model

*Inherits: Steps 1-2 — enriched Dream model + event system that dispatches research based on state changes*

Now that we have the model (Step 1) and the dispatch system (Step 2), we need to define WHAT gets researched and HOW. This implements Path B's specialized dimensions within Path F's architecture.

**Five research dimensions, each with specialized search strategies:**

**1. Technical Feasibility**
- Queries: "how to implement [X]", "[X] architecture patterns", "[X] open source library"
- Sources: GitHub, Stack Overflow, technical blogs, documentation
- Output: feasibility_score (1-10), key_technologies[], implementation_patterns[], estimated_complexity

**2. Market Intelligence**
- Queries: "[X] market size", "[X] competitors", "[X] pricing", "who uses [X]"
- Sources: Crunchbase, Product Hunt, industry reports, news
- Output: market_score (1-10), competitors[], market_size_estimate, pricing_benchmarks[]

**3. Academic & Innovation**
- Queries: "[X] research paper", "[X] novel approach", "[X] state of the art"
- Sources: arXiv, Google Scholar, research blogs, conference proceedings
- Output: novelty_score (1-10), prior_art[], research_gaps[], innovation_opportunities[]

**4. Community Sentiment**
- Queries: "[X] opinions", "why [X] fails", "[X] vs alternatives", "[X] problems"
- Sources: Reddit, HN, Twitter/X, forums, review sites
- Output: sentiment_score (-1 to 1), common_complaints[], praise_points[], unmet_needs[]

**5. Implementation Roadmap**
- Queries: "[X] tutorial", "[X] best practices", "[X] mistakes to avoid", "[X] production"
- Sources: Engineering blogs, case studies, post-mortems, documentation
- Output: roadmap_phases[], estimated_timeline, critical_dependencies[], common_pitfalls[]

**Depth determines which dimensions run:**
- Scout: Dimensions 1 + 2 only (quick viability check)
- Deep: Dimensions 1-4 (full landscape minus roadmap)
- Heavy: All 5 dimensions (complete investigation)

**Connection to Steps 1-2:** Each dimension writes to specific fields in Step 1's enriched Dream model. The event system from Step 2 determines which dimensions fire based on the event type. A `dream.bloomed` event triggers all 5; a `dream.planted` triggers only 1+2.

---

### Step 4: The Reverse Flow — Building on Steps 1-3's Research Infrastructure

*Inherits: Steps 1-3 — enriched model + event system + five research dimensions*

With the outbound research infrastructure in place (dreams → research → findings), we now build the inbound flow (world → seeds → dreams). This implements Path D using the same infrastructure from Steps 2-3.

**External Signal Sources:**

1. **Trending Tech** (daily scan)
   - Hacker News front page (`https://hacker-news.firebaseio.com/v0/topstories.json`)
   - Product Hunt daily digest
   - GitHub Trending repos
   - Query: Top stories → extract concepts → match against garden tags

2. **Research Papers** (weekly scan)
   - arXiv CS categories (cs.AI, cs.SE, cs.HC)
   - Query: Recent papers → extract abstracts → match against dream essences

3. **Industry Signals** (weekly scan)
   - TechCrunch, The Verge, Ars Technica
   - Funding announcements (relevant to dream domains)
   - Query: News → extract product/company themes → match against garden

**Matching Algorithm:**
```python
def match_signal_to_garden(signal, garden_state):
    """Match an external signal against existing dreams."""
    signal_tags = extract_tags(signal)
    
    for dream in garden_state.dreams.values():
        overlap = len(set(signal_tags) & set(dream.tags))
        if overlap >= 2:  # At least 2 shared tags
            dream.external_signals.append(signal)
            # Boost dream strength slightly (external validation)
            dream.strength += 0.02
    
    # If no match, consider as new seed
    if not any_match:
        return create_seed_from_signal(signal)
```

**Seed Generation from Signals:**
- Only generate seeds from signals that DON'T match existing dreams (avoid redundancy)
- Seeds from external signals get `source: "external-signal"` tag
- Energy threshold: 0.5 (higher bar than synthesis-generated seeds)
- Maximum 3 new seeds per scan cycle (prevent garden flooding)

**Connection to Steps 1-3:** External signals use the same Brave Search client (Step 3's infrastructure) for fetching content. Matched signals write to Step 1's `external_signals` field. New seeds enter the garden through Step 2's event system (`garden.external_signal` event).

---

### Step 5: Internal Cross-Investigation — Building on Steps 1-4's Full Pipeline

*Inherits: Steps 1-4 — enriched model + events + dimensions + reverse flow*

With both outbound and inbound research working, we add Path E's internal investigation layer. This is the cheapest and most powerful research dimension because it uses knowledge already in the garden.

**Dream Cross-Investigation Protocol:**

When two dreams share 2+ tags or are explicitly connected, during evolution:

1. **Comparison Analysis:** "Dream A wants to do X. Dream B already solved a similar problem with Y. Can A learn from B?"
2. **Competition Check:** "Dream A and Dream B both target the same space. Are they competing or complementary?"
3. **Merger Detection:** "Dream A (strength 0.3) and Dream B (strength 0.6) cover overlapping ground. Should A be absorbed into B?"
4. **Gap Filling:** "Dream A has strong technical feasibility but no market research. Dream B has market research in the same domain. Transfer B's market knowledge to A."

**Implementation in Evolution Prompt:**
```
# Cross-Investigation Context
Dream "{connected_dream.title}" (strength {connected_dream.strength}) has:
- Research findings: {connected_dream.knowledge_anchors}
- Competitors identified: {connected_dream.competitive_context}  
- Feasibility scores: {connected_dream.feasibility_scores}

Consider: How does this dream relate to the one you're evolving?
Should they merge, compete, or cross-pollinate specific knowledge?
```

**Garden Intelligence Metrics:**
- Connection density (avg connections per dream)
- Knowledge transfer rate (how much research flows between dreams)
- Merger rate (dreams consolidated per cycle)
- Diversity index (tag entropy across garden)

**Connection to Steps 1-4:** Cross-investigation reads from Step 1's enriched fields (knowledge_anchors, feasibility_scores) populated by Step 3's research dimensions. External signals from Step 4 provide additional context. The event system (Step 2) tracks `dream.connected` events to trigger cross-investigation.

---

### Step 6: The Dashboard & Feedback Loop — Building on Steps 1-5's Complete System

*Inherits: Steps 1-5 — full pipeline with enriched model, events, research dimensions, reverse flow, and cross-investigation*

The final piece: visibility and human feedback. The system needs to show what it's doing and accept guidance.

**Discord Integration (already partially built):**

1. **#research channel** — Research reports posted here (already implemented in discord_reporter.py)
2. **#garden channel** — Evolution summaries now include research findings
3. **#blooms channel** — Bloom announcements now include feasibility scores and competitive landscape
4. **#dream-journal** — Journal entries reference external signals and research discoveries

**New: Research Dashboard (posted daily to #morning-brief):**
```
🔬 Research Dashboard — Feb 11, 2026

📊 Garden Health
  Dreams: 12 | Blooms: 3 | Seeds today: 5
  Avg feasibility: 6.2/10 | Avg novelty: 7.1/10
  
🔍 Research Activity (24h)
  Reports generated: 4 (2 heavy, 1 deep, 1 scout)
  Sources consulted: 127
  Seeds planted from research: 7
  
📡 External Signals
  Matched to existing dreams: 3
  New seeds from signals: 2
  Trending overlap: AI agents, voice interfaces
  
🏆 Top Dreams by Research Score
  1. Cross-Project Pollination — 7.8/10
  2. Autonomous Dream Engine — 6.5/10
  
⚠️ Research Gaps
  - No market research on: [dream X, dream Y]
  - Stale research (>7 days): [dream Z]
```

**Human Feedback Mechanisms:**
- React with 🔬 on any dream/bloom to force a heavy research cycle
- React with 🚫 on a research report to stop researching that dream
- React with 🌰 on a research-generated seed to boost its energy
- `/research <dream_id> [depth]` — manual trigger

**Connection to Steps 1-5:** Dashboard reads from Step 1's enriched model fields across all dreams. Research activity comes from Step 2's event log. External signals from Step 4. Cross-investigation metrics from Step 5. All feedback reactions flow back through Step 2's event system.

---

### Step 7: Synthesis — The Complete Research-Enhanced Dream Garden

*Inherits: Steps 1-6 — everything*

**The unified system:**

```
EXTERNAL WORLD                    DREAM GARDEN                    RESEARCH ENGINE
─────────────────                ────────────────                ─────────────────
                                                                
Trends ──────────┐               ┌── Dreams ───┐               ┌── Brave Search
Papers ──────────┤               │  · model    │               ├── Kimi-K2 Synthesis  
News ────────────┤──→ Signal ──→ │  · research │──→ Events ──→ ├── 5 Dimensions
Product Hunt ────┘    Matcher    │  · anchors  │               ├── Content Extraction
                                 │  · scores   │               └── Seed Generator
                                 └─────────────┘                        │
                                       ↑                                │
                                       └────── Findings + Seeds ────────┘
                                       
                                 Discord Dashboard
                                 Human Feedback ↔ Event System
```

**Key properties of the complete system:**
1. **Self-sustaining:** Dreams generate research, research generates seeds, seeds become dreams
2. **World-aware:** External signals keep the garden relevant and grounded
3. **Internally intelligent:** Dreams investigate each other, sharing knowledge and challenging assumptions
4. **Human-guided:** Dashboard provides visibility, reactions provide steering
5. **Scalable:** Event-driven architecture handles garden growth without bottlenecks
6. **Cost-aware:** Depth scales with dream strength — no wasted research on dead seeds

---

## STAGE 3: EXPAND + MASTER PLAN

### 3a. Audit

**What holds strong:**
- ✅ The enriched Dream model (Step 1) — natural extension of existing Pydantic model, backward compatible
- ✅ Event system (Step 2) — maps cleanly to existing GitHub Actions workflow_run triggers
- ✅ Research dimensions (Step 3) — already partially implemented in report_generator.py
- ✅ Discord integration (Step 6) — building on existing webhook infrastructure
- ✅ Cost management — depth-based research prevents runaway API costs

**What breaks under pressure:**
- ⚠️ **GitHub Actions limits:** Free tier = 2,000 minutes/month. Heavy research on 20 dreams × 15 page fetches × 12 queries = expensive. Need budget tracking.
- ⚠️ **Brave API rate limits:** Free tier = 2,000 queries/month. With 12 queries per heavy research × 30 evolution cycles/month... that's tight.
- ⚠️ **Race conditions:** Evolution pushes state, research reads state, both modify dreams. Need locking or atomic updates.
- ⚠️ **Context window pressure:** Injecting research findings + external signals + cross-investigation context into evolution prompts could exceed Kimi-K2's effective attention even within 256K.

**What's missing:**
- 🔴 **BRAVE_API_KEY** — not yet configured as GitHub secret
- 🔴 **DISCORD_WEBHOOK_RESEARCH** — webhook not created yet
- 🟡 **Budget tracking** — no mechanism to track API spend across Brave + Together
- 🟡 **Research quality scoring** — no way to evaluate if research was actually useful
- 🟡 **Deduplication** — research seeds could duplicate existing dreams
- 🟡 **External signal monitoring** — infrastructure not built yet (Step 4)
- 🟡 **Cross-investigation prompts** — not yet added to evolution prompts (Step 5)

---

### 3b. Expansions

**Expansion 1: Budget Management System**

```python
# state/budget.json
{
  "brave_api": {
    "monthly_limit": 2000,
    "used_this_month": 0,
    "reset_date": "2026-03-01",
    "cost_per_query": 0  # Free tier
  },
  "together_ai": {
    "monthly_budget_usd": 50.00,
    "used_this_month_usd": 0,
    "cost_per_1k_input": 0.0012,
    "cost_per_1k_output": 0.004
  },
  "github_actions": {
    "monthly_minutes": 2000,
    "used_this_month": 0
  }
}
```

Before any research call, check budget. If >80% consumed, downgrade all research to scout depth. If >95%, pause research until next month.

**Expansion 2: Research Quality Feedback Loop**

After research findings are injected into a dream and the dream evolves:
- Compare evolution quality (strength delta, insight quality) with vs. without research context
- Track which research dimensions most influenced dream evolution
- Over time, learn which dimensions are worth the cost for which dream types

**Expansion 3: Smart Deduplication**

Before planting research-generated seeds:
1. Compare title similarity (fuzzy match) against all existing dreams
2. Compare tag overlap (>60% = likely duplicate)
3. If potential duplicate found, merge insights into existing dream instead of planting new seed

---

### 3c. Master Execution Checklist

### PHASE 1: Activate Core Pipeline (This Week)

- [ ] **1.1** Get Brave Search API key
  - Owner: Human
  - Input: Brave Search account
  - Output: API key string
  - Validation: `curl -H "X-Subscription-Token: KEY" "https://api.search.brave.com/res/v1/web/search?q=test"` returns results
  - Depends on: Nothing
  - Status: Not Started

- [ ] **1.2** Create Discord webhook for #research channel
  - Owner: Agent (Clawdbot)
  - Input: #research channel ID (1470138487565979719)
  - Output: Webhook URL
  - Validation: POST to webhook produces message in #research
  - Depends on: Nothing
  - Status: Not Started

- [ ] **1.3** Set GitHub secrets: BRAVE_API_KEY + DISCORD_WEBHOOK_RESEARCH
  - Owner: Agent (via `gh secret set`)
  - Input: API key from 1.1, webhook from 1.2
  - Output: Secrets configured in Diomandeee/dream-weaver-engine
  - Validation: `gh secret list` shows both secrets
  - Depends on: 1.1, 1.2
  - Status: Not Started

- [ ] **1.4** Test pipeline with manual trigger
  - Owner: Agent
  - Input: Existing dream (cross-project-pollination or autonomous-dream-engine)
  - Output: Research report in #research, report file in research/reports/
  - Validation: Report contains synthesis, feasibility scores, at least 1 seed
  - Depends on: 1.3
  - Status: Not Started

- [ ] **1.5** Verify automatic trigger
  - Owner: Agent
  - Input: Trigger evolution cycle, observe research workflow
  - Output: Research workflow runs after evolution completes
  - Validation: GitHub Actions shows research.yml completed after evolve.yml
  - Depends on: 1.4
  - Status: Not Started

### PHASE 2: Enrich Dream Model (Week 2)

- [ ] **2.1** Add research fields to Dream model
  - Owner: Agent (sub-agent)
  - Input: Current models.py
  - Output: Updated Dream class with research_state, knowledge_anchors, competitive_context, feasibility_scores, external_signals
  - Validation: Existing state loads with new fields (backward compatible with defaults)
  - Depends on: 1.5 (pipeline proven)
  - Status: Not Started

- [ ] **2.2** Update evolution prompt to read research context
  - Owner: Agent (sub-agent)
  - Input: Current together_client.py evolve_dream()
  - Output: Evolution prompt includes knowledge_anchors and feasibility_scores when available
  - Validation: Evolution with research-enriched dream produces qualitatively different output
  - Depends on: 2.1
  - Status: Not Started

- [ ] **2.3** Research writes back to Dream model
  - Owner: Agent (sub-agent)
  - Input: Current research/engine.py
  - Output: research_dream() updates dream's enriched fields in state
  - Validation: After research, `state/dreams.json` shows populated research fields
  - Depends on: 2.1, 2.2
  - Status: Not Started

### PHASE 3: Budget & Quality Gates (Week 2-3)

- [ ] **3.1** Implement budget tracking (state/budget.json)
  - Owner: Agent (sub-agent)
  - Input: Budget schema from Expansion 1
  - Output: Budget file created, checked before every API call
  - Validation: Research degrades gracefully when budget >80%
  - Depends on: 1.5
  - Status: Not Started

- [ ] **3.2** Add deduplication to seed planting
  - Owner: Agent (sub-agent)
  - Input: Current plant_research_seeds()
  - Output: Fuzzy title + tag matching before planting
  - Validation: Duplicate seeds get merged instead of planted
  - Depends on: 1.5
  - Status: Not Started

- [ ] **3.3** Research quality scoring
  - Owner: Agent (sub-agent)
  - Input: Evolution results pre/post research
  - Output: Quality delta metric in research state
  - Validation: Dashboard shows which research dimensions most impact evolution
  - Depends on: 2.2, 2.3
  - Status: Not Started

### PHASE 4: External Signals (Week 3-4)

- [ ] **4.1** Build signal scanner (HN, Product Hunt, GitHub Trending)
  - Owner: Agent (sub-agent)
  - Input: External APIs
  - Output: research/signals.py with scan_external_signals()
  - Validation: Returns structured list of signals with extracted tags
  - Depends on: 2.1 (needs external_signals field)
  - Status: Not Started

- [ ] **4.2** Signal-to-garden matching
  - Owner: Agent (sub-agent)
  - Input: Signal list + garden state
  - Output: Matched signals update dream strength, unmatched generate seeds
  - Validation: At least 1 existing dream gets signal match, at least 1 new seed planted
  - Depends on: 4.1
  - Status: Not Started

- [ ] **4.3** GitHub Actions workflow for signal scanning
  - Owner: Agent (sub-agent)
  - Input: Workflow template
  - Output: .github/workflows/signals.yml (runs daily)
  - Validation: Daily signal scan completes, results in state/signals.json
  - Depends on: 4.1, 4.2
  - Status: Not Started

### PHASE 5: Cross-Investigation & Dashboard (Week 4)

- [ ] **5.1** Cross-investigation in evolution prompts
  - Owner: Agent (sub-agent)
  - Input: Connected dream research data
  - Output: Evolution prompt includes cross-investigation context
  - Validation: Connected dreams show knowledge transfer in evolution notes
  - Depends on: 2.2, 2.3
  - Status: Not Started

- [ ] **5.2** Daily research dashboard
  - Owner: Agent (cron job)
  - Input: Garden state, research state, budget state
  - Output: Dashboard post in #morning-brief
  - Validation: Dashboard shows garden health, research activity, budget status
  - Depends on: 3.1, 4.2
  - Status: Not Started

- [ ] **5.3** Reaction-based human feedback
  - Owner: Agent (Clawdbot hook)
  - Input: Discord reactions on research/dream messages
  - Output: 🔬 triggers research, 🚫 stops it, 🌰 boosts seed energy
  - Validation: React on a dream, observe corresponding action
  - Depends on: 5.2
  - Status: Not Started

---

*Generated by Evolution³ — Dream Weaver Research Engine*
