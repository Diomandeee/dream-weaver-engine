# DG-0.2 Complete: Structural Quality Gate (Tier 1)

## Summary

Expanded `validate_evolution` from 3 basic checks to 7 structural checks. Wired the gate into both `evo_cube.full_cycle()` and the legacy `evolve.py` path so rejected proposals are skipped before mutating dream state. 18 tests, all passing.

### Rejection rules

| Check | Condition | Reason |
|-------|-----------|--------|
| `strength_delta` type | not int/float | Must be a number |
| `strength_delta` max | > 0.15 | Excessive strength jump |
| `strength_delta` min | < 0 | Negative delta |
| `new_connections` type | not a list | Must be a list |
| `new_connections` count | > 5 tags | Too many tags at once |
| `new_connections` items | non-string or blank | Invalid tag |
| `insight` | empty / whitespace / missing / non-string | No insight provided |

Checks run in the order above; first failure wins.

### Return values

- `(True, 'ok')` — proposal is valid
- `(False, '<reason>')` — proposal rejected with human-readable reason

### Pipeline integration

Both `evo_cube.py:full_cycle()` and `evolve.py` legacy path now call `validate_evolution(result)` between the model response and dream mutation. Rejected proposals are logged and skipped via `continue`.

## Tests

`tests/test_quality_gate.py` — 18 tests covering:
- Valid proposals (boundary values, minimal, zero delta)
- Each rejection path independently (type errors, negatives, empty tags)
- Missing keys, non-string insight, whitespace-only insight
- Priority ordering when multiple checks fail
- Check order verification (strength → connections → insight)

```
18 passed in 0.02s
```

## Files changed

- `dream_engine/quality_gate.py` (rewritten — 7 structural checks)
- `dream_engine/evo_cube.py` (modified — import + gate call in full_cycle)
- `dream_engine/evolve.py` (modified — import + gate call in legacy path)
- `tests/test_quality_gate.py` (rewritten — 18 tests)

## RTD Verification

- [x] Structure: all files present
- [x] Compilation: builds clean
- [x] Integration: no broken refs
- [x] Content: requirements met
- [x] User Journey: works e2e
- [x] Deployment: committed as b4c77f9

## Cross-Pollination
N/A — no cross-track dependencies
