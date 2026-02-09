"""Prompt Synthesizer via Kimi-K2-Thinking.

Preprocesses messages before they reach Claude:
- Enriches context
- Extracts dream seeds
- Detects skill chains
- Classifies intent

Now with persistent memory!
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
6. LEARN - Extract facts, preferences, and patterns to remember

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
  "route_reason": "Why this routing",
  "learnings": {
    "facts": [{"key": "fact_name", "value": "fact_value"}],
    "preferences": [{"key": "pref_name", "value": "pref_value"}],
    "patterns": [{"key": "pattern_name", "value": "pattern_description"}]
  }
}

Be generous with dream seed extraction - capture any fuzzy idea that could grow.
Only suggest skill chains when truly applicable (creative work, research, evolution).
Extract learnings whenever the user reveals preferences, facts about themselves, or patterns in their behavior.
"""


class KimiSynthesizer:
    """Prompt synthesizer using Kimi-K2-Thinking with persistent memory."""
    
    def __init__(self, api_key: str = None, use_memory: bool = True):
        self.api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        self.client = Together(api_key=self.api_key)
        self.context_buffer = []  # Rolling context (in-memory fallback)
        self.max_context = 50
        
        # Persistent memory
        self.use_memory = use_memory
        self._memory = None
    
    @property
    def memory(self):
        """Lazy-load memory store."""
        if self._memory is None and self.use_memory:
            try:
                import sys
                sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
                from memory.store import get_store
                self._memory = get_store()
            except Exception as e:
                print(f"Memory store unavailable: {e}")
                self.use_memory = False
        return self._memory
    
    def add_context(self, role: str, content: str, channel: str = None):
        """Add to context - both in-memory and persistent."""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # In-memory buffer
        self.context_buffer.append(entry)
        if len(self.context_buffer) > self.max_context:
            self.context_buffer = self.context_buffer[-self.max_context:]
        
        # Persistent storage
        if self.memory:
            return self.memory.save_message(content, role, channel)
        return None
    
    def get_context_summary(self) -> str:
        """Get recent context - from memory if available."""
        if self.memory:
            context = self.memory.build_context_summary()
            if context and context != "":
                return context
        
        # Fallback to in-memory
        if not self.context_buffer:
            return "No prior context."
        
        recent = self.context_buffer[-10:]
        return "\n".join([
            f"[{m['role']}] {m['content'][:200]}..."
            for m in recent
        ])
    
    def save_synthesis_result(self, message_id: int, result: dict):
        """Save synthesis result to memory."""
        if self.memory and message_id:
            self.memory.save_synthesis(message_id, result)
            
            # Extract and save learnings
            learnings = result.get("learnings", {})
            for fact in learnings.get("facts", []):
                self.memory.remember(fact["key"], fact["value"], "fact", 0.7)
            for pref in learnings.get("preferences", []):
                self.memory.remember(pref["key"], pref["value"], "preference", 0.8)
            for pattern in learnings.get("patterns", []):
                self.memory.remember(pattern["key"], pattern["value"], "pattern", 0.6)
    
    def synthesize(self, message: str, channel: str = None) -> dict:
        """Synthesize a message, returning enriched output."""
        
        # Save incoming message
        message_id = self.add_context("user", message, channel)
        
        # Get context
        context = self.get_context_summary()
        
        prompt = f"""# Memory Context
{context}

# Current Channel
{channel or "unknown"}

# Message to Synthesize
{message}

# Task
Synthesize this message. Extract any learnings (facts, preferences, patterns).
Output JSON only."""

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
                "route_reason": "Parse failed, defaulting to direct",
                "learnings": {}
            }
        
        # Save synthesis result
        self.save_synthesis_result(message_id, result)
        
        return result
    
    def get_stats(self) -> dict:
        """Get memory statistics."""
        if self.memory:
            return self.memory.get_stats()
        return {"status": "memory_disabled", "buffer_size": len(self.context_buffer)}


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


def get_memory_stats() -> dict:
    """Get memory statistics."""
    return get_synthesizer().get_stats()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        print(json.dumps(get_memory_stats(), indent=2))
    else:
        message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test message"
        result = synthesize(message)
        print(json.dumps(result, indent=2))
