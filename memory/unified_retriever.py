"""Unified Retriever - Combines local memory, Graph Kernel, and RAG++.

Three-tier retrieval:
1. Local SQLite memory (fast, always available)
2. Graph Kernel slicing (when available)
3. RAG++ vector search (when available)
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .store import MemoryStore, get_store
from .graph_kernel_client import (
    GraphKernelClient, get_graph_kernel_client,
    SliceExport, PolicyRef, KnowledgeTriple
)
from .rag_client import (
    RAGPlusPlusClient, get_rag_client,
    SearchResult, SliceScopedResults, GlobalResults
)


@dataclass
class UnifiedContext:
    """Context built from all available sources."""
    
    # Local memory
    recent_messages: List[Dict] = field(default_factory=list)
    known_facts: List[Dict] = field(default_factory=list)
    known_preferences: List[Dict] = field(default_factory=list)
    patterns: List[Dict] = field(default_factory=list)
    
    # Graph Kernel
    slice_export: Optional[SliceExport] = None
    knowledge_triples: List[KnowledgeTriple] = field(default_factory=list)
    
    # RAG++
    retrieved_results: List[SearchResult] = field(default_factory=list)
    retrieval_mode: str = "local"  # local, slice, global, hybrid
    
    # Meta
    build_time_ms: float = 0
    sources_used: List[str] = field(default_factory=list)
    
    def to_prompt_context(self, max_chars: int = 4000) -> str:
        """Build context string for prompt injection."""
        parts = []
        
        # Recent conversation
        if self.recent_messages:
            parts.append("## Recent Conversation")
            for msg in self.recent_messages[-5:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')[:200]
                parts.append(f"[{role}] {content}...")
        
        # Known facts & preferences
        if self.known_facts:
            parts.append("\n## Known Facts")
            for f in self.known_facts[:10]:
                parts.append(f"- {f['key']}: {f['value']}")
        
        if self.known_preferences:
            parts.append("\n## Preferences")
            for p in self.known_preferences[:10]:
                parts.append(f"- {p['key']}: {p['value']}")
        
        # Knowledge graph
        if self.knowledge_triples:
            parts.append("\n## Related Knowledge")
            for t in self.knowledge_triples[:10]:
                parts.append(f"- {t.subject} → {t.predicate} → {t.object}")
        
        # Retrieved content
        if self.retrieved_results:
            parts.append(f"\n## Retrieved Context ({self.retrieval_mode})")
            for r in self.retrieved_results[:5]:
                parts.append(f"[score={r.score:.2f}] {r.content[:200]}...")
        
        # Slice info
        if self.slice_export:
            parts.append(f"\n## Slice: {self.slice_export.slice_id}")
            parts.append(f"Anchor: {self.slice_export.anchor_turn_id}")
            parts.append(f"Turns: {self.slice_export.turn_count}")
        
        context = "\n".join(parts)
        if len(context) > max_chars:
            context = context[:max_chars] + "\n...[truncated]"
        
        return context


class UnifiedRetriever:
    """Unified retrieval across local memory, Graph Kernel, and RAG++."""
    
    def __init__(self):
        self.memory: MemoryStore = get_store()
        self.graph_kernel: GraphKernelClient = get_graph_kernel_client()
        self.rag: RAGPlusPlusClient = get_rag_client()
        
        self._gk_available = None
        self._rag_available = None
    
    async def check_services(self) -> Dict[str, bool]:
        """Check which services are available."""
        gk_check = self.graph_kernel.health_check()
        rag_check = self.rag.health_check()
        
        results = await asyncio.gather(gk_check, rag_check, return_exceptions=True)
        
        self._gk_available = results[0] if not isinstance(results[0], Exception) else False
        self._rag_available = results[1] if not isinstance(results[1], Exception) else False
        
        return {
            "local_memory": True,
            "graph_kernel": self._gk_available,
            "rag_plus_plus": self._rag_available
        }
    
    async def build_context(
        self,
        query: str,
        anchor_turn_id: Optional[str] = None,
        policy_ref: Optional[PolicyRef] = None,
        include_slice: bool = True,
        include_rag: bool = True,
        max_messages: int = 10,
        max_results: int = 5
    ) -> UnifiedContext:
        """Build unified context from all available sources."""
        
        start_time = datetime.utcnow()
        context = UnifiedContext()
        
        # 1. Local memory (always available)
        context.recent_messages = self.memory.get_recent_messages(limit=max_messages)
        context.known_facts = self.memory.get_context_by_category("fact", limit=10)
        context.known_preferences = self.memory.get_context_by_category("preference", limit=10)
        context.patterns = self.memory.get_context_by_category("pattern", limit=5)
        context.sources_used.append("local_memory")
        
        # 2. Graph Kernel (if available and requested)
        if include_slice and anchor_turn_id:
            if self._gk_available is None:
                await self.graph_kernel.health_check()
                self._gk_available = self.graph_kernel.available
            
            if self._gk_available:
                try:
                    # Get slice
                    slice_export = await self.graph_kernel.get_slice(
                        anchor_turn_id, policy_ref
                    )
                    if slice_export:
                        context.slice_export = slice_export
                        context.sources_used.append("graph_kernel")
                    
                    # Get related knowledge
                    # Extract key terms from query for knowledge lookup
                    # (simplified - could use NLP here)
                    words = query.split()[:3]
                    for word in words:
                        if len(word) > 3:
                            triples = await self.graph_kernel.query_knowledge(
                                subject=word, limit=5
                            )
                            context.knowledge_triples.extend(triples)
                except Exception as e:
                    print(f"Graph Kernel retrieval failed: {e}")
        
        # 3. RAG++ (if available and requested)
        if include_rag:
            if self._rag_available is None:
                await self.rag.health_check()
                self._rag_available = self.rag.available
            
            if self._rag_available:
                try:
                    if context.slice_export and anchor_turn_id:
                        # Slice-scoped search
                        slice_results = await self.rag.search_slice(
                            query=query,
                            anchor_turn_id=anchor_turn_id,
                            policy_ref=policy_ref,
                            limit=max_results
                        )
                        if slice_results:
                            context.retrieved_results = slice_results.results
                            context.retrieval_mode = "slice"
                            context.sources_used.append("rag_slice")
                    else:
                        # Global search
                        global_results = await self.rag.search_global(
                            query=query,
                            limit=max_results
                        )
                        if global_results:
                            context.retrieved_results = global_results.results
                            context.retrieval_mode = "global"
                            context.sources_used.append("rag_global")
                except Exception as e:
                    print(f"RAG++ retrieval failed: {e}")
        
        # Calculate build time
        end_time = datetime.utcnow()
        context.build_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Set final retrieval mode
        if len(context.sources_used) > 1:
            context.retrieval_mode = "hybrid"
        elif "local_memory" in context.sources_used:
            context.retrieval_mode = "local"
        
        return context
    
    async def sync_learnings_to_graph_kernel(
        self,
        learnings: Dict[str, List[Dict]]
    ) -> int:
        """Sync extracted learnings to Graph Kernel as knowledge triples."""
        if not self._gk_available:
            if not await self.graph_kernel.health_check():
                return 0
        
        triples = []
        
        # Convert facts to triples
        for fact in learnings.get("facts", []):
            triples.append(KnowledgeTriple(
                subject=fact["key"],
                predicate="is",
                object=str(fact["value"]),
                confidence=0.7,
                source="kimi-synthesis"
            ))
        
        # Convert preferences to triples
        for pref in learnings.get("preferences", []):
            triples.append(KnowledgeTriple(
                subject="user",
                predicate=f"prefers_{pref['key']}",
                object=str(pref["value"]),
                confidence=0.8,
                source="kimi-synthesis"
            ))
        
        # Convert patterns to triples
        for pattern in learnings.get("patterns", []):
            triples.append(KnowledgeTriple(
                subject="user_behavior",
                predicate="exhibits",
                object=f"{pattern['key']}: {pattern['value']}",
                confidence=0.6,
                source="kimi-synthesis"
            ))
        
        if triples:
            return await self.graph_kernel.add_knowledge_batch(triples)
        return 0


# Singleton
_retriever: Optional[UnifiedRetriever] = None

def get_unified_retriever() -> UnifiedRetriever:
    global _retriever
    if _retriever is None:
        _retriever = UnifiedRetriever()
    return _retriever


async def build_rich_context(
    query: str,
    anchor_turn_id: Optional[str] = None
) -> UnifiedContext:
    """Convenience function to build rich context."""
    retriever = get_unified_retriever()
    return await retriever.build_context(query, anchor_turn_id)
