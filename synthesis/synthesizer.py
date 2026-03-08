"""Prompt Synthesizer via Kimi-K2-Thinking.

Preprocesses messages before they reach Claude:
- Enriches context via unified retrieval (local + Graph Kernel + RAG++)
- Extracts dream seeds
- Detects skill chains
- Classifies intent
- Learns facts, preferences, patterns

v2: Integrated with Comp-Core services (Graph Kernel, RAG++)
"""

import os
import json
import asyncio
from datetime import datetime
from together import Together

MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

SYSTEM_PROMPT = """You are a Prompt Synthesizer - a preprocessing layer that enriches user messages before they reach the main AI assistant.

You have access to:
- Recent conversation history
- Known facts and preferences about the user
- Knowledge graph relationships
- Retrieved relevant context (when available)

Your job:
1. ENRICH - Add implicit context, expand abbreviated thoughts, fill gaps
2. EXTRACT - Identify dream seeds (fuzzy ideas worth incubating)
3. DETECT - Recognize when multiple skills should chain together
4. CLASSIFY - Categorize as: idea, task, question, exploration, directive
5. ROUTE - Suggest where this should go: direct response, dream garden, pulse session, skill chain
6. LEARN - Extract facts, preferences, and patterns to remember
7. CONNECT - Identify relationships to existing knowledge
8. PARALLEL_PATHS - Detect when multiple actions can/should execute together

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
  "project_refs": ["bwb", "milkmen", "comp-core", etc] or [],
  "route": "direct|garden|pulse|chain",
  "route_reason": "Why this routing",
  "learnings": {
    "facts": [{"key": "fact_name", "value": "fact_value"}],
    "preferences": [{"key": "pref_name", "value": "pref_value"}],
    "patterns": [{"key": "pattern_name", "value": "pattern_description"}]
  },
  "knowledge_connections": [
    {"subject": "entity1", "predicate": "relation", "object": "entity2"}
  ],
  "parallel_paths": {
    "detected": true|false,
    "execute_all": true|false,
    "paths": [
      {"action": "...", "independent": true|false, "type": "format|platform|feature|research"}
    ],
    "exclusive_choices": ["..."] or null,
    "reason": "Why these are/aren't parallel"
  }
}

PARALLEL PATHS RULES (CRITICAL):
- INDEPENDENT paths can ALL execute simultaneously (formats, platforms, additive features)
- EXCLUSIVE paths require user choice (architecture, naming, destructive actions)
- When paths are independent, set execute_all: true - the agent will run ALL without asking
- Examples of INDEPENDENT: "tweet AND blog", "export to A AND B", "generate image AND diagram"
- Examples of EXCLUSIVE: "use React OR Vue", "name it X OR Y", "delete this OR that"
- BIAS TOWARD ACTION: If reversible and non-destructive, lean toward execute_all: true

Be generous with dream seed extraction - capture any fuzzy idea that could grow.
Only suggest skill chains when truly applicable (creative work, research, evolution).
Extract learnings whenever the user reveals preferences, facts about themselves, or patterns.
Identify knowledge connections when entities relate to each other."""


class KimiSynthesizer:
    """Prompt synthesizer using Kimi-K2-Thinking with unified retrieval."""
    
    def __init__(self, api_key: str = None, use_memory: bool = True, use_services: bool = True):
        self.api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        self.client = Together(api_key=self.api_key)
        self.context_buffer = []  # In-memory fallback
        self.max_context = 50
        
        # Memory and services
        self.use_memory = use_memory
        self.use_services = use_services
        self._memory = None
        self._retriever = None
        
        # HTDS integration
        self._htds_context = None
        try:
            from synthesis.htds_integration import get_domain_context_for_synthesis
            self._htds_context = get_domain_context_for_synthesis
        except Exception:
            try:
                from htds_integration import get_domain_context_for_synthesis
                self._htds_context = get_domain_context_for_synthesis
            except Exception:
                pass
    
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
    
    @property
    def retriever(self):
        """Lazy-load unified retriever."""
        if self._retriever is None and self.use_services:
            try:
                import sys
                sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
                from memory.unified_retriever import get_unified_retriever
                self._retriever = get_unified_retriever()
            except Exception as e:
                print(f"Unified retriever unavailable: {e}")
                self.use_services = False
        return self._retriever
    
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
            if context and context.strip():
                return context
        
        # Fallback to in-memory
        if not self.context_buffer:
            return "No prior context."
        
        recent = self.context_buffer[-10:]
        return "\n".join([
            f"[{m['role']}] {m['content'][:200]}..."
            for m in recent
        ])
    
    async def get_rich_context(self, message: str, anchor_turn_id: str = None) -> str:
        """Get rich context using unified retriever."""
        if not self.retriever:
            return self.get_context_summary()
        
        try:
            context = await self.retriever.build_context(
                query=message,
                anchor_turn_id=anchor_turn_id,
                include_slice=True,
                include_rag=True
            )
            return context.to_prompt_context(max_chars=4000)
        except Exception as e:
            print(f"Rich context failed: {e}")
            return self.get_context_summary()
    
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
    
    async def sync_to_graph_kernel(self, result: dict):
        """Sync learnings and knowledge connections to Graph Kernel."""
        if not self.retriever:
            return
        
        try:
            # Sync learnings
            learnings = result.get("learnings", {})
            if learnings:
                await self.retriever.sync_learnings_to_graph_kernel(learnings)
            
            # Sync knowledge connections
            connections = result.get("knowledge_connections", [])
            if connections:
                from memory.graph_kernel_client import get_graph_kernel_client, KnowledgeTriple
                client = get_graph_kernel_client()
                triples = [
                    KnowledgeTriple(
                        subject=c["subject"],
                        predicate=c["predicate"],
                        object=c["object"],
                        confidence=0.7,
                        source="kimi-synthesis"
                    )
                    for c in connections
                ]
                await client.add_knowledge_batch(triples)
        except Exception as e:
            print(f"Graph Kernel sync failed: {e}")
    
    async def synthesize_async(
        self,
        message: str,
        channel: str = None,
        anchor_turn_id: str = None
    ) -> dict:
        """Async synthesis with full service integration."""
        
        # Save incoming message
        message_id = self.add_context("user", message, channel)
        
        # Get rich context
        context = await self.get_rich_context(message, anchor_turn_id)
        
        # HTDS topology context
        htds_context = ""
        if self._htds_context:
            try:
                htds_context = self._htds_context(message)
            except Exception:
                htds_context = "[HTDS] unavailable"
        
        prompt = f"""# Context (from memory, knowledge graph, and retrieval)
{context}

# Topology Context (from HTDS — density-pruned knowledge hierarchy)
{htds_context}

# Current Channel
{channel or "unknown"}

# Message to Synthesize
{message}

# Task
Synthesize this message. Extract learnings. Identify knowledge connections.
Use the topology context to weight domain relevance.
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
                "learnings": {},
                "knowledge_connections": []
            }
        
        # Save synthesis result
        self.save_synthesis_result(message_id, result)
        
        # Sync to Graph Kernel (background)
        asyncio.create_task(self.sync_to_graph_kernel(result))
        
        # === SKILL ROUTER INTEGRATION ===
        # Enhance skill_chain with intelligent routing
        try:
            import subprocess
            router_path = os.path.expanduser("~/.clawdbot/tools/skill-router.py")
            if os.path.exists(router_path):
                # Use the router to resolve/enhance the chain
                router_result = subprocess.run(
                    ["python3", router_path, "chain", message],
                    capture_output=True, text=True, timeout=5
                )
                if router_result.returncode == 0:
                    router_data = json.loads(router_result.stdout)
                    routed_chain = router_data.get("chain", [])
                    
                    # Merge: Kimi's chain + router's chain (deduplicated)
                    kimi_chain = result.get("skill_chain") or []
                    seen = set(kimi_chain)
                    merged = list(kimi_chain)
                    for skill in routed_chain:
                        if skill not in seen:
                            merged.append(skill)
                            seen.add(skill)
                    
                    if merged:
                        result["skill_chain"] = merged
                        result["skill_chain_context"] = router_data.get("context", "")
                        if result.get("route") == "direct" and len(merged) > 1:
                            result["route"] = "chain"
                            result["route_reason"] = f"Skill router detected chain: {' → '.join(merged)}"
        except Exception as e:
            pass  # Router is optional enhancement, never block synthesis
        # === END SKILL ROUTER ===
        
        return result
    
    def synthesize(self, message: str, channel: str = None) -> dict:
        """Sync wrapper for synthesis."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop for sync context
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.synthesize_async(message, channel)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(
                    self.synthesize_async(message, channel)
                )
        except Exception as e:
            print(f"Async synthesis failed, falling back: {e}")
            return self._synthesize_simple(message, channel)
    
    def _synthesize_simple(self, message: str, channel: str = None) -> dict:
        """Simple synchronous synthesis without service integration."""
        context = self.get_context_summary()
        
        prompt = f"""# Context
{context}

# Channel
{channel or "unknown"}

# Message
{message}

Synthesize. Output JSON only."""

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
        
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            return json.loads(result_text.strip())
        except json.JSONDecodeError:
            return {
                "enriched_prompt": message,
                "intent": "unknown",
                "confidence": 0.5,
                "dream_seeds": [],
                "skill_chain": None,
                "project_refs": [],
                "route": "direct",
                "route_reason": "Parse failed"
            }
    
    def get_stats(self) -> dict:
        """Get memory and service statistics."""
        stats = {"status": "ok"}
        
        if self.memory:
            stats["memory"] = self.memory.get_stats()
        else:
            stats["memory"] = {"status": "disabled"}
        
        if self.retriever:
            stats["services"] = {
                "graph_kernel": self.retriever._gk_available,
                "rag_plus_plus": self.retriever._rag_available
            }
        else:
            stats["services"] = {"status": "disabled"}
        
        return stats


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


async def synthesize_async(message: str, channel: str = None, anchor: str = None) -> dict:
    """Async entry point for synthesis."""
    return await get_synthesizer().synthesize_async(message, channel, anchor)


def get_memory_stats() -> dict:
    """Get memory and service statistics."""
    return get_synthesizer().get_stats()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        print(json.dumps(get_memory_stats(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "check":
        async def check():
            synth = get_synthesizer()
            if synth.retriever:
                services = await synth.retriever.check_services()
                print(json.dumps(services, indent=2))
            else:
                print("Retriever not available")
        asyncio.run(check())
    else:
        message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test message"
        result = synthesize(message)
        print(json.dumps(result, indent=2))
