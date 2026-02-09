"""Kimi-K2 Memory Module - Persistent context and knowledge storage.

Components:
- MemoryStore: SQLite-backed message, synthesis, and context storage
- GraphKernelClient: Connects to Comp-Core's cc-graph-kernel
- RAGPlusPlusClient: Connects to Comp-Core's cc-rag-plus-plus
- UnifiedRetriever: Combines all sources for rich context building
"""

from .store import MemoryStore, get_store
from .graph_kernel_client import (
    GraphKernelClient, get_graph_kernel_client,
    SliceExport, PolicyRef, KnowledgeTriple
)
from .rag_client import (
    RAGPlusPlusClient, get_rag_client,
    SearchResult, SliceScopedResults, GlobalResults, RetrievalProvenance
)
from .unified_retriever import (
    UnifiedRetriever, get_unified_retriever,
    UnifiedContext, build_rich_context
)

__all__ = [
    # Store
    "MemoryStore", "get_store",
    # Graph Kernel
    "GraphKernelClient", "get_graph_kernel_client",
    "SliceExport", "PolicyRef", "KnowledgeTriple",
    # RAG++
    "RAGPlusPlusClient", "get_rag_client",
    "SearchResult", "SliceScopedResults", "GlobalResults", "RetrievalProvenance",
    # Unified
    "UnifiedRetriever", "get_unified_retriever",
    "UnifiedContext", "build_rich_context",
]
