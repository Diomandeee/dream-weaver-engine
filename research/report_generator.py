"""
Report Generator — Kimi-K2 powered research synthesis.

Takes raw search results + dream context and produces:
- Research queries (from dream essence)
- Synthesized findings
- Feasibility scoring
- Competitive landscape
- Implementation roadmap
- New dream seeds from research
"""

import json
import os
from typing import Optional

from together import Together


MODEL = "moonshotai/Kimi-K2-Thinking"


class ReportGenerator:
    """Generates research reports using Kimi-K2-Thinking."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY not set")
        self.client = Together(api_key=self.api_key)
    
    def _call_kimi(
        self,
        prompt: str,
        system: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call Kimi-K2-Thinking."""
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    def _parse_json(self, text: str) -> dict:
        """Extract JSON from model output."""
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            return {}
    
    def generate_research_queries(
        self,
        title: str,
        essence: str,
        context: str = "",
        tags: list[str] = None,
        depth: str = "deep",
    ) -> list[str]:
        """
        Generate research queries from dream context.
        
        Returns list of search queries optimized for different research angles.
        """
        tags = tags or []
        
        query_counts = {
            "scout": 3,
            "deep": 7,
            "heavy": 12,
        }
        count = query_counts.get(depth, 7)
        
        system = """You are a research query strategist. Given a dream/idea, generate 
diverse search queries that will uncover:
1. Prior art and existing solutions
2. Technical feasibility and approaches
3. Market landscape and competitors
4. Academic research and papers
5. Community discussions and opinions
6. Implementation patterns and architectures
7. Potential pitfalls and failure modes

Output a JSON array of query strings. Each query should target a DIFFERENT angle.
Be specific — generic queries waste API calls."""

        prompt = f"""# Dream to Research

**Title:** {title}
**Essence:** {essence}
**Context:** {context}
**Tags:** {', '.join(tags)}

Generate exactly {count} diverse, specific search queries.
Output JSON array of strings only."""

        result = self._call_kimi(prompt, system, max_tokens=1024, temperature=0.8)
        queries = self._parse_json(result)
        
        if isinstance(queries, list):
            return queries[:count]
        
        # Fallback: generate basic queries
        return [
            f"{title} {essence[:50]}",
            f"{title} implementation architecture",
            f"{title} alternatives competitors",
        ][:count]
    
    def synthesize_research(
        self,
        dream_title: str,
        dream_essence: str,
        dream_context: str,
        dream_tags: list[str],
        dream_strength: float,
        sources: list[dict],
        connections: list[dict],
        depth: str = "deep",
    ) -> dict:
        """
        Synthesize all research sources into a structured report.
        
        Returns dict with synthesis, feasibility, competitors, roadmap, prior_art, key_findings.
        """
        # Format sources for context
        sources_text = self._format_sources(sources)
        connections_text = "\n".join([
            f"- {c.get('title', 'Connected Dream')}: {c.get('essence', '')[:100]}"
            for c in connections
        ]) or "No connected dreams."
        
        system = f"""You are a senior research analyst producing a {'comprehensive' if depth == 'heavy' else 'focused'} research report.

Your output MUST be valid JSON with this exact structure:
{{
  "synthesis": "Executive summary of all findings (3-5 paragraphs for heavy, 1-2 for scout)",
  "key_findings": [
    {{"title": "Finding title", "detail": "Detailed explanation", "confidence": 0.0-1.0, "source_urls": ["url1"]}}
  ],
  "feasibility": {{
    "technical": 1-10,
    "market": 1-10,
    "novelty": 1-10,
    "complexity": 1-10,
    "overall": 1-10,
    "reasoning": "Why these scores"
  }},
  "competitors": [
    {{"name": "...", "url": "...", "description": "...", "strengths": "...", "weaknesses": "...", "differentiation": "How dream differs"}}
  ],
  "prior_art": [
    {{"title": "...", "url": "...", "relevance": "How it relates", "year": "..."}}
  ],
  "roadmap": [
    {{"phase": "Phase 1: ...", "description": "...", "effort": "days/weeks/months", "dependencies": ["..."]}}
  ],
  "risks": [
    {{"risk": "...", "severity": "low/medium/high", "mitigation": "..."}}
  ],
  "opportunities": ["Unexpected opportunities discovered"],
  "recommended_strength_delta": 0.0-0.2,
  "recommended_tags": ["new", "tags", "from", "research"]
}}

Be brutally honest. Don't inflate scores. Real analysis > cheerleading."""

        prompt = f"""# Dream Under Research

**Title:** {dream_title}
**Essence:** {dream_essence}
**Context:** {dream_context}
**Tags:** {', '.join(dream_tags)}
**Current Strength:** {dream_strength}

# Connected Dreams
{connections_text}

# Research Sources ({len(sources)} found)

{sources_text}

# Task
Synthesize ALL sources into a structured research report.
Depth: {depth.upper()}
Be thorough. Cite specific sources. Score honestly.
Output JSON only."""

        max_tokens = {
            "scout": 2048,
            "deep": 4096,
            "heavy": 8192,
        }.get(depth, 4096)
        
        result = self._call_kimi(prompt, system, max_tokens=max_tokens, temperature=0.6)
        parsed = self._parse_json(result)
        
        if not parsed:
            # Fallback minimal report
            parsed = {
                "synthesis": f"Research on '{dream_title}' found {len(sources)} sources but synthesis parsing failed. Raw findings available in source data.",
                "key_findings": [],
                "feasibility": {"technical": 5, "market": 5, "novelty": 5, "complexity": 5, "overall": 5, "reasoning": "Unable to parse full analysis"},
                "competitors": [],
                "prior_art": [],
                "roadmap": [],
                "risks": [],
                "opportunities": [],
                "recommended_strength_delta": 0.05,
                "recommended_tags": [],
            }
        
        # Attach source metadata
        parsed["sources"] = [
            {"title": s.get("title", ""), "url": s.get("url", ""), "snippet": s.get("snippet", "")}
            for s in sources
        ]
        
        return parsed
    
    def extract_dream_seeds(
        self,
        dream_title: str,
        research_findings: str,
        sources: list[dict],
    ) -> list[dict]:
        """
        Extract new dream seeds from research findings.
        
        These are adjacent ideas, gaps in the market, or unexpected connections
        discovered during research that deserve their own incubation.
        """
        system = """You are a creative ideation engine. Given research findings about a dream/idea,
extract NEW dream seeds — adjacent ideas, gaps discovered, unexpected connections,
or innovations that emerged from the research.

These should be genuinely NEW ideas, not reformulations of the original dream.

Output JSON array:
[
  {
    "title": "Short catchy title",
    "essence": "Core idea in 2-3 sentences",
    "context": "How this connects to the original research",
    "energy": 0.0-1.0 (how promising is this?),
    "tags": ["tag1", "tag2"]
  }
]

Generate 2-5 seeds. Quality over quantity. Skip if nothing genuinely new emerges."""

        # Truncate sources for context
        source_summaries = "\n".join([
            f"- {s.get('title', '')}: {s.get('snippet', '')[:150]}"
            for s in sources[:10]
        ])
        
        prompt = f"""# Original Dream: {dream_title}

# Research Findings
{research_findings[:4000]}

# Key Sources
{source_summaries}

# Task
Extract 2-5 NEW dream seeds from this research. 
These should be adjacent ideas or gaps discovered — NOT the original idea restated.
Output JSON array only."""

        result = self._call_kimi(prompt, system, max_tokens=2048, temperature=0.85)
        seeds = self._parse_json(result)
        
        if isinstance(seeds, list):
            return seeds
        return []
    
    def _format_sources(self, sources: list[dict]) -> str:
        """Format sources for model context."""
        parts = []
        for i, source in enumerate(sources, 1):
            part = f"### Source {i}: {source.get('title', 'Untitled')}\n"
            part += f"**URL:** {source.get('url', '')}\n"
            part += f"**Snippet:** {source.get('snippet', '')}\n"
            if source.get("content"):
                # Include extracted content (truncated)
                part += f"**Full Content (excerpt):**\n{source['content'][:3000]}\n"
            if source.get("extra_snippets"):
                part += f"**Additional:** {' | '.join(source['extra_snippets'][:3])}\n"
            parts.append(part)
        
        return "\n---\n".join(parts)
    
    def format_discord_report(
        self,
        dream_title: str,
        report: dict,
        depth: str = "deep",
    ) -> dict:
        """
        Format report as a Discord embed.
        
        Returns dict suitable for Discord webhook.
        """
        feasibility = report.get("feasibility", {})
        overall = feasibility.get("overall", "?")
        
        # Color based on overall score
        if isinstance(overall, (int, float)):
            if overall >= 7:
                color = 0x00FF00  # Green - strong
            elif overall >= 5:
                color = 0xFFAA00  # Orange - moderate
            else:
                color = 0xFF4444  # Red - weak
        else:
            color = 0x7B68EE  # Medium slate blue
        
        # Key findings summary
        findings_text = "\n".join([
            f"• **{f.get('title', 'Finding')}** ({f.get('confidence', '?')})"
            for f in report.get("key_findings", [])[:5]
        ]) or "No key findings."
        
        # Competitor summary
        comp_text = "\n".join([
            f"• **{c.get('name', '?')}** — {c.get('description', '')[:80]}"
            for c in report.get("competitors", [])[:4]
        ]) or "None identified."
        
        # Seeds
        seeds_text = "\n".join([
            f"• 🌰 {s.get('title', 'Seed')} ({s.get('energy', '?')})"
            for s in report.get("new_seeds", [])[:5]
        ]) or "None extracted."
        
        embed = {
            "title": f"🔬 Research Report: {dream_title}",
            "description": report.get("synthesis", "")[:2000],
            "color": color,
            "fields": [
                {
                    "name": "📊 Feasibility",
                    "value": (
                        f"Technical: {feasibility.get('technical', '?')}/10 | "
                        f"Market: {feasibility.get('market', '?')}/10 | "
                        f"Novelty: {feasibility.get('novelty', '?')}/10\n"
                        f"**Overall: {overall}/10**"
                    ),
                    "inline": False,
                },
                {
                    "name": "🔍 Key Findings",
                    "value": findings_text[:1024],
                    "inline": False,
                },
                {
                    "name": "⚔️ Competitors",
                    "value": comp_text[:1024],
                    "inline": False,
                },
                {
                    "name": "🌰 New Seeds",
                    "value": seeds_text[:1024],
                    "inline": False,
                },
            ],
            "footer": {
                "text": f"Depth: {depth.upper()} | Sources: {len(report.get('sources', []))} | Dream Weaver Research Engine"
            },
        }
        
        return embed
