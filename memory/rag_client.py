"""RAG++ Client for Kimi-K2 Memory Integration.

Connects to Comp-Core's cc-rag-plus-plus service for:
- Vector search
- Slice-scoped retrieval
- Dual-plane retrieval (raw + semantic)
"""

import os
import httpx
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .graph_kernel_client import SliceExport, PolicyRef


RAG_PLUS_PLUS_URL = os.environ.get("RAG_PLUS_PLUS_URL", "http://localhost:8000")


@dataclass
class RetrievalProvenance:
    """Full provenance chain for retrieved content."""
    query_id: str
    slice_id: Optional[str]  # None for global search
    anchor_turn_id: Optional[str]
    policy_ref: Optional[PolicyRef]
    retrieved_turn_ids: List[str]
    retrieval_mode: str  # "slice" or "global"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def is_admissible(self) -> bool:
        return self.retrieval_mode == "slice"


@dataclass
class SearchResult:
    """Single search result from RAG++."""
    turn_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Semantic artifacts (for dual-plane)
    atoms: List[Dict] = field(default_factory=list)
    proposals: List[Dict] = field(default_factory=list)


@dataclass
class SliceScopedResults:
    """Results from slice-scoped search."""
    results: List[SearchResult]
    provenance: RetrievalProvenance
    slice_export: SliceExport
    total_candidates: int = 0
    search_time_ms: float = 0


@dataclass
class GlobalResults:
    """Results from global search."""
    results: List[SearchResult]
    provenance: RetrievalProvenance
    total_candidates: int = 0
    search_time_ms: float = 0


class RAGPlusPlusClient:
    """Client for RAG++ REST API."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or RAG_PLUS_PLUS_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        self._available = None
    
    async def health_check(self) -> bool:
        """Check if RAG++ service is available."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            self._available = response.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False
    
    @property
    def available(self) -> bool:
        return self._available if self._available is not None else False
    
    # Search Operations
    
    async def search_slice(
        self,
        query: str,
        anchor_turn_id: str,
        policy_ref: Optional[PolicyRef] = None,
        limit: int = 10
    ) -> Optional[SliceScopedResults]:
        """Slice-conditioned search - retrieval within admissible slice."""
        try:
            payload = {
                "query": query,
                "anchor_turn_id": anchor_turn_id,
                "policy_ref": {
                    "id": policy_ref.id if policy_ref else "default",
                    "version": policy_ref.version if policy_ref else "v1"
                } if policy_ref else None,
                "limit": limit
            }
            response = await self.client.post(
                f"{self.base_url}/api/rag/search/slice",
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                
                results = [
                    SearchResult(
                        turn_id=r["turn_id"],
                        content=r["content"],
                        score=r["score"],
                        metadata=r.get("metadata", {}),
                        atoms=r.get("atoms", []),
                        proposals=r.get("proposals", [])
                    )
                    for r in data["results"]
                ]
                
                prov = data["provenance"]
                provenance = RetrievalProvenance(
                    query_id=prov["query_id"],
                    slice_id=prov.get("slice_id"),
                    anchor_turn_id=prov.get("anchor_turn_id"),
                    policy_ref=PolicyRef(
                        id=prov["policy_ref"]["id"],
                        version=prov["policy_ref"].get("version", "v1")
                    ) if prov.get("policy_ref") else None,
                    retrieved_turn_ids=prov["retrieved_turn_ids"],
                    retrieval_mode=prov["retrieval_mode"],
                    timestamp=prov.get("timestamp", datetime.utcnow().isoformat())
                )
                
                se = data["slice_export"]
                slice_export = SliceExport(
                    slice_id=se["slice_id"],
                    anchor_turn_id=se["anchor_turn_id"],
                    turn_ids=se.get("turn_ids", []),
                    edges=[],  # Simplified
                    policy_id=se["policy_id"],
                    policy_params_hash=se.get("policy_params_hash", ""),
                    schema_version=se.get("schema_version", "v1")
                )
                
                return SliceScopedResults(
                    results=results,
                    provenance=provenance,
                    slice_export=slice_export,
                    total_candidates=data.get("total_candidates", 0),
                    search_time_ms=data.get("search_time_ms", 0)
                )
        except Exception as e:
            print(f"Slice search failed: {e}")
        return None
    
    async def search_global(
        self,
        query: str,
        limit: int = 10
    ) -> Optional[GlobalResults]:
        """Global search - whole-fabric recall."""
        try:
            payload = {
                "query": query,
                "limit": limit
            }
            response = await self.client.post(
                f"{self.base_url}/api/rag/search/global",
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                
                results = [
                    SearchResult(
                        turn_id=r["turn_id"],
                        content=r["content"],
                        score=r["score"],
                        metadata=r.get("metadata", {})
                    )
                    for r in data["results"]
                ]
                
                prov = data["provenance"]
                provenance = RetrievalProvenance(
                    query_id=prov["query_id"],
                    slice_id=None,
                    anchor_turn_id=None,
                    policy_ref=None,
                    retrieved_turn_ids=prov["retrieved_turn_ids"],
                    retrieval_mode="global",
                    timestamp=prov.get("timestamp", datetime.utcnow().isoformat())
                )
                
                return GlobalResults(
                    results=results,
                    provenance=provenance,
                    total_candidates=data.get("total_candidates", 0),
                    search_time_ms=data.get("search_time_ms", 0)
                )
        except Exception as e:
            print(f"Global search failed: {e}")
        return None
    
    # Context Building
    
    async def get_slice_context(
        self,
        query: str,
        anchor_turn_id: str,
        policy_ref: Optional[PolicyRef] = None
    ) -> Optional[str]:
        """Generate context strictly within slice admissibility."""
        try:
            payload = {
                "query": query,
                "anchor_turn_id": anchor_turn_id,
                "policy_ref": {
                    "id": policy_ref.id if policy_ref else "default",
                    "version": policy_ref.version if policy_ref else "v1"
                } if policy_ref else None
            }
            response = await self.client.post(
                f"{self.base_url}/api/rag/context/slice",
                json=payload
            )
            if response.status_code == 200:
                return response.json().get("context", "")
        except Exception as e:
            print(f"Context request failed: {e}")
        return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton
_client: Optional[RAGPlusPlusClient] = None

def get_rag_client() -> RAGPlusPlusClient:
    global _client
    if _client is None:
        _client = RAGPlusPlusClient()
    return _client
