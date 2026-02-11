"""
Research Engine — Deep automated research for dream evolution.

Full loop: Dream → Research → Analysis → Report → New Seeds
Triggered by the evolution pipeline when dreams reach thresholds.

Research depth levels:
  - SCOUT: Quick web scan, 2-3 sources (strength < 0.4)
  - DEEP: Multi-query research, 10+ sources, competitive analysis (strength 0.4-0.7)
  - HEAVY: Full report — market analysis, technical deep-dive, feasibility scoring,
           prior art search, implementation roadmap (strength 0.7+ or bloom)
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from enum import Enum

from .brave_search import BraveSearchClient
from .report_generator import ReportGenerator


RESEARCH_DIR = Path("research/reports")
RESEARCH_STATE = Path("state/research.json")
RESEARCH_SEEDS_DIR = Path("dreams")  # Feed seeds back into dream garden


class ResearchDepth(str, Enum):
    SCOUT = "scout"       # Quick scan
    DEEP = "deep"         # Multi-source analysis
    HEAVY = "heavy"       # Full report with everything


class ResearchTrigger(str, Enum):
    EVOLUTION = "evolution"        # Dream evolved past threshold
    BLOOM = "bloom"                # Dream bloomed
    STAGE_CHANGE = "stage_change"  # Dream changed stage
    MANUAL = "manual"              # Manual trigger
    SEED = "seed"                  # New seed planted
    SYNTHESIS = "synthesis"        # Kimi synthesis detected research-worthy topic


class ResearchEngine:
    """
    Autonomous research engine that investigates dream topics.
    
    Flow:
    1. Receive dream context + trigger
    2. Generate research queries from dream essence
    3. Execute multi-wave search (Brave API)
    4. Fetch and extract key content from top results
    5. Synthesize findings via Kimi-K2
    6. Generate structured report
    7. Score feasibility, novelty, market fit
    8. Extract new dream seeds from research
    9. Post findings to Discord
    10. Feed seeds back to dream garden
    """
    
    def __init__(
        self,
        brave_api_key: Optional[str] = None,
        together_api_key: Optional[str] = None,
    ):
        self.brave = BraveSearchClient(api_key=brave_api_key)
        self.report_gen = ReportGenerator(api_key=together_api_key)
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load research state tracking."""
        if RESEARCH_STATE.exists():
            with open(RESEARCH_STATE) as f:
                return json.load(f)
        return {
            "researched_dreams": {},  # dream_id -> last_research_info
            "total_reports": 0,
            "total_seeds_generated": 0,
            "total_sources_processed": 0,
            "research_log": [],
        }
    
    def _save_state(self):
        """Persist research state."""
        RESEARCH_STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(RESEARCH_STATE, "w") as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def should_research(
        self,
        dream_id: str,
        dream_strength: float,
        trigger: ResearchTrigger,
        stage: str = None,
    ) -> tuple[bool, ResearchDepth]:
        """
        Decide if a dream needs research and at what depth.
        
        Returns (should_research, depth).
        """
        # Always research blooms at heavy depth
        if trigger == ResearchTrigger.BLOOM:
            return True, ResearchDepth.HEAVY
        
        # Manual triggers always go
        if trigger == ResearchTrigger.MANUAL:
            return True, ResearchDepth.HEAVY
        
        # Check cooldown — don't re-research too often
        last_research = self.state["researched_dreams"].get(dream_id, {})
        if last_research:
            last_time = datetime.fromisoformat(last_research.get("timestamp", "2000-01-01"))
            cooldown = {
                ResearchDepth.SCOUT: timedelta(hours=2),
                ResearchDepth.DEEP: timedelta(hours=12),
                ResearchDepth.HEAVY: timedelta(days=2),
            }
            last_depth = ResearchDepth(last_research.get("depth", "scout"))
            if datetime.utcnow() - last_time < cooldown.get(last_depth, timedelta(hours=2)):
                return False, ResearchDepth.SCOUT
        
        # Depth based on strength
        if dream_strength >= 0.7 or stage == "flowering":
            return True, ResearchDepth.HEAVY
        elif dream_strength >= 0.4 or stage == "growing":
            return True, ResearchDepth.DEEP
        elif dream_strength >= 0.2 or trigger == ResearchTrigger.SEED:
            return True, ResearchDepth.SCOUT
        
        # Stage change always triggers at least a scout
        if trigger == ResearchTrigger.STAGE_CHANGE:
            return True, ResearchDepth.DEEP
        
        return False, ResearchDepth.SCOUT
    
    def research_dream(
        self,
        dream_id: str,
        dream_title: str,
        dream_essence: str,
        dream_context: str = "",
        dream_tags: list[str] = None,
        dream_strength: float = 0.0,
        connections: list[dict] = None,
        depth: ResearchDepth = ResearchDepth.DEEP,
        trigger: ResearchTrigger = ResearchTrigger.EVOLUTION,
    ) -> dict:
        """
        Execute full research cycle on a dream.
        
        Returns structured research report with:
        - findings: synthesized research results
        - sources: all sources consulted
        - feasibility: technical feasibility score
        - novelty: how novel the idea is
        - market_fit: market opportunity score
        - implementation_roadmap: suggested steps
        - new_seeds: dream seeds extracted from research
        - report_path: path to saved report
        """
        print(f"  🔬 Researching [{depth.value}]: {dream_title}")
        
        dream_tags = dream_tags or []
        connections = connections or []
        
        # Step 1: Generate research queries
        queries = self.report_gen.generate_research_queries(
            title=dream_title,
            essence=dream_essence,
            context=dream_context,
            tags=dream_tags,
            depth=depth,
        )
        print(f"    Generated {len(queries)} research queries")
        
        # Step 2: Execute multi-wave search
        all_results = []
        seen_urls = set()
        
        for i, query in enumerate(queries):
            print(f"    Searching [{i+1}/{len(queries)}]: {query[:60]}...")
            results = self.brave.search(
                query=query,
                count=self._results_per_query(depth),
                freshness=self._freshness_for_depth(depth),
            )
            for r in results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)
        
        print(f"    Found {len(all_results)} unique sources")
        
        # Step 3: Fetch and extract content from top sources
        enriched_sources = []
        max_fetch = self._max_fetch_for_depth(depth)
        
        # Rank by relevance and fetch top N
        ranked = self._rank_results(all_results, dream_title, dream_essence)[:max_fetch]
        
        for result in ranked:
            content = self.brave.fetch_page_content(result["url"])
            if content:
                enriched_sources.append({
                    **result,
                    "content": content[:8000],  # Truncate for context window
                })
            else:
                enriched_sources.append(result)
        
        print(f"    Enriched {len([s for s in enriched_sources if 'content' in s])} sources with full content")
        
        # Step 4: Synthesize findings
        report = self.report_gen.synthesize_research(
            dream_title=dream_title,
            dream_essence=dream_essence,
            dream_context=dream_context,
            dream_tags=dream_tags,
            dream_strength=dream_strength,
            sources=enriched_sources,
            connections=connections,
            depth=depth,
        )
        
        # Step 5: Extract new dream seeds from research
        new_seeds = self.report_gen.extract_dream_seeds(
            dream_title=dream_title,
            research_findings=report.get("synthesis", ""),
            sources=enriched_sources,
        )
        report["new_seeds"] = new_seeds
        
        # Step 6: Save report
        report_path = self._save_report(dream_id, dream_title, report, depth)
        report["report_path"] = str(report_path)
        
        # Step 7: Update state
        self.state["researched_dreams"][dream_id] = {
            "timestamp": datetime.utcnow().isoformat(),
            "depth": depth.value,
            "trigger": trigger.value,
            "sources_found": len(all_results),
            "report_path": str(report_path),
            "seeds_generated": len(new_seeds),
        }
        self.state["total_reports"] += 1
        self.state["total_seeds_generated"] += len(new_seeds)
        self.state["total_sources_processed"] += len(all_results)
        self.state["research_log"].append({
            "dream_id": dream_id,
            "dream_title": dream_title,
            "depth": depth.value,
            "trigger": trigger.value,
            "timestamp": datetime.utcnow().isoformat(),
            "sources": len(all_results),
            "seeds": len(new_seeds),
        })
        # Keep log manageable
        if len(self.state["research_log"]) > 200:
            self.state["research_log"] = self.state["research_log"][-100:]
        
        self._save_state()
        
        print(f"    ✅ Report saved: {report_path}")
        print(f"    🌰 {len(new_seeds)} new seeds extracted")
        
        return report
    
    def _results_per_query(self, depth: ResearchDepth) -> int:
        """How many search results per query."""
        return {
            ResearchDepth.SCOUT: 5,
            ResearchDepth.DEEP: 10,
            ResearchDepth.HEAVY: 10,
        }[depth]
    
    def _freshness_for_depth(self, depth: ResearchDepth) -> Optional[str]:
        """Search freshness filter by depth."""
        return {
            ResearchDepth.SCOUT: "py",     # Past year
            ResearchDepth.DEEP: None,       # All time
            ResearchDepth.HEAVY: None,      # All time
        }[depth]
    
    def _max_fetch_for_depth(self, depth: ResearchDepth) -> int:
        """Max pages to fetch full content from."""
        return {
            ResearchDepth.SCOUT: 3,
            ResearchDepth.DEEP: 8,
            ResearchDepth.HEAVY: 15,
        }[depth]
    
    def _rank_results(self, results: list[dict], title: str, essence: str) -> list[dict]:
        """Simple relevance ranking — keywords from title/essence in snippet."""
        keywords = set(
            (title + " " + essence).lower().split()
        ) - {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "is", "it"}
        
        def score(r):
            text = (r.get("title", "") + " " + r.get("snippet", "")).lower()
            return sum(1 for kw in keywords if kw in text)
        
        return sorted(results, key=score, reverse=True)
    
    def _save_report(self, dream_id: str, dream_title: str, report: dict, depth: ResearchDepth) -> Path:
        """Save research report to file."""
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        safe_title = dream_title.lower().replace(" ", "-")[:40]
        filename = f"{timestamp}_{safe_title}_{depth.value}.json"
        
        report_path = RESEARCH_DIR / filename
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Also save a markdown version for humans
        md_path = RESEARCH_DIR / filename.replace(".json", ".md")
        md_content = self._report_to_markdown(dream_title, report, depth)
        with open(md_path, "w") as f:
            f.write(md_content)
        
        return report_path
    
    def _report_to_markdown(self, title: str, report: dict, depth: ResearchDepth) -> str:
        """Convert report to readable markdown."""
        md = f"""# 🔬 Research Report: {title}

**Depth:** {depth.value.upper()}
**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
**Sources:** {len(report.get('sources', []))}

---

## Executive Summary
{report.get('synthesis', 'No synthesis available.')}

## Feasibility Assessment
- **Technical Feasibility:** {report.get('feasibility', {}).get('technical', 'N/A')}/10
- **Market Opportunity:** {report.get('feasibility', {}).get('market', 'N/A')}/10
- **Novelty Score:** {report.get('feasibility', {}).get('novelty', 'N/A')}/10
- **Implementation Complexity:** {report.get('feasibility', {}).get('complexity', 'N/A')}/10
- **Overall Score:** {report.get('feasibility', {}).get('overall', 'N/A')}/10

## Key Findings
"""
        for i, finding in enumerate(report.get("key_findings", []), 1):
            md += f"\n### {i}. {finding.get('title', 'Finding')}\n{finding.get('detail', '')}\n"
        
        md += "\n## Competitive Landscape\n"
        for comp in report.get("competitors", []):
            md += f"- **{comp.get('name', 'Unknown')}**: {comp.get('description', '')}\n"
        
        md += "\n## Implementation Roadmap\n"
        for step in report.get("roadmap", []):
            md += f"- [ ] **{step.get('phase', 'Phase')}**: {step.get('description', '')}\n"
        
        md += "\n## Prior Art\n"
        for art in report.get("prior_art", []):
            md += f"- [{art.get('title', 'Source')}]({art.get('url', '#')}) — {art.get('relevance', '')}\n"
        
        md += "\n## New Dream Seeds Extracted\n"
        for seed in report.get("new_seeds", []):
            md += f"- 🌰 **{seed.get('title', 'Seed')}**: {seed.get('essence', '')}\n"
        
        md += f"\n---\n*Generated by Dream Weaver Research Engine*\n"
        return md
    
    def plant_research_seeds(self, seeds: list[dict], source_dream_id: str) -> list[str]:
        """
        Plant new dream seeds extracted from research back into the garden.
        
        Returns list of created file paths.
        """
        created = []
        RESEARCH_SEEDS_DIR.mkdir(parents=True, exist_ok=True)
        
        for seed in seeds:
            if seed.get("energy", 0) < 0.4:
                continue  # Skip low-energy seeds
            
            title = seed.get("title", "Untitled Research Seed")
            safe_name = title.lower().replace(" ", "-").replace("'", "").replace('"', '')
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")[:60]
            filepath = RESEARCH_SEEDS_DIR / f"{safe_name}.md"
            
            # Don't overwrite existing dreams
            if filepath.exists():
                continue
            
            content = f"""# {title}

## Essence
{seed.get('essence', '')}

## Context
Discovered through automated research on dream [{source_dream_id}].
{seed.get('context', '')}

## Tags
{', '.join(seed.get('tags', ['auto-research']))}

## Metadata
- Source: auto-research
- Parent Dream: {source_dream_id}
- Energy: {seed.get('energy', 0.5)}
- Planted: {datetime.utcnow().isoformat()}Z
"""
            filepath.write_text(content)
            created.append(str(filepath))
            print(f"    🌰 Planted: {title}")
        
        return created
