"""Unified multi-channel bloom notifier.

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


class Notifier:
    """Unified notifier — drop-in replacement for DiscordNotifier with multi-channel support."""

    def __init__(
        self,
        webhook_blooms: Optional[str] = None,
        webhook_garden: Optional[str] = None,
        webhook_journal: Optional[str] = None,
    ):
        # Parse active channels
        channels_env = os.environ.get("BLOOM_CHANNELS", "discord")
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

    def post_evolution_summary(self, evolutions: list[dict], total_dreams: int):
        """Post evolution summary — Discord only (rich embeds)."""
        if "discord" in self.channels:
            self.discord.post_evolution_summary(evolutions, total_dreams)

    def post_journal_entry(self, entry: str, date: Optional[datetime] = None):
        """Post journal entry — Discord only."""
        if "discord" in self.channels:
            self.discord.post_journal_entry(entry, date)

    def announce_new_seed(self, dream_title: str, essence: str, source: str):
        """Announce a new seed — Discord only."""
        if "discord" in self.channels:
            self.discord.announce_new_seed(dream_title, essence, source)

    # ------------------------------------------------------------------
    # iMessage
    # ------------------------------------------------------------------

    def _send_imessage_bloom(self, title: str, essence: str, strength: float):
        if not self._imsg_available:
            print("[Notifier] imsg CLI not found, skipping iMessage")
            return
        if not self.imessage_to:
            print("[Notifier] BLOOM_IMESSAGE_TO not set, skipping iMessage")
            return

        msg = f"🌸 Dream Bloom: {title}\n{essence[:200]}\nStrength: {strength:.2f}"
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

    def _write_bloom_event(self, title: str, essence: str, strength: float, channel: str):
        """Append a bloom event to ~/.clawdbot/state/bloom-events.json."""
        event = {
            "type": "bloom",
            "title": title,
            "essence": essence[:300],
            "strength": round(strength, 3),
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat() + "Z",
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

        print(f"[Notifier] Bloom event written for {channel}")
