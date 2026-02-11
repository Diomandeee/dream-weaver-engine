"""
Discord reporter for research findings.

Posts research reports to a dedicated #research channel via webhook.
"""

import os
import json
import requests
from datetime import datetime
from typing import Optional


class ResearchDiscordReporter:
    """Post research reports to Discord."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_RESEARCH")
    
    def _send(self, content: str = "", embed: dict = None, embeds: list = None):
        """Send to Discord webhook."""
        if not self.webhook_url:
            print("    [Discord] No DISCORD_WEBHOOK_RESEARCH configured, skipping")
            return False
        
        payload = {}
        if content:
            payload["content"] = content
        if embed:
            payload["embeds"] = [embed]
        elif embeds:
            payload["embeds"] = embeds[:10]  # Discord max 10 embeds
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"    [Discord] Failed to post: {e}")
            return False
    
    def post_research_report(
        self,
        dream_title: str,
        report: dict,
        depth: str,
        dream_id: str = "",
    ):
        """Post a full research report to Discord."""
        feasibility = report.get("feasibility", {})
        overall = feasibility.get("overall", "?")
        
        # Color based on score
        if isinstance(overall, (int, float)):
            color = 0x00FF00 if overall >= 7 else (0xFFAA00 if overall >= 5 else 0xFF4444)
        else:
            color = 0x7B68EE
        
        # Main embed - synthesis
        synthesis = report.get("synthesis", "No synthesis available.")
        if len(synthesis) > 4000:
            synthesis = synthesis[:3997] + "..."
        
        main_embed = {
            "title": f"🔬 Research: {dream_title}",
            "description": synthesis,
            "color": color,
            "fields": [
                {
                    "name": "📊 Scores",
                    "value": (
                        f"⚙️ Technical: **{feasibility.get('technical', '?')}**/10\n"
                        f"📈 Market: **{feasibility.get('market', '?')}**/10\n"
                        f"✨ Novelty: **{feasibility.get('novelty', '?')}**/10\n"
                        f"🔧 Complexity: **{feasibility.get('complexity', '?')}**/10\n"
                        f"🎯 **Overall: {overall}/10**"
                    ),
                    "inline": True,
                },
                {
                    "name": "📋 Meta",
                    "value": (
                        f"Depth: **{depth.upper()}**\n"
                        f"Sources: **{len(report.get('sources', []))}**\n"
                        f"Seeds Found: **{len(report.get('new_seeds', []))}**\n"
                        f"Risks: **{len(report.get('risks', []))}**"
                    ),
                    "inline": True,
                },
            ],
            "footer": {"text": f"Dream: {dream_id} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"},
        }
        
        # Key findings
        findings = report.get("key_findings", [])
        if findings:
            findings_text = "\n".join([
                f"**{i}. {f.get('title', 'Finding')}** (confidence: {f.get('confidence', '?')})\n{f.get('detail', '')[:200]}"
                for i, f in enumerate(findings[:5], 1)
            ])
            main_embed["fields"].append({
                "name": "🔍 Key Findings",
                "value": findings_text[:1024],
                "inline": False,
            })
        
        # Competitors
        competitors = report.get("competitors", [])
        if competitors:
            comp_text = "\n".join([
                f"• **{c.get('name', '?')}** — {c.get('description', '')[:100]}\n  *Diff:* {c.get('differentiation', '')[:100]}"
                for c in competitors[:4]
            ])
            main_embed["fields"].append({
                "name": "⚔️ Competitive Landscape",
                "value": comp_text[:1024],
                "inline": False,
            })
        
        # Roadmap
        roadmap = report.get("roadmap", [])
        if roadmap:
            road_text = "\n".join([
                f"**{r.get('phase', 'Phase')}** ({r.get('effort', '?')})\n{r.get('description', '')[:150]}"
                for r in roadmap[:4]
            ])
            main_embed["fields"].append({
                "name": "🗺️ Implementation Roadmap",
                "value": road_text[:1024],
                "inline": False,
            })
        
        # Seeds
        new_seeds = report.get("new_seeds", [])
        if new_seeds:
            seeds_text = "\n".join([
                f"🌰 **{s.get('title', 'Seed')}** (energy: {s.get('energy', '?')})\n{s.get('essence', '')[:100]}"
                for s in new_seeds[:5]
            ])
            main_embed["fields"].append({
                "name": "🌱 New Dream Seeds",
                "value": seeds_text[:1024],
                "inline": False,
            })
        
        # Risks
        risks = report.get("risks", [])
        if risks:
            risk_text = "\n".join([
                f"⚠️ **{r.get('risk', '?')}** [{r.get('severity', '?')}]\n  → {r.get('mitigation', '')[:100]}"
                for r in risks[:4]
            ])
            main_embed["fields"].append({
                "name": "⚠️ Risks & Mitigations",
                "value": risk_text[:1024],
                "inline": False,
            })
        
        self._send(embed=main_embed)
    
    def post_research_summary(self, researched_dreams: list[dict]):
        """Post a summary of all research done in this cycle."""
        if not researched_dreams:
            return
        
        lines = []
        for d in researched_dreams:
            score = d.get("feasibility", {}).get("overall", "?")
            emoji = "🟢" if isinstance(score, (int, float)) and score >= 7 else ("🟡" if isinstance(score, (int, float)) and score >= 5 else "🔴")
            lines.append(f"{emoji} **{d.get('title', '?')}** — Score: {score}/10 | Seeds: {d.get('seeds', 0)}")
        
        embed = {
            "title": "📊 Research Cycle Summary",
            "description": "\n".join(lines),
            "color": 0x4169E1,
            "footer": {"text": f"Dreams researched: {len(researched_dreams)} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"},
        }
        self._send(embed=embed)
