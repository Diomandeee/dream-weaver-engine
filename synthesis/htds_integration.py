"""
HTDS Integration Layer — Wires the Hierarchical Topological Data Structure
into the live Kimi K2 synthesis, Dream Weaver, and RAG++ pipelines.

Consumers:
  1. Synthesizer: domain-aware context enrichment  
  2. Dream Weaver: high-density session → dream seeds
  3. RAG++ Bridge: density-filtered ingestion (skip noise)
  4. Chronicles: backwards trajectory content ranking
  5. Prompt Synthesizer: real-time topology-weighted context

This module is imported by each pipeline to access HTDS data.
"""

import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

HTDS_DB = Path.home() / ".clawdbot/context-ledger/htds.db"
QUALITY_DB = Path.home() / ".clawdbot/context-ledger/quality.db"

# ═══════════════════════════════════════════════════════════════
# HTDS Client
# ═══════════════════════════════════════════════════════════════

class HTDSClient:
    """Read-only client for querying HTDS from any pipeline."""
    
    def __init__(self, db_path: Path = HTDS_DB):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
    
    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if not self._db_path.exists():
                raise FileNotFoundError(f"HTDS not built yet: {self._db_path}")
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
    
    # ─── Domain queries ──────────────────────────────────────────
    
    def get_domains(self) -> List[Dict]:
        """Get all domain nodes with stats."""
        rows = self.conn.execute("""
            SELECT label, density_score, freshness, signal_ratio, 
                   total_leaf_count, child_count, metadata
            FROM nodes WHERE level = 'domain'
            ORDER BY density_score * total_leaf_count DESC
        """).fetchall()
        return [dict(r) for r in rows]
    
    def get_domain_for_content(self, text: str) -> Optional[str]:
        """Classify text into a domain based on keyword matching."""
        from collections import Counter
        
        DOMAIN_KEYWORDS = {
            "dream-garden": ["dream", "garden", "bloom", "incubat", "seed", "metamorpho"],
            "comp-core": ["comp-core", "kernel", "rag++", "trajectory", "graph kernel"],
            "nko-linguistics": ["n'ko", "nko", "n ko", "linguistic", "transliter", "bamanan"],
            "app-development": ["bwb", "milk men", "serenity", "meaningful power", "swiftui"],
            "tie-evolution": ["tie", "evoflow", "evolution", "hef", "generation"],
            "meta-process": ["meta", "recursion", "chronicle", "reflection"],
            "tooling": ["pulse", "spore", "skill", "clawdbot", "agent"],
            "litrpg": ["litrpg", "eternal serenity", "innerlands"],
        }
        
        text_lower = text.lower()
        scores = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits > 0:
                scores[domain] = hits
        
        if scores:
            return max(scores, key=scores.get)
        return None
    
    def get_domain_context(self, domain: str) -> Dict:
        """Get full context for a domain: density, freshness, leaf count."""
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE level = 'domain' AND label = ?",
            (domain,)
        ).fetchone()
        return dict(row) if row else {}
    
    # ─── Session queries ─────────────────────────────────────────
    
    def get_high_density_sessions(self, limit: int = 20) -> List[Dict]:
        """Get sessions ranked by density × freshness for dream seeding."""
        rows = self.conn.execute("""
            SELECT id, label, density_score, freshness, signal_ratio, 
                   total_leaf_count, metadata
            FROM nodes 
            WHERE level = 'session' 
              AND density_tier IN ('high', 'substantial')
              AND freshness > 0.1
            ORDER BY density_score * freshness * signal_ratio DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    
    def get_session_density(self, session_id: str) -> Optional[str]:
        """Check if a session is worth ingesting (returns density tier or None)."""
        row = self.conn.execute(
            "SELECT density_tier FROM nodes WHERE id = ?",
            (f"L2:{session_id}",)
        ).fetchone()
        return row["density_tier"] if row else None
    
    # ─── Leaf queries ────────────────────────────────────────────
    
    def is_message_signal(self, message_rowid: int) -> bool:
        """Check if a message passed pruning (is in HTDS as a leaf)."""
        row = self.conn.execute(
            "SELECT 1 FROM nodes WHERE id = ? AND level = 'leaf'",
            (f"L0:{message_rowid}",)
        ).fetchone()
        return row is not None
    
    def get_message_density(self, message_rowid: int) -> Optional[float]:
        """Get the density score of a specific message."""
        row = self.conn.execute(
            "SELECT density_score FROM nodes WHERE id = ?",
            (f"L0:{message_rowid}",)
        ).fetchone()
        return row["density_score"] if row else None
    
    # ─── Topology queries ────────────────────────────────────────
    
    def get_manifold_health(self) -> Dict:
        """Get root-level health metrics."""
        row = self.conn.execute(
            "SELECT density_score, freshness, signal_ratio, total_leaf_count, child_count "
            "FROM nodes WHERE level = 'root'"
        ).fetchone()
        if row:
            return {
                "density": row["density_score"],
                "freshness": row["freshness"],
                "signal_ratio": row["signal_ratio"],
                "total_leaves": row["total_leaf_count"],
                "domains": row["child_count"],
                "health": row["density_score"] * row["freshness"],
            }
        return {"error": "HTDS not built"}
    
    def get_ring_neighbors(self, node_id: str, radius: float = 0.5) -> List[Dict]:
        """Get nearby nodes on the IRCP ring."""
        row = self.conn.execute(
            "SELECT ring_position FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if not row:
            return []
        
        center = row["ring_position"]
        # Ring distance: min(|a-b|, 2π - |a-b|)
        rows = self.conn.execute("""
            SELECT id, label, density_score, ring_position,
                   MIN(ABS(ring_position - ?), 6.28318 - ABS(ring_position - ?)) as ring_dist
            FROM nodes 
            WHERE level = (SELECT level FROM nodes WHERE id = ?)
              AND id != ?
            HAVING ring_dist < ?
            ORDER BY ring_dist
            LIMIT 10
        """, (center, center, node_id, node_id, radius)).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# DENSITY FILTER (for RAG++ Bridge)
# ═══════════════════════════════════════════════════════════════

class DensityFilter:
    """Filters messages during RAG++ ingestion based on pruning audit.
    
    Used by clawdbot_bridge.py to skip noise before embedding/ingesting.
    """
    
    def __init__(self):
        self._quality_conn: Optional[sqlite3.Connection] = None
    
    @property
    def quality_conn(self) -> sqlite3.Connection:
        if self._quality_conn is None:
            self._quality_conn = sqlite3.connect(str(QUALITY_DB))
        return self._quality_conn
    
    def should_ingest(self, content: str, role: str = "assistant") -> Tuple[bool, str]:
        """Determine if a message is worth ingesting.
        
        Returns (should_ingest, reason).
        Uses heuristic classification matching the pruning audit logic.
        """
        if not content or len(content) < 10:
            return False, "empty"
        
        # Quick noise patterns
        noise_patterns = [
            "HEARTBEAT_OK", "NO_REPLY", "(no output)",
            "Successfully replaced", "Command still running",
            "Process exited", "Killed session",
        ]
        for p in noise_patterns:
            if content.strip().startswith(p):
                return False, f"noise:{p}"
        
        # Extract text from JSON if needed
        actual_text = content
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                texts = []
                for part in parsed:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            texts.append(part.get("text", ""))
                        elif part.get("type") == "thinking":
                            texts.append(part.get("thinking", ""))
                actual_text = "\n".join(texts)
        except (json.JSONDecodeError, TypeError):
            pass
        
        if len(actual_text) < 50:
            return False, "too_short"
        
        # Score for density indicators
        high_words = ['insight', 'pattern', 'decision', 'architecture', 
                     'design', 'philosophy', 'strategy', 'principle',
                     'lesson', 'breakthrough', 'framework', 'paradox']
        hits = sum(1 for w in high_words if w.lower() in actual_text.lower())
        
        if hits >= 2 and len(actual_text) > 300:
            return True, "high_density"
        elif len(actual_text) > 200:
            return True, "substantial"
        elif len(actual_text) > 100:
            return True, "moderate"
        else:
            return False, "low_density"
    
    def close(self):
        if self._quality_conn:
            self._quality_conn.close()
            self._quality_conn = None


# ═══════════════════════════════════════════════════════════════
# SYNTHESIS ENRICHMENT (for Kimi K2)
# ═══════════════════════════════════════════════════════════════

def get_domain_context_for_synthesis(message: str) -> str:
    """Get HTDS domain context to inject into K2 synthesis prompt.
    
    Returns a concise domain summary string for the synthesizer.
    """
    try:
        client = HTDSClient()
        domain = client.get_domain_for_content(message)
        
        if not domain:
            health = client.get_manifold_health()
            client.close()
            return f"[HTDS] Knowledge base: {health.get('total_leaves', 0):,} indexed messages across {health.get('domains', 0)} domains"
        
        ctx = client.get_domain_context(domain)
        health = client.get_manifold_health()
        client.close()
        
        if ctx:
            return (
                f"[HTDS Domain: {domain}] "
                f"density:{ctx.get('density_score', 0):.2f} "
                f"freshness:{ctx.get('freshness', 0):.2f} "
                f"leaves:{ctx.get('total_leaf_count', 0)} "
                f"sessions:{ctx.get('child_count', 0)} | "
                f"Global: {health.get('total_leaves', 0):,} indexed across {health.get('domains', 0)} domains"
            )
        
        return f"[HTDS] Domain '{domain}' detected but no topology data yet"
    except Exception as e:
        return f"[HTDS] unavailable: {e}"


# ═══════════════════════════════════════════════════════════════
# DREAM WEAVER FEED
# ═══════════════════════════════════════════════════════════════

def get_dream_seeds_from_htds(limit: int = 10) -> List[Dict]:
    """Extract high-density sessions as dream seed candidates.
    
    Called by Dream Weaver evolution pipeline.
    """
    try:
        client = HTDSClient()
        sessions = client.get_high_density_sessions(limit)
        client.close()
        
        seeds = []
        for s in sessions:
            meta = json.loads(s.get("metadata", "{}"))
            seeds.append({
                "source": "htds",
                "session_id": meta.get("session_id", ""),
                "strength": s["density_score"] * s["freshness"],
                "density": s["density_score"],
                "freshness": s["freshness"],
                "leaf_count": s["total_leaf_count"],
            })
        return seeds
    except Exception as e:
        return [{"error": str(e)}]


# ═══════════════════════════════════════════════════════════════
# CHRONICLES FEED  
# ═══════════════════════════════════════════════════════════════

def get_chronicles_content_ranking() -> List[Dict]:
    """Rank domains by content potential for backwards trajectory posts.
    
    Higher potential = more material × higher density × better signal ratio.
    """
    try:
        client = HTDSClient()
        domains = client.get_domains()
        client.close()
        
        ranking = []
        for d in domains:
            potential = d["density_score"] * d["total_leaf_count"] * d["signal_ratio"]
            ranking.append({
                "domain": d["label"],
                "content_potential": round(potential, 1),
                "density": d["density_score"],
                "depth": d["total_leaf_count"],
                "sessions": d["child_count"],
                "freshness": d["freshness"],
            })
        
        ranking.sort(key=lambda x: x["content_potential"], reverse=True)
        return ranking
    except Exception as e:
        return [{"error": str(e)}]


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_htds_client: Optional[HTDSClient] = None
_density_filter: Optional[DensityFilter] = None

def get_htds() -> HTDSClient:
    """Get singleton HTDS client."""
    global _htds_client
    if _htds_client is None:
        _htds_client = HTDSClient()
    return _htds_client

def get_density_filter() -> DensityFilter:
    """Get singleton density filter."""
    global _density_filter
    if _density_filter is None:
        _density_filter = DensityFilter()
    return _density_filter
