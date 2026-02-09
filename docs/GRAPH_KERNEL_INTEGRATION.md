# Graph Kernel + Kimi-K2 Memory Integration

## Vision

Connect Comp-Core's Graph Kernel and RAG++ to the Kimi-K2 memory layer, enabling:
- **Slice-conditioned synthesis** — Context slicing for focused responses
- **Knowledge graph integration** — Semantic relationships from Graph Kernel
- **Dual-plane retrieval** — Raw messages + semantic atoms

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    UNIFIED MEMORY ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐                    ┌─────────────────┐        │
│  │   Kimi-K2       │◄──────────────────►│   Graph Kernel  │        │
│  │   Synthesizer   │    knowledge        │   (Rust/8001)   │        │
│  │   (Python)      │    triples          │                 │        │
│  └────────┬────────┘                    └────────┬────────┘        │
│           │                                      │                  │
│           ▼                                      ▼                  │
│  ┌─────────────────┐                    ┌─────────────────┐        │
│  │   SQLite        │                    │   RAG++         │        │
│  │   Memory DB     │◄──────────────────►│   (Python/8000) │        │
│  │                 │    slice-scoped     │                 │        │
│  │  • messages     │    retrieval        │  • vector search│        │
│  │  • syntheses    │                    │  • reranking    │        │
│  │  • context      │                    │  • provenance   │        │
│  │  • knowledge    │                    │                 │        │
│  └─────────────────┘                    └─────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Integration Points

### 1. Knowledge Graph Sync
Kimi-K2 extracts knowledge triples → Graph Kernel stores relationships

```python
# In synthesizer.py
def sync_to_graph_kernel(triples: List[Triple]):
    """Push extracted knowledge to Graph Kernel."""
    for subject, predicate, obj in triples:
        requests.post(
            "http://localhost:8001/api/knowledge",
            json={"subject": subject, "predicate": predicate, "object": obj}
        )
```

### 2. Slice-Conditioned Synthesis
Before synthesis, get admissible context slice from Graph Kernel

```python
# Enhanced synthesis flow
async def synthesize_with_slice(message: str, anchor_turn_id: str):
    # Get slice from Graph Kernel
    slice_export = await slice_client.get_slice(anchor_turn_id, policy_ref)
    
    # Filter memory to admissible turns
    admissible_context = memory.get_messages_in_slice(slice_export.turn_ids)
    
    # Synthesize with focused context
    return synthesize(message, context=admissible_context)
```

### 3. RAG++ Retrieval Augmentation
Use RAG++ for semantic search when building context

```python
async def build_rich_context(query: str, anchor: str):
    # Slice-scoped retrieval
    rag_results = await rag_client.search_slice(query, anchor)
    
    # Combine with memory context
    memory_context = memory.build_context_summary()
    
    return {
        "memory": memory_context,
        "retrieved": rag_results.results,
        "provenance": rag_results.provenance
    }
```

## Implementation Phases

### Phase 1: Local Integration (Current)
- [x] SQLite memory store
- [x] Knowledge graph table
- [ ] Graph Kernel client in Python
- [ ] Slice-aware context building

### Phase 2: Service Connection
- [ ] Connect to running Graph Kernel service
- [ ] Connect to RAG++ service
- [ ] Bidirectional knowledge sync

### Phase 3: Unified Retrieval
- [ ] Dual-plane retrieval (messages + atoms)
- [ ] Provenance-aware synthesis
- [ ] Semantic artifact incorporation

## Configuration

```yaml
# config.yaml
graph_kernel:
  enabled: true
  url: http://localhost:8001
  policy_ref: "default_slice_policy"

rag_plus_plus:
  enabled: true
  url: http://localhost:8000
  search_mode: "slice"  # or "global"

memory:
  sync_knowledge: true
  slice_aware: true
```

## API Endpoints

### From Graph Kernel
- `POST /api/slice` — Get context slice
- `GET /api/policies` — List slice policies
- `POST /api/knowledge` — Add knowledge triple

### From RAG++
- `POST /api/rag/search/slice` — Slice-scoped search
- `POST /api/rag/context/slice` — Slice-scoped context

## Benefits

1. **Focused Context** — Only admissible information in synthesis
2. **Semantic Depth** — Knowledge graph relationships enrich understanding
3. **Determinism** — Same anchor + policy = same slice = reproducible
4. **Provenance** — Full chain from query to retrieved content
5. **Scale** — RAG++ handles large corpora efficiently
