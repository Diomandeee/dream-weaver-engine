"""Gemini CLI client for dream evolution — FREE inference via gemini CLI tool."""

import subprocess
import json
import os
from typing import Optional


class GeminiClient:
    """Client for Gemini 3 via the gemini CLI tool (free, no API key needed)."""

    def __init__(self, model: str = "gemini-2.5-pro"):
        self.model = model
        self.cli_path = os.environ.get("GEMINI_CLI_PATH", "/opt/homebrew/bin/gemini")

    def generate(
        self,
        prompt: str,
        system: str = "You are a creative dream evolution engine.",
        max_tokens: int = 2048,
        temperature: float = 0.8,
    ) -> str:
        """Generate a response using gemini CLI."""
        full_prompt = f"{system}\n\n---\n\n{prompt}"

        try:
            result = subprocess.run(
                [self.cli_path, "-m", self.model, "-p", full_prompt],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "TERM": "dumb"},
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                raise RuntimeError(f"gemini CLI failed: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("gemini CLI timed out after 120s")

    def evolve_dream(self, dream_context: str, garden_context: str) -> dict:
        """Evolve a dream using Gemini's creative synthesis."""

        system = """You are the Dream Evolution Engine. You nurture ideas through creative synthesis.

Your role: find unexpected connections, deepen essences, suggest concrete next steps.

Respond ONLY in JSON:
{
  "insight": "New insight or development",
  "strength_delta": 0.05 to 0.15,
  "new_connections": ["tag1", "tag2"],
  "next_steps": ["step1", "step2"],
  "cross_pollinate": ["dream_name"],
  "bloom_ready": false
}"""

        prompt = f"""# Dream to Evolve

{dream_context}

# Garden Context

{garden_context}

Evolve this dream. Find angles not yet explored. Connect to other dreams. JSON only."""

        response = self.generate(prompt, system=system, temperature=0.85)
        return self._parse_json(response)

    def cross_pollinate(self, dream_a: str, dream_b: str) -> dict:
        """Find creative connections between two dreams."""

        system = """You find unexpected connections between ideas. Be creative but concrete.

Respond ONLY in JSON:
{
  "connection": "How these ideas connect",
  "synergy_score": 0.0 to 1.0,
  "merged_concept": "What emerges from combining them",
  "actionable_bridge": "Concrete step to connect them"
}"""

        prompt = f"""# Dream A
{dream_a}

# Dream B
{dream_b}

Find the hidden connection. JSON only."""

        response = self.generate(prompt, system=system, temperature=0.9)
        return self._parse_json(response)

    def generate_bloom_announcement(self, dream_context: str) -> str:
        """Generate a celebratory bloom announcement."""
        system = "Write a short, inspiring 2-3 sentence announcement that a dream has bloomed into reality."
        prompt = f"A dream has bloomed! Announce it:\n\n{dream_context}"
        return self.generate(prompt, system=system, max_tokens=256, temperature=0.9)

    def generate_journal_entry(self, garden_summary: str, evolutions: list[dict]) -> str:
        """Generate a reflective journal entry."""
        system = "Write a brief, poetic 3-4 sentence journal entry about the dream garden."
        evolutions_text = "\n".join([
            f"- {e['dream_title']}: {e.get('insight', '')[:100]}..."
            for e in evolutions
        ])
        prompt = f"Today's Garden Activity:\n\n{garden_summary}\n\nEvolutions:\n{evolutions_text}\n\nBrief journal entry."
        return self.generate(prompt, system=system, max_tokens=256, temperature=0.9)

    def _parse_json(self, response: str) -> dict:
        """Parse JSON from response, handling markdown blocks."""
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return {
                "insight": response[:500],
                "strength_delta": 0.05,
                "new_connections": [],
                "next_steps": [],
                "cross_pollinate": [],
                "bloom_ready": False,
            }
