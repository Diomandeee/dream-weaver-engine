"""Dual Synthesizer — Kimi-K2 + OpenAI running in parallel.

Two independent synthesis perspectives merged into a unified result.
Each model sees the same input but produces its own enrichment,
dream seeds, skill chains, and learnings. Results are merged with
deduplication and confidence-weighted selection.

v1: 2026-02-22
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ── Provider imports ─────────────────────────────────────────────
try:
    from together import Together
    HAS_TOGETHER = True
except ImportError:
    HAS_TOGETHER = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# ── Models ───────────────────────────────────────────────────────
KIMI_MODEL = "moonshotai/Kimi-K2-Thinking"
OPENAI_MODEL = os.environ.get("OPENAI_SYNTH_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = "https://api.openai.com/v1"

# ── Shared system prompt (both models get the same instructions) ──
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


def _parse_json_response(text: str) -> dict:
    """Parse JSON from model response, handling code fences and thinking tokens."""
    if not text:
        return None
    
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Strip code fences
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
            return json.loads(text.strip())
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        pass
    
    # Thinking model: find the last JSON object in the text
    # (reasoning tokens come before the actual JSON)
    import re
    json_blocks = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    for block in reversed(json_blocks):
        try:
            result = json.loads(block)
            if "enriched_prompt" in result or "intent" in result:
                return result
        except json.JSONDecodeError:
            continue
    
    # Last resort: find anything between first { and last }
    try:
        first_brace = text.index('{')
        last_brace = text.rindex('}')
        if first_brace < last_brace:
            return json.loads(text[first_brace:last_brace + 1])
    except (ValueError, json.JSONDecodeError):
        pass
    
    return None


def _empty_result(message: str, reason: str = "provider unavailable") -> dict:
    """Return a minimal result when a provider fails."""
    return {
        "enriched_prompt": message,
        "intent": "unknown",
        "confidence": 0.0,
        "dream_seeds": [],
        "skill_chain": None,
        "project_refs": [],
        "route": "direct",
        "route_reason": reason,
        "learnings": {},
        "knowledge_connections": [],
        "parallel_paths": {"detected": False, "execute_all": False, "paths": [], "reason": reason},
        "_provider": "none",
        "_latency_ms": 0,
    }


class DualSynthesizer:
    """Runs Kimi-K2 and OpenAI synthesis in parallel, merges results."""

    def __init__(
        self,
        together_api_key: str = None,
        openai_api_key: str = None,
        use_memory: bool = True,
        use_services: bool = True,
    ):
        # ── Kimi-K2 (Together AI) ────────────────────────────────
        self.together_key = together_api_key or os.environ.get("TOGETHER_API_KEY")
        self.together_client = None
        if HAS_TOGETHER and self.together_key:
            self.together_client = Together(api_key=self.together_key)

        # ── OpenAI ───────────────────────────────────────────────
        self.openai_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.openai_available = bool(HAS_HTTPX and self.openai_key)

        # ── Memory / services (shared, loaded once) ──────────────
        self.use_memory = use_memory
        self.use_services = use_services
        self._memory = None
        self._retriever = None
        self.context_buffer: list = []
        self.max_context = 50

        # ── Stats ────────────────────────────────────────────────
        self.stats = {
            "kimi": {"calls": 0, "successes": 0, "failures": 0, "total_ms": 0},
            "openai": {"calls": 0, "successes": 0, "failures": 0, "total_ms": 0},
            "merges": 0,
            "started_at": datetime.utcnow().isoformat(),
        }

        # ── HTDS integration ─────────────────────────────────────
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

    # ── Memory helpers (reused from original synthesizer) ────────
    @property
    def memory(self):
        if self._memory is None and self.use_memory:
            try:
                sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
                from memory.store import get_store
                self._memory = get_store()
            except Exception:
                self.use_memory = False
        return self._memory

    @property
    def retriever(self):
        if self._retriever is None and self.use_services:
            try:
                sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
                from memory.unified_retriever import get_unified_retriever
                self._retriever = get_unified_retriever()
            except Exception:
                self.use_services = False
        return self._retriever

    def add_context(self, role: str, content: str, channel: str = None):
        entry = {"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()}
        self.context_buffer.append(entry)
        if len(self.context_buffer) > self.max_context:
            self.context_buffer = self.context_buffer[-self.max_context:]
        if self.memory:
            return self.memory.save_message(content, role, channel)
        return None

    def get_context_summary(self) -> str:
        if self.memory:
            ctx = self.memory.build_context_summary()
            if ctx and ctx.strip():
                return ctx
        if not self.context_buffer:
            return "No prior context."
        recent = self.context_buffer[-10:]
        return "\n".join([f"[{m['role']}] {m['content'][:200]}..." for m in recent])

    async def get_rich_context(self, message: str, anchor_turn_id: str = None) -> str:
        if not self.retriever:
            return self.get_context_summary()
        try:
            context = await self.retriever.build_context(
                query=message, anchor_turn_id=anchor_turn_id,
                include_slice=True, include_rag=True,
            )
            return context.to_prompt_context(max_chars=4000)
        except Exception:
            return self.get_context_summary()

    def _build_prompt(self, message: str, context: str, channel: str, htds_context: str) -> str:
        return f"""# Context (from memory, knowledge graph, and retrieval)
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

    # ── Provider calls ───────────────────────────────────────────
    async def _call_kimi(self, prompt: str) -> dict:
        """Call Kimi-K2 via Together AI."""
        if not self.together_client:
            return _empty_result("", "Kimi-K2 client not available")

        self.stats["kimi"]["calls"] += 1
        t0 = time.monotonic()
        try:
            response = await asyncio.to_thread(
                self.together_client.chat.completions.create,
                model=KIMI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2048,
                temperature=0.7,
            )
            raw = response.choices[0].message.content
            result = _parse_json_response(raw) or _empty_result("", "Kimi parse failed")
            result["_provider"] = "kimi-k2"
            result["_latency_ms"] = int((time.monotonic() - t0) * 1000)
            self.stats["kimi"]["successes"] += 1
            self.stats["kimi"]["total_ms"] += result["_latency_ms"]
            return result
        except Exception as e:
            self.stats["kimi"]["failures"] += 1
            r = _empty_result("", f"Kimi error: {e}")
            r["_provider"] = "kimi-k2"
            r["_latency_ms"] = int((time.monotonic() - t0) * 1000)
            return r

    async def _call_openai(self, prompt: str) -> dict:
        """Call OpenAI via httpx (no openai package needed)."""
        if not self.openai_available:
            return _empty_result("", "OpenAI not configured")

        self.stats["openai"]["calls"] += 1
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{OPENAI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": OPENAI_MODEL,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 2048,
                        "temperature": 0.7,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw = data["choices"][0]["message"]["content"]
                result = _parse_json_response(raw) or _empty_result("", "OpenAI parse failed")
                result["_provider"] = "openai"
                result["_latency_ms"] = int((time.monotonic() - t0) * 1000)
                self.stats["openai"]["successes"] += 1
                self.stats["openai"]["total_ms"] += result["_latency_ms"]
                return result
        except Exception as e:
            self.stats["openai"]["failures"] += 1
            r = _empty_result("", f"OpenAI error: {e}")
            r["_provider"] = "openai"
            r["_latency_ms"] = int((time.monotonic() - t0) * 1000)
            return r

    # ── Merge logic ──────────────────────────────────────────────
    def _merge_results(self, kimi: dict, openai: dict, original_message: str) -> dict:
        """Merge two synthesis perspectives into one unified result."""
        self.stats["merges"] += 1

        # Determine primary (higher confidence wins)
        k_conf = kimi.get("confidence", 0) or 0
        o_conf = openai.get("confidence", 0) or 0
        primary = kimi if k_conf >= o_conf else openai
        secondary = openai if k_conf >= o_conf else kimi

        # Use primary's enriched prompt (higher confidence)
        enriched = primary.get("enriched_prompt") or secondary.get("enriched_prompt") or original_message

        # Merge dream seeds (deduplicate by title)
        seen_titles = set()
        merged_seeds = []
        for seed in (kimi.get("dream_seeds") or []) + (openai.get("dream_seeds") or []):
            title = seed.get("title", "").lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                merged_seeds.append(seed)

        # Merge skill chains (deduplicate, preserve order)
        kimi_chain = kimi.get("skill_chain") or []
        openai_chain = openai.get("skill_chain") or []
        seen_skills = set()
        merged_chain = []
        for s in kimi_chain + openai_chain:
            if s not in seen_skills:
                seen_skills.add(s)
                merged_chain.append(s)

        # Merge project refs
        merged_refs = list(set((kimi.get("project_refs") or []) + (openai.get("project_refs") or [])))

        # Merge learnings
        merged_learnings = {"facts": [], "preferences": [], "patterns": []}
        for src in [kimi, openai]:
            l = src.get("learnings") or {}
            for cat in ["facts", "preferences", "patterns"]:
                seen_keys = {f.get("key") for f in merged_learnings[cat]}
                for item in l.get(cat, []):
                    if item.get("key") not in seen_keys:
                        merged_learnings[cat].append(item)
                        seen_keys.add(item.get("key"))

        # Merge knowledge connections (deduplicate by subject+predicate+object)
        seen_triples = set()
        merged_connections = []
        for src in [kimi, openai]:
            for conn in src.get("knowledge_connections") or []:
                key = (conn.get("subject", ""), conn.get("predicate", ""), conn.get("object", ""))
                if key not in seen_triples:
                    seen_triples.add(key)
                    merged_connections.append(conn)

        # Merge parallel paths — union of detected paths
        k_paths = kimi.get("parallel_paths") or {}
        o_paths = openai.get("parallel_paths") or {}
        merged_parallel = {
            "detected": k_paths.get("detected", False) or o_paths.get("detected", False),
            "execute_all": k_paths.get("execute_all", False) or o_paths.get("execute_all", False),
            "paths": (k_paths.get("paths") or []) + (o_paths.get("paths") or []),
            "exclusive_choices": (k_paths.get("exclusive_choices") or []) + (o_paths.get("exclusive_choices") or []) or None,
            "reason": primary.get("parallel_paths", {}).get("reason", ""),
        }

        return {
            "enriched_prompt": enriched,
            "intent": primary.get("intent", "unknown"),
            "confidence": max(k_conf, o_conf),
            "dream_seeds": merged_seeds,
            "skill_chain": merged_chain or None,
            "project_refs": merged_refs,
            "route": primary.get("route", "direct"),
            "route_reason": primary.get("route_reason", ""),
            "learnings": merged_learnings,
            "knowledge_connections": merged_connections,
            "parallel_paths": merged_parallel,
            # Dual synthesis metadata
            "_dual_synthesis": True,
            "_perspectives": {
                "kimi": {
                    "provider": "kimi-k2",
                    "confidence": k_conf,
                    "intent": kimi.get("intent", "unknown"),
                    "route": kimi.get("route", "direct"),
                    "latency_ms": kimi.get("_latency_ms", 0),
                    "dream_seed_count": len(kimi.get("dream_seeds") or []),
                },
                "openai": {
                    "provider": "openai",
                    "confidence": o_conf,
                    "intent": openai.get("intent", "unknown"),
                    "route": openai.get("route", "direct"),
                    "latency_ms": openai.get("_latency_ms", 0),
                    "dream_seed_count": len(openai.get("dream_seeds") or []),
                },
            },
        }

    # ── Main entry points ────────────────────────────────────────
    async def synthesize_async(
        self,
        message: str,
        channel: str = None,
        anchor_turn_id: str = None,
    ) -> dict:
        """Run both synthesizers in parallel, merge results."""
        # Save incoming message
        message_id = self.add_context("user", message, channel)

        # Get shared context (computed once, used by both)
        context = await self.get_rich_context(message, anchor_turn_id)

        # HTDS topology context
        htds_context = ""
        if self._htds_context:
            try:
                htds_context = self._htds_context(message)
            except Exception:
                htds_context = "[HTDS] unavailable"

        prompt = self._build_prompt(message, context, channel, htds_context)

        # ── Run both in parallel ─────────────────────────────────
        kimi_result, openai_result = await asyncio.gather(
            self._call_kimi(prompt),
            self._call_openai(prompt),
            return_exceptions=True,
        )

        # Handle exceptions from gather
        if isinstance(kimi_result, Exception):
            kimi_result = _empty_result(message, f"Kimi exception: {kimi_result}")
            kimi_result["_provider"] = "kimi-k2"
        if isinstance(openai_result, Exception):
            openai_result = _empty_result(message, f"OpenAI exception: {openai_result}")
            openai_result["_provider"] = "openai"

        # ── Merge ────────────────────────────────────────────────
        merged = self._merge_results(kimi_result, openai_result, message)

        # Save synthesis result
        if self.memory and message_id:
            self.memory.save_synthesis(message_id, merged)
            learnings = merged.get("learnings", {})
            for fact in learnings.get("facts", []):
                self.memory.remember(fact["key"], fact["value"], "fact", 0.7)
            for pref in learnings.get("preferences", []):
                self.memory.remember(pref["key"], pref["value"], "preference", 0.8)
            for pattern in learnings.get("patterns", []):
                self.memory.remember(pattern["key"], pattern["value"], "pattern", 0.6)

        # Sync to Graph Kernel (background, non-blocking)
        if self.retriever:
            asyncio.create_task(self._sync_to_graph_kernel(merged))

        # Skill router integration
        self._enhance_with_skill_router(merged, message)

        return merged

    async def _sync_to_graph_kernel(self, result: dict):
        """Sync learnings and knowledge connections to Graph Kernel."""
        try:
            learnings = result.get("learnings", {})
            if learnings and self.retriever:
                await self.retriever.sync_learnings_to_graph_kernel(learnings)
            connections = result.get("knowledge_connections", [])
            if connections:
                from memory.graph_kernel_client import get_graph_kernel_client, KnowledgeTriple
                client = get_graph_kernel_client()
                triples = [
                    KnowledgeTriple(
                        subject=c["subject"], predicate=c["predicate"], object=c["object"],
                        confidence=0.7, source="dual-synthesis",
                    )
                    for c in connections
                ]
                await client.add_knowledge_batch(triples)
        except Exception as e:
            print(f"Graph Kernel sync failed: {e}", file=sys.stderr)

    def _enhance_with_skill_router(self, result: dict, message: str):
        """Enhance skill chain with intelligent routing (optional)."""
        try:
            import subprocess
            router_path = os.path.expanduser("~/.clawdbot/tools/skill-router.py")
            if os.path.exists(router_path):
                router_result = subprocess.run(
                    ["python3", router_path, "chain", message],
                    capture_output=True, text=True, timeout=5,
                )
                if router_result.returncode == 0:
                    router_data = json.loads(router_result.stdout)
                    routed_chain = router_data.get("chain", [])
                    existing = result.get("skill_chain") or []
                    seen = set(existing)
                    for skill in routed_chain:
                        if skill not in seen:
                            existing.append(skill)
                            seen.add(skill)
                    if existing:
                        result["skill_chain"] = existing
        except Exception:
            pass

    def synthesize(self, message: str, channel: str = None) -> dict:
        """Sync wrapper."""
        try:
            return asyncio.run(self.synthesize_async(message, channel))
        except RuntimeError:
            # Already running event loop — use thread
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.synthesize_async(message, channel),
                    )
                    return future.result(timeout=60)
            except Exception as e2:
                print(f"Threaded dual synthesis failed: {e2}", file=sys.stderr)
                return _empty_result(message, f"Thread fallback failed: {e2}")
        except Exception as e:
            print(f"Dual synthesis failed: {e}", file=sys.stderr)
            # Fallback: try Kimi alone
            try:
                from synthesizer import synthesize as kimi_synthesize
                return kimi_synthesize(message, channel)
            except Exception:
                return _empty_result(message, f"All providers failed: {e}")

    def get_stats(self) -> dict:
        """Get dual synthesis statistics."""
        stats = dict(self.stats)
        stats["providers"] = {
            "kimi": {"available": self.together_client is not None},
            "openai": {"available": self.openai_available},
        }
        if self.memory:
            stats["memory"] = self.memory.get_stats()
        if self.retriever:
            stats["services"] = {
                "graph_kernel": self.retriever._gk_available,
                "rag_plus_plus": self.retriever._rag_available,
            }
        return stats


# ── Singleton ────────────────────────────────────────────────────
_dual_synthesizer = None


def get_dual_synthesizer() -> DualSynthesizer:
    global _dual_synthesizer
    if _dual_synthesizer is None:
        _dual_synthesizer = DualSynthesizer()
    return _dual_synthesizer


def synthesize(message: str, channel: str = None) -> dict:
    """Main entry point — dual synthesis."""
    return get_dual_synthesizer().synthesize(message, channel)


async def synthesize_async(message: str, channel: str = None, anchor: str = None) -> dict:
    """Async entry point — dual synthesis."""
    return await get_dual_synthesizer().synthesize_async(message, channel, anchor)


def get_stats() -> dict:
    return get_dual_synthesizer().get_stats()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        print(json.dumps(get_stats(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "I want to build an AI-powered coffee ordering app"
        result = synthesize(msg)
        print(json.dumps(result, indent=2))
        print(f"\n--- Perspectives ---")
        for name, p in result.get("_perspectives", {}).items():
            print(f"  {name}: confidence={p['confidence']}, intent={p['intent']}, route={p['route']}, latency={p['latency_ms']}ms")
    else:
        msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test message"
        result = synthesize(msg)
        print(json.dumps(result, indent=2))
