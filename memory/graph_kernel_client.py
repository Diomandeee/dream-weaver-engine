"""Graph Kernel Client for Kimi-K2 Memory Integration.

Connects to Comp-Core's cc-graph-kernel service for:
- Context slicing (admissibility filtering)
- Knowledge graph operations
- Policy resolution
"""

import os
import httpx
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


GRAPH_KERNEL_URL = os.environ.get("GRAPH_KERNEL_URL", "http://localhost:8001")


@dataclass
class PolicyRef:
    """Reference to a slice policy."""
    id: str
    version: str = "v1"
    params_hash: Optional[str] = None


@dataclass
class Edge:
    """Knowledge graph edge."""
    source: str
    target: str
    relation: str
    weight: float = 1.0


@dataclass
class SliceExport:
    """Exported context slice from Graph Kernel."""
    slice_id: str
    anchor_turn_id: str
    turn_ids: List[str]
    edges: List[Edge]
    policy_id: str
    policy_params_hash: str
    schema_version: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @property
    def turn_count(self) -> int:
        return len(self.turn_ids)
    
    def is_admissible(self, turn_id: str) -> bool:
        """Check if a turn is admissible within this slice."""
        return turn_id in self.turn_ids


@dataclass
class KnowledgeTriple:
    """Subject-predicate-object triple for knowledge graph."""
    subject: str
    predicate: str
    object: str
    confidence: float = 0.5
    source: str = "kimi-synthesis"


class GraphKernelClient:
    """Client for Graph Kernel REST API."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or GRAPH_KERNEL_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        self._available = None
    
    async def health_check(self) -> bool:
        """Check if Graph Kernel service is available."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            self._available = response.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False
    
    @property
    def available(self) -> bool:
        """Return cached availability status."""
        return self._available if self._available is not None else False
    
    # Slice Operations
    
    async def get_slice(
        self,
        anchor_turn_id: str,
        policy_ref: Optional[PolicyRef] = None
    ) -> Optional[SliceExport]:
        """Get context slice for an anchor turn."""
        try:
            payload = {
                "anchor_turn_id": anchor_turn_id,
                "policy_ref": {
                    "id": policy_ref.id if policy_ref else "default",
                    "version": policy_ref.version if policy_ref else "v1"
                }
            }
            response = await self.client.post(
                f"{self.base_url}/api/slice",
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                return SliceExport(
                    slice_id=data["slice_id"],
                    anchor_turn_id=data["anchor_turn_id"],
                    turn_ids=data["turn_ids"],
                    edges=[Edge(**e) for e in data.get("edges", [])],
                    policy_id=data["policy_id"],
                    policy_params_hash=data["policy_params_hash"],
                    schema_version=data["schema_version"]
                )
        except Exception as e:
            print(f"Slice request failed: {e}")
        return None
    
    async def get_slice_batch(
        self,
        anchor_turn_ids: List[str],
        policy_ref: Optional[PolicyRef] = None
    ) -> List[SliceExport]:
        """Batch slice construction for multiple anchors."""
        try:
            payload = {
                "anchors": anchor_turn_ids,
                "policy_ref": {
                    "id": policy_ref.id if policy_ref else "default",
                    "version": policy_ref.version if policy_ref else "v1"
                }
            }
            response = await self.client.post(
                f"{self.base_url}/api/slice/batch",
                json=payload
            )
            if response.status_code == 200:
                return [
                    SliceExport(
                        slice_id=d["slice_id"],
                        anchor_turn_id=d["anchor_turn_id"],
                        turn_ids=d["turn_ids"],
                        edges=[Edge(**e) for e in d.get("edges", [])],
                        policy_id=d["policy_id"],
                        policy_params_hash=d["policy_params_hash"],
                        schema_version=d["schema_version"]
                    )
                    for d in response.json()
                ]
        except Exception as e:
            print(f"Batch slice request failed: {e}")
        return []
    
    # Policy Operations
    
    async def list_policies(self) -> List[PolicyRef]:
        """List available slice policies."""
        try:
            response = await self.client.get(f"{self.base_url}/api/policies")
            if response.status_code == 200:
                return [
                    PolicyRef(id=p["id"], version=p.get("version", "v1"))
                    for p in response.json()
                ]
        except Exception:
            pass
        return []
    
    async def register_policy(self, policy: Dict[str, Any]) -> Optional[PolicyRef]:
        """Register a new slice policy."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/policies",
                json=policy
            )
            if response.status_code == 200:
                data = response.json()
                return PolicyRef(id=data["id"], version=data.get("version", "v1"))
        except Exception:
            pass
        return None
    
    # Knowledge Graph Operations
    
    async def add_knowledge(self, triple: KnowledgeTriple) -> bool:
        """Add a knowledge triple to the graph."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/knowledge",
                json={
                    "subject": triple.subject,
                    "predicate": triple.predicate,
                    "object": triple.object,
                    "confidence": triple.confidence,
                    "source": triple.source
                }
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def add_knowledge_batch(self, triples: List[KnowledgeTriple]) -> int:
        """Add multiple knowledge triples. Returns count of successful adds."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/knowledge/batch",
                json=[
                    {
                        "subject": t.subject,
                        "predicate": t.predicate,
                        "object": t.object,
                        "confidence": t.confidence,
                        "source": t.source
                    }
                    for t in triples
                ]
            )
            if response.status_code == 200:
                return response.json().get("added", 0)
        except Exception:
            pass
        return 0
    
    async def query_knowledge(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        limit: int = 50
    ) -> List[KnowledgeTriple]:
        """Query knowledge graph."""
        try:
            params = {"limit": limit}
            if subject:
                params["subject"] = subject
            if predicate:
                params["predicate"] = predicate
            
            response = await self.client.get(
                f"{self.base_url}/api/knowledge",
                params=params
            )
            if response.status_code == 200:
                return [
                    KnowledgeTriple(
                        subject=t["subject"],
                        predicate=t["predicate"],
                        object=t["object"],
                        confidence=t.get("confidence", 0.5),
                        source=t.get("source", "unknown")
                    )
                    for t in response.json()
                ]
        except Exception:
            pass
        return []
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton
_client: Optional[GraphKernelClient] = None

def get_graph_kernel_client() -> GraphKernelClient:
    global _client
    if _client is None:
        _client = GraphKernelClient()
    return _client


async def sync_knowledge_to_graph_kernel(triples: List[Dict]) -> int:
    """Convenience function to sync knowledge triples from Kimi-K2 to Graph Kernel."""
    client = get_graph_kernel_client()
    
    # Check availability
    if not await client.health_check():
        print("Graph Kernel not available, skipping sync")
        return 0
    
    # Convert to KnowledgeTriple objects
    kt_list = [
        KnowledgeTriple(
            subject=t["subject"],
            predicate=t["predicate"],
            object=t["object"],
            confidence=t.get("confidence", 0.5),
            source="kimi-synthesis"
        )
        for t in triples
    ]
    
    return await client.add_knowledge_batch(kt_list)
