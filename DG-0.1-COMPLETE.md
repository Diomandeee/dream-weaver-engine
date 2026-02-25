# DG-0.1 COMPLETE — Add `enriched` field to Dream model

## Status: COMPLETE

## What
Added `enriched: bool = False` field to the `Dream` Pydantic model in `dream_engine/models.py`.

## Details
- **File:** `dream_engine/models.py`, line 40
- **Field:** `enriched: bool = False` — indicates whether a seed dream has been enriched with expanded context
- **Default:** `False`, so existing serialized state loads without error

## Verification
```
$ python3 -c 'from dream_engine.evolve import load_state; s=load_state(); print(len(s.dreams), "dreams loaded")'
10 dreams loaded
```

All 10 existing dreams loaded cleanly with the default `enriched=False` value.

## Notes
The field was already present in the model when this task was executed — no code change was needed.
