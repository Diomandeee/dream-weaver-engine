"""Prompt Synthesizer via Kimi-K2-Thinking.

Preprocesses messages before they reach Claude:
- Enriches context
- Extracts dream seeds
- Detects skill chains
- Classifies intent
"""

import os
import json
from datetime import datetime
from together import Together

MODEL = "moonshotai/Kimi-K2-Thinking"

SYSTEM_PROMPT = """You are a Prompt Synthesizer - a preprocessing layer that enriches user messages before they reach the main AI assistant.

Your job:
1. ENRICH - Add implicit context, expand abbreviated thoughts, fill gaps
2. EXTRACT - Identify dream seeds (fuzzy ideas worth incubating)
3. DETECT - Recognize when multiple skills should chain together
4. CLASSIFY - Categorize as: idea, task, question, exploration, directive
5. ROUTE - Suggest where this should go: direct response, dream garden, pulse session, skill chain

Output JSON:
{
  "enriched_prompt": "The expanded, context-rich version of the input",
  "intent": "idea|task|question|exploration|directive",
  "confidence": 0.0-1.0,
  "dream_seeds": [
    {
      "title": "Short title",
      "essence": "Core idea in 1-2 sentences",
      "energy": 0.0-1.0,
      "tags": ["tag1", "tag2"]
    }
  ],
  "skill_chain": ["skill1", "skill2"] or null,
  "project_refs": ["bwb", "milkmen", etc] or [],
  "route": "direct|garden|pulse|chain",
  "route_reason": "Why this routing"
}

Be generous with dream seed extraction - capture any fuzzy idea that could grow.
Only suggest skill chains when truly applicable (creative work, research, evolution).
"""


class KimiSynthesizer:
    """Prompt synthesizer using Kimi-K2-Thinking."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        self.client = Together(api_key=self.api_key)
        self.context_buffer = []  # Rolling context
        self.max_context = 50  # Last N messages for context
    
    def add_context(self, role: str, content: str):
        """Add to rolling context buffer."""
        self.context_buffer.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Trim to max
        if len(self.context_buffer) > self.max_context:
            self.context_buffer = self.context_buffer[-self.max_context:]
    
    def get_context_summary(self) -> str:
        """Get recent context as summary."""
        if not self.context_buffer:
            return "No prior context."
        
        recent = self.context_buffer[-10:]  # Last 10
        return "\n".join([
            f"[{m['role']}] {m['content'][:200]}..."
            for m in recent
        ])
    
    def synthesize(self, message: str, channel: str = None) -> dict:
        """Synthesize a message, returning enriched output."""
        
        context = self.get_context_summary()
        
        prompt = f"""# Recent Context
{context}

# Current Channel
{channel or "unknown"}

# Message to Synthesize
{message}

# Task
Synthesize this message. Output JSON only."""

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.7,
        )
        
        result_text = response.choices[0].message.content
        
        # Parse JSON
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            result = json.loads(result_text.strip())
        except json.JSONDecodeError:
            result = {
                "enriched_prompt": message,
                "intent": "unknown",
                "confidence": 0.5,
                "dream_seeds": [],
                "skill_chain": None,
                "project_refs": [],
                "route": "direct",
                "route_reason": "Parse failed, defaulting to direct"
            }
        
        # Add to context
        self.add_context("user", message)
        
        return result


# Singleton for persistent context
_synthesizer = None

def get_synthesizer() -> KimiSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = KimiSynthesizer()
    return _synthesizer


def synthesize(message: str, channel: str = None) -> dict:
    """Main entry point for synthesis."""
    return get_synthesizer().synthesize(message, channel)


if __name__ == "__main__":
    import sys
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test message"
    result = synthesize(message)
    print(json.dumps(result, indent=2))
