"""Discord webhook integration for notifications."""

import os
import requests
from typing import Optional
from datetime import datetime


class DiscordNotifier:
    """Send notifications to Discord via webhooks."""
    
    def __init__(
        self,
        webhook_blooms: Optional[str] = None,
        webhook_garden: Optional[str] = None,
        webhook_journal: Optional[str] = None,
    ):
        self.webhook_blooms = webhook_blooms or os.environ.get("DISCORD_WEBHOOK_BLOOMS")
        self.webhook_garden = webhook_garden or os.environ.get("DISCORD_WEBHOOK_GARDEN")
        self.webhook_journal = webhook_journal or os.environ.get("DISCORD_WEBHOOK_JOURNAL")
    
    def _send(self, webhook_url: str, content: str, embed: Optional[dict] = None):
        """Send a message to a Discord webhook."""
        if not webhook_url:
            print(f"[Discord] No webhook configured, skipping: {content[:50]}...")
            return False
        
        payload = {"content": content}
        if embed:
            payload["embeds"] = [embed]
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Discord] Failed to send: {e}")
            return False
    
    def announce_bloom(self, dream_title: str, essence: str, announcement: str):
        """Announce a dream bloom to #blooms."""
        embed = {
            "title": f"🌸 BLOOM: {dream_title}",
            "description": announcement,
            "color": 0xFF69B4,  # Hot pink
            "fields": [
                {"name": "Essence", "value": essence[:200], "inline": False}
            ],
            "footer": {"text": f"Bloomed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"}
        }
        self._send(self.webhook_blooms, "", embed=embed)
    
    def post_evolution_summary(self, evolutions: list[dict], total_dreams: int):
        """Post evolution cycle summary to #garden."""
        if not evolutions:
            return
        
        evolution_text = "\n".join([
            f"• **{e['dream_title']}** +{e['strength_delta']:.2f} → {e['new_strength']:.2f}"
            for e in evolutions
        ])
        
        embed = {
            "title": "🌱 Evolution Cycle Complete",
            "description": f"Evolved {len(evolutions)} dreams",
            "color": 0x90EE90,  # Light green
            "fields": [
                {"name": "Dreams Evolved", "value": evolution_text, "inline": False},
                {"name": "Garden Size", "value": f"{total_dreams} dreams", "inline": True}
            ],
            "footer": {"text": datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        }
        self._send(self.webhook_garden, "", embed=embed)
    
    def post_journal_entry(self, entry: str, date: Optional[datetime] = None):
        """Post a reflective journal entry to #dream-journal."""
        date = date or datetime.utcnow()
        
        embed = {
            "title": f"📔 Garden Journal — {date.strftime('%B %d, %Y')}",
            "description": entry,
            "color": 0xDDA0DD,  # Plum
            "footer": {"text": "Dream Weaver Engine"}
        }
        self._send(self.webhook_journal, "", embed=embed)
    
    def announce_new_seed(self, dream_title: str, essence: str, source: str):
        """Announce a new seed planted in #garden."""
        embed = {
            "title": f"🌰 New Seed: {dream_title}",
            "description": essence[:300],
            "color": 0x8B4513,  # Saddle brown
            "fields": [
                {"name": "Source", "value": source, "inline": True}
            ],
            "footer": {"text": datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        }
        self._send(self.webhook_garden, "", embed=embed)
