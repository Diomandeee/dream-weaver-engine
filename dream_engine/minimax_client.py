"""MiniMax local model client for dream scoring — FREE, runs on Mac4 via Ollama."""

import json
import os
import urllib.request
from typing import Optional


class MiniMaxClient:
    """Client for MiniMax/Llama local models via Ollama on Mac4 or localhost."""

    def __init__(self, base_url: str = None, model: str = None):
        # Allow env override for Docker/container environments
        ollama_url = os.environ.get("OLLAMA_URL")
        if ollama_url and not base_url:
            base_url = ollama_url
            model = model or "llama3.2:3b"
        # Try Mac4 Ollama first, then localhost
        self.endpoints = [
            ("http://100.91.231.93:11434", "llama3.2:3b"),  # Mac4 Ollama
            ("http://localhost:18080", "local"),              # Mac1 MiniMax-3B
        ]
        self.base_url = base_url
        self.model = model
        self._resolved = False

    def _resolve(self):
        """Find first available endpoint."""
        if self._resolved:
            return
        if self.base_url:
            self._resolved = True
            return

        for url, model in self.endpoints:
            try:
                health_url = f"{url}/api/tags" if ":11434" in url else f"{url}/health"
                req = urllib.request.Request(health_url, method="GET")
                urllib.request.urlopen(req, timeout=3)
                self.base_url = url
                self.model = model
                self._resolved = True
                return
            except Exception:
                continue

        raise RuntimeError("No local model endpoint available (Mac4 Ollama or localhost MiniMax)")

    def generate(self, prompt: str, system: str = "", max_tokens: int = 512, temperature: float = 0.3) -> str:
        """Generate using local model."""
        self._resolve()

        if ":11434" in self.base_url:
            return self._ollama_generate(prompt, system, max_tokens, temperature)
        else:
            return self._openai_generate(prompt, system, max_tokens, temperature)

    def _ollama_generate(self, prompt: str, system: str, max_tokens: int, temperature: float) -> str:
        """Generate via Ollama API."""
        payload = json.dumps({
            "model": self.model,
            "prompt": f"{system}\n\n{prompt}" if system else prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        return data.get("response", "")

    def _openai_generate(self, prompt: str, system: str, max_tokens: int, temperature: float) -> str:
        """Generate via OpenAI-compatible API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]

    def score_connection(self, dream_a_tags: list[str], dream_b_tags: list[str],
                         dream_a_essence: str, dream_b_essence: str) -> float:
        """Score connection strength between two dreams. Returns 0.0-1.0."""
        system = "You are a scoring engine. Score the connection strength between two ideas from 0.0 to 1.0. Reply with ONLY a decimal number."
        prompt = f"""Idea A tags: {', '.join(dream_a_tags)}
Idea A: {dream_a_essence[:200]}

Idea B tags: {', '.join(dream_b_tags)}
Idea B: {dream_b_essence[:200]}

Connection strength (0.0 = unrelated, 1.0 = deeply connected). Reply with ONLY a number:"""

        try:
            response = self.generate(prompt, system=system, max_tokens=10, temperature=0.1)
            # Extract float from response
            for token in response.strip().split():
                try:
                    score = float(token)
                    return max(0.0, min(1.0, score))
                except ValueError:
                    continue
            return 0.3  # default if parsing fails
        except Exception:
            # Tag overlap fallback
            overlap = len(set(dream_a_tags) & set(dream_b_tags))
            return min(1.0, overlap * 0.2)

    def rank_evolution_priority(self, dreams: list[dict]) -> list[str]:
        """Rank which dreams should evolve next. Returns ordered list of dream IDs.
        
        Uses local model for smart ranking, with deterministic fallback.
        """
        system = "You are a priority ranker. Rank ideas by evolution priority. Lower strength and fewer evolutions = higher priority. Reply with ONLY the IDs, one per line, nothing else."

        dreams_text = "\n".join([
            f"ID: {d['id']} | Strength: {d['strength']:.2f} | Evolutions: {d['evos']}"
            for d in dreams
        ])
        prompt = f"Rank by priority (most needy first). Reply ONLY with IDs:\n\n{dreams_text}"

        valid_ids = {d['id'] for d in dreams}
        
        try:
            response = self.generate(prompt, system=system, max_tokens=200, temperature=0.1)
            # Try to extract valid IDs from response
            found_ids = []
            for line in response.strip().split("\n"):
                line = line.strip().strip("- ").strip("0123456789. ")
                if line in valid_ids:
                    found_ids.append(line)
                else:
                    # Try to fuzzy match — check if any valid ID is contained in the line
                    for vid in valid_ids:
                        if vid in line.lower():
                            found_ids.append(vid)
                            break
            
            # Deduplicate preserving order
            seen = set()
            ranked = []
            for i in found_ids:
                if i not in seen:
                    seen.add(i)
                    ranked.append(i)
            
            if ranked:
                return ranked
        except Exception:
            pass
        
        # Deterministic fallback: sort by (strength ASC, evolution_count ASC)
        # This ensures seeds with 0 evolutions and lowest strength go first
        return [d['id'] for d in sorted(dreams, key=lambda x: (x['strength'], x['evos']))]
