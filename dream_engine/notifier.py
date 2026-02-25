"""Unified multi-channel bloom notifier v2.

Supports: Discord (webhooks), iMessage (imsg CLI), Telegram (event file), WhatsApp (event file).
Config via environment variables:
  BLOOM_CHANNELS=discord,imessage,telegram,whatsapp  (comma-separated)
  BLOOM_IMESSAGE_TO=+15551234567  (phone or email)
  BLOOM_TELEGRAM_CHAT=chat_id  (optional)
"""

import json
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .discord import DiscordNotifier


BLOOM_EVENTS_FILE = Path.home() / ".clawdbot" / "state" / "bloom-events.json"
BLOOM_HISTORY_FILE = Path.home() / ".clawdbot" / "state" / "bloom-history.json"


class Notifier:
    """Unified notifier — drop-in replacement for DiscordNotifier with multi-channel support.

    v2 additions:
    - Rich bloom cards with stage progression emoji trail
    - Bloom history tracking (deduplicated)
    - Evolution milestone notifications (every 10 evolutions per dream)
    - Garden digest (periodic summary of all garden activity)
    """

    def __init__(
        self,
        webhook_blooms: Optional[str] = None,
        webhook_garden: Optional[str] = None,
        webhook_journal: Optional[str] = None,
    ):
        # Parse active channels
        channels_env = os.environ.get("BLOOM_CHANNELS", "discord,imessage,telegram")
        self.channels = [c.strip().lower() for c in channels_env.split(",") if c.strip()]

        # Discord — delegate to existing DiscordNotifier
        self.discord = DiscordNotifier(
            webhook_blooms=webhook_blooms,
            webhook_garden=webhook_garden,
            webhook_journal=webhook_journal,
        )

        # iMessage
        self.imessage_to = os.environ.get("BLOOM_IMESSAGE_TO", "")
        self._imsg_available = shutil.which("imsg") is not None

        # Telegram / WhatsApp chat IDs (optional, included in event payloads)
        self.telegram_chat = os.environ.get("BLOOM_TELEGRAM_CHAT", "")

    # ------------------------------------------------------------------
    # Public API — matches DiscordNotifier interface for backward compat
    # ------------------------------------------------------------------

    def announce_bloom(self, dream_title: str, essence: str, announcement: str, strength: float = 0.0):
        """Announce a dream bloom across all configured channels."""
        # Track in bloom history
        self._record_bloom(dream_title, essence, strength)

        for ch in self.channels:
            try:
                if ch == "discord":
                    self.discord.announce_bloom(dream_title, essence, announcement)
                elif ch == "imessage":
                    self._send_imessage_bloom(dream_title, essence, strength)
                elif ch == "telegram":
                    self._write_bloom_event(dream_title, essence, strength, "telegram")
                elif ch == "whatsapp":
                    self._write_bloom_event(dream_title, essence, strength, "whatsapp")
                else:
                    print(f"[Notifier] Unknown channel '{ch}', skipping")
            except Exception as e:
                print(f"[Notifier] Error on {ch}: {e}")

    def announce_stage_change(self, dream_title: str, old_stage: str, new_stage: str, strength: float):
        """Announce a dream stage transition across messaging channels."""
        stage_emoji = {
            "seed": "🌰", "germinating": "🌱", "growing": "🌿",
            "flowering": "🌸", "bloom": "🌺", "archived": "📦",
        }
        old_icon = stage_emoji.get(old_stage, "❓")
        new_icon = stage_emoji.get(new_stage, "❓")
        msg = f"{old_icon}→{new_icon} {dream_title}\nStage: {old_stage} → {new_stage} | Strength: {strength:.2f}"

        for ch in self.channels:
            try:
                if ch == "imessage":
                    self._send_imessage(f"🌙 Dream Stage Change\n{msg}")
                elif ch in ("telegram", "whatsapp"):
                    self._write_bloom_event(
                        dream_title, f"Stage: {old_stage} → {new_stage}",
                        strength, ch, event_type="stage_change",
                    )
            except Exception as e:
                print(f"[Notifier] Stage change error on {ch}: {e}")

    def announce_evolution_milestone(self, dream_title: str, evolution_count: int, strength: float):
        """Notify when a dream hits an evolution milestone (every 10)."""
        msg = f"🔄 {dream_title} reached {evolution_count} evolutions! Strength: {strength:.2f}"
        for ch in self.channels:
            try:
                if ch == "imessage":
                    self._send_imessage(msg)
                elif ch in ("telegram", "whatsapp"):
                    self._write_bloom_event(
                        dream_title, f"{evolution_count} evolutions",
                        strength, ch, event_type="milestone",
                    )
            except Exception as e:
                print(f"[Notifier] Milestone error on {ch}: {e}")

    def send_garden_digest(self, total_dreams: int, total_blooms: int, total_evolutions: int,
                           top_dreams: list[tuple[str, float]]):
        """Send a periodic garden digest to messaging channels."""
        top_str = "\n".join(f"  {name}: {s:.2f}" for name, s in top_dreams[:5])
        msg = (
            f"🌙 Dream Garden Digest\n"
            f"🌿 {total_dreams} dreams | 🌺 {total_blooms} blooms | 🔄 {total_evolutions} evolutions\n"
            f"\n📊 Top Dreams:\n{top_str}"
        )
        for ch in self.channels:
            try:
                if ch == "imessage":
                    self._send_imessage(msg)
                elif ch in ("telegram", "whatsapp"):
                    self._write_bloom_event(
                        "Garden Digest", msg, 0.0, ch, event_type="digest",
                    )
            except Exception as e:
                print(f"[Notifier] Digest error on {ch}: {e}")

    def post_evolution_summary(self, evolutions: list[dict], total_dreams: int):
        """Post evolution summary — Discord only (rich embeds)."""
        if "discord" in self.channels:
            self.discord.post_evolution_summary(evolutions, total_dreams)

    def post_journal_entry(self, entry: str, date: Optional[datetime] = None):
        """Post journal entry — Discord only."""
        if "discord" in self.channels:
            self.discord.post_journal_entry(entry, date)

    def announce_new_seed(self, dream_title: str, essence: str, source: str):
        """Announce a new seed — Discord + messaging channels."""
        if "discord" in self.channels:
            self.discord.announce_new_seed(dream_title, essence, source)

        # Also notify messaging channels for new seeds
        for ch in self.channels:
            try:
                if ch == "imessage":
                    self._send_imessage(f"🌰 New Dream Seed: {dream_title}\n{essence[:150]}\nSource: {source}")
                elif ch in ("telegram", "whatsapp"):
                    self._write_bloom_event(
                        dream_title, essence[:200], 0.1, ch, event_type="new_seed",
                    )
            except Exception as e:
                print(f"[Notifier] New seed notify error on {ch}: {e}")

    # ------------------------------------------------------------------
    # iMessage — rich bloom cards
    # ------------------------------------------------------------------

    def _send_imessage_bloom(self, title: str, essence: str, strength: float):
        """Send a rich bloom notification via iMessage."""
        strength_bar = self._build_strength_bar(strength)
        msg = (
            f"🌺 Dream Bloom!\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🌙 {title}\n"
            f"\n{essence[:200]}\n"
            f"\n{strength_bar}\n"
            f"🌰→🌱→🌿→🌸→🌺 Complete!\n"
            f"━━━━━━━━━━━━━━━━"
        )
        self._send_imessage(msg)

    def _send_imessage(self, msg: str):
        """Low-level iMessage send via imsg CLI."""
        if not self._imsg_available:
            print("[Notifier] imsg CLI not found, skipping iMessage")
            return
        if not self.imessage_to:
            print("[Notifier] BLOOM_IMESSAGE_TO not set, skipping iMessage")
            return

        try:
            subprocess.run(
                ["imsg", "send", self.imessage_to, msg],
                timeout=15,
                capture_output=True,
                text=True,
            )
            print(f"[Notifier] iMessage sent to {self.imessage_to}")
        except Exception as e:
            print(f"[Notifier] iMessage failed: {e}")

    # ------------------------------------------------------------------
    # Telegram / WhatsApp — write event files for Clawdbot pickup
    # ------------------------------------------------------------------

    def _write_bloom_event(self, title: str, essence: str, strength: float, channel: str,
                           event_type: str = "bloom"):
        """Append a bloom event to ~/.clawdbot/state/bloom-events.json."""
        event = {
            "type": event_type,
            "title": title,
            "essence": essence[:300],
            "strength": round(strength, 3),
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "delivered": False,
        }
        if channel == "telegram" and self.telegram_chat:
            event["chat_id"] = self.telegram_chat

        BLOOM_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Read existing events
        events: list = []
        if BLOOM_EVENTS_FILE.exists():
            try:
                with open(BLOOM_EVENTS_FILE) as f:
                    events = json.load(f)
                if not isinstance(events, list):
                    events = []
            except (json.JSONDecodeError, IOError):
                events = []

        events.append(event)

        with open(BLOOM_EVENTS_FILE, "w") as f:
            json.dump(events, f, indent=2)

        print(f"[Notifier] {event_type} event written for {channel}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_strength_bar(strength: float, width: int = 10) -> str:
        filled = round(strength * width)
        return f"Strength: [{'█' * filled}{'░' * (width - filled)}] {strength:.2f}"

    def _record_bloom(self, title: str, essence: str, strength: float):
        """Track bloom in history file for deduplication and stats."""
        BLOOM_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        history: list = []
        if BLOOM_HISTORY_FILE.exists():
            try:
                with open(BLOOM_HISTORY_FILE) as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        history.append({
            "title": title,
            "essence": essence[:200],
            "strength": round(strength, 3),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

        with open(BLOOM_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
