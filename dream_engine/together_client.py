"""Together AI client for Kimi-K2-Thinking."""

import os
from together import Together
from typing import Optional


# Kimi-K2-Thinking - 256K context, great for deep reasoning
MODEL = "moonshotai/Kimi-K2-Thinking"


class KimiClient:
    """Client for Kimi-K2-Thinking via Together AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY not set")
        self.client = Together(api_key=self.api_key)
    
    def generate(
        self,
        prompt: str,
        system: str = "You are a creative dream evolution engine.",
        max_tokens: int = 2048,
        temperature: float = 0.8,
    ) -> str:
        """Generate a response from Kimi-K2-Thinking."""
        
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response.choices[0].message.content
    
    def evolve_dream(self, dream_context: str, garden_context: str) -> dict:
        """Evolve a dream, returning new insights and strength delta."""
        
        system = """You are the Dream Evolution Engine, a creative AI that nurtures ideas.

Your role is to evolve dreams by:
1. Deepening the core essence
2. Finding unexpected connections
3. Identifying actionable next steps
4. Suggesting cross-pollinations with other dreams

Respond in JSON format:
{
  "insight": "New insight or development for this dream",
  "strength_delta": 0.05 to 0.15 (how much the dream grew),
  "new_connections": ["tag1", "tag2"] (new themes discovered),
  "next_steps": ["step1", "step2"] (concrete actions),
  "cross_pollinate": ["dream_id"] (dreams to connect with),
  "bloom_ready": true/false (is this ready to become real?)
}"""

        prompt = f"""# Dream to Evolve

{dream_context}

# Garden Context (other dreams for cross-pollination)

{garden_context}

# Task

Evolve this dream. Consider:
- What new angles haven't been explored?
- How does it connect to other dreams in the garden?
- What would make it stronger and more actionable?
- Is it ready to bloom into reality?

Respond with JSON only."""

        response = self.generate(prompt, system=system, temperature=0.85)
        
        # Parse JSON from response
        import json
        try:
            # Handle potential markdown code blocks
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
                "bloom_ready": False
            }
    
    def generate_bloom_announcement(self, dream_context: str) -> str:
        """Generate a celebratory bloom announcement."""
        
        system = """You are announcing that a dream has bloomed - it's ready to become reality!
Write a short, inspiring announcement (2-3 sentences) celebrating this moment.
Include the dream's essence and what makes it special."""

        prompt = f"""A dream has bloomed! Announce it:

{dream_context}"""

        return self.generate(prompt, system=system, max_tokens=256, temperature=0.9)
    
    def generate_journal_entry(self, garden_summary: str, evolutions: list[dict]) -> str:
        """Generate a reflective journal entry about today's garden activity."""
        
        system = """You are writing a brief, poetic journal entry about the dream garden.
Reflect on what grew, what's emerging, and the overall health of the garden.
Keep it to 3-4 sentences, evocative but concise."""

        evolutions_text = "\n".join([
            f"- {e['dream_title']}: {e['insight'][:100]}..."
            for e in evolutions
        ])

        prompt = f"""Today's Garden Activity:

{garden_summary}

Evolutions:
{evolutions_text}

Write a brief journal entry."""

        return self.generate(prompt, system=system, max_tokens=256, temperature=0.9)
