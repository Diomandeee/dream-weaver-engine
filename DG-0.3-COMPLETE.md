# DG-0.3 COMPLETE — evolution_weight() replaces rank_evolution_queue model call

## What changed

**File:** `dream_engine/evo_cube.py`

Replaced the `rank_evolution_queue` method's dependency on `self.scoring.rank_evolution_priority()` (a model call) with a pure-math `evolution_weight()` static method.

### Formula

```
weight = (1 - strength) * (1 / (evolution_count + 1)) * recency_penalty
```

Where `recency_penalty = min(1.0, hours_since_last_evolved / 6.0)`.

- Never-evolved dreams get `recency_penalty = 1.0` (max priority).
- Dreams evolved less than 6 hours ago get a fractional penalty.

### Why it works

| Factor | Seeds (str=0.1, evos=0) | Blooms (str=1.0, evos=117) |
|--------|------------------------|---------------------------|
| `1 - strength` | 0.9 | 0.0 |
| `1 / (evos + 1)` | 1.0 | ~0.0085 |
| Product (before recency) | 0.9 | 0.0 |

Blooms at strength 1.0 always get weight **0.0** regardless of recency, so seeds always rank above blooms.

### `rank_evolution_queue` refactored

The method still exists with the same signature (`state, max_count`) so `full_cycle` needed no changes. Internally it now sorts by `evolution_weight` instead of calling a model, making ranking:

- **Free** — no model call, no network
- **Deterministic** — same state always produces the same ranking
- **Fast** — O(n log n) sort

## Test results (live garden, 10 dreams)

```
Rank    Weight  Stage          Str  Evos  Title
1      0.90000  seed          0.10     0  Cognitive Twin — The Reversal
2      0.90000  seed          0.10     0  Speak Flow — Personal Voice OS
3      0.90000  seed          0.10     0  Eternal Serenity — The LitRPG Convergence
4      0.06053  seed          0.15     1  N'Ko Digital Preservation
5      0.06025  seed          0.15     1  Spore — The Idea Garden App
6      0.05991  seed          0.15     1  The Autonomous Pulse Machine
7      0.05599  germinating   0.22     1  VisionClaw — AI Eyes for the Real World
8      0.05509  germinating   0.23     1  Skill Entity Architecture (SEA)
9      0.00000  bloom         1.00   117  Cross-Project Pollination
10     0.00000  bloom         1.00   117  Autonomous Dream Engine

Worst seed weight:  0.059914
Best bloom weight:  0.000000
PASS: All seeds rank above all blooms
```

## Unit tests

`tests/test_evolution_weight.py` — 13 tests covering:

| Category | Tests |
|----------|-------|
| Weight formula | fresh seed max weight, full bloom zero, strength=0 max base |
| Recency penalty | zero at t=0, linear at 3h, saturates at 6h, caps at 1.0 |
| Evolution count | dampening effect verified |
| Seed vs bloom | typical seeds outrank typical blooms |
| `rank_evolution_queue` | correct ordering, archived exclusion, max_count limit |

```
24 passed in 0.06s  (13 evolution_weight + 11 quality_gate)
```

## RTD Verification
- [x] Structure: all files present
- [x] Compilation: builds clean
- [x] Integration: no broken refs
- [x] Content: requirements met
- [x] User Journey: works e2e (live garden ranking confirmed)
- [x] Deployment: committed (b9117b4)
