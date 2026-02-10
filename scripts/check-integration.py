#!/usr/bin/env python3
"""
Unified Integration Health Check for Kimi K2 Synthesis Pipeline.

Verifies:
  1. TOGETHER_API_KEY is set
  2. Graph Kernel (:8001) is healthy
  3. RAG++ (:8000) is healthy
  4. Kimi memory DB exists and has data
  5. Synthesis works end-to-end (optional --live flag)

Usage:
  python3 check-integration.py          # Quick health check
  python3 check-integration.py --live   # Full end-to-end synthesis test
  python3 check-integration.py --json   # Machine-readable output
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DB = PROJECT_ROOT / "memory" / "kimi_memory.db"
SYNTHESIZER = PROJECT_ROOT / "synthesis" / "synthesizer.py"
PYTHON_PATH = PROJECT_ROOT / ".venv" / "bin" / "python3"
ENV_FILE = PROJECT_ROOT / ".env"

# Service URLs
GRAPH_KERNEL_URL = "http://127.0.0.1:8001"
RAG_PP_URL = "http://127.0.0.1:8000"

# Results
results = []


def check(name: str, passed: bool, detail: str = ""):
    """Record a check result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({
        "name": name,
        "passed": passed,
        "detail": detail,
    })
    if not json_mode:
        print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))
    return passed


def check_env_vars():
    """Check that required environment variables are set."""
    api_key = os.environ.get("TOGETHER_API_KEY", "")
    
    # Also check .env file
    env_key = ""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("TOGETHER_API_KEY="):
                env_key = line.split("=", 1)[1].strip()
    
    key = api_key or env_key
    if key:
        check("TOGETHER_API_KEY", True, f"set ({key[:8]}...)")
    else:
        check("TOGETHER_API_KEY", False, "not found in env or .env file")
    
    synth_flag = os.environ.get("ENABLE_SYNTHESIS", "")
    check("ENABLE_SYNTHESIS", synth_flag in ("1", "true"),
          f"value='{synth_flag}'" if synth_flag else "not set")


def check_service(name: str, url: str):
    """Check that a service is healthy."""
    try:
        req = Request(f"{url}/health", method="GET")
        resp = urlopen(req, timeout=5)
        data = resp.read().decode()
        check(name, True, f"HTTP {resp.status} — {data[:100]}")
    except URLError as e:
        check(name, False, f"connection failed: {e.reason}")
    except Exception as e:
        check(name, False, str(e))


def check_memory_db():
    """Check that the Kimi memory DB exists and has data."""
    if not MEMORY_DB.exists():
        check("Kimi Memory DB", False, f"not found at {MEMORY_DB}")
        return
    
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        
        msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        synth_count = conn.execute("SELECT COUNT(*) FROM synthesis_results").fetchone()[0]
        ctx_count = conn.execute("SELECT COUNT(*) FROM context_memory").fetchone()[0]
        kg_count = conn.execute("SELECT COUNT(*) FROM knowledge_graph").fetchone()[0]
        conn.close()
        
        check("Kimi Memory DB", True,
              f"messages={msg_count}, syntheses={synth_count}, "
              f"context={ctx_count}, knowledge={kg_count}")
        
        if msg_count == 0:
            check("DB has messages", False, "0 messages — sync may not be working")
        else:
            check("DB has messages", True, f"{msg_count} messages")
    except Exception as e:
        check("Kimi Memory DB", False, str(e))


def check_python_env():
    """Check that the Python venv and synthesizer exist."""
    check("Python venv", PYTHON_PATH.exists(), str(PYTHON_PATH))
    check("Synthesizer script", SYNTHESIZER.exists(), str(SYNTHESIZER))
    
    # Check that together package is installed
    if PYTHON_PATH.exists():
        try:
            result = subprocess.run(
                [str(PYTHON_PATH), "-c", "import together; print(together.__version__)"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                check("together package", True, f"v{result.stdout.strip()}")
            else:
                check("together package", False, result.stderr.strip()[:200])
        except Exception as e:
            check("together package", False, str(e))


def check_plugin_config():
    """Check Clawdbot plugin configuration."""
    config_path = Path.home() / ".clawdbot" / "clawdbot.json"
    if not config_path.exists():
        check("Clawdbot config", False, "clawdbot.json not found")
        return
    
    try:
        config = json.loads(config_path.read_text())
        plugin_conf = config.get("plugins", {}).get("entries", {}).get("kimi-memory-sync", {})
        
        enabled = plugin_conf.get("enabled", False)
        check("Plugin enabled", enabled, json.dumps(plugin_conf.get("config", {})))
        
        synth_enabled = plugin_conf.get("config", {}).get("enableSynthesis", False)
        check("Plugin enableSynthesis", synth_enabled, f"value={synth_enabled}")
    except Exception as e:
        check("Clawdbot config", False, str(e))


def check_hook_registration():
    """Check that the synthesis-preprocessor hook is properly set up."""
    hook_dir = Path.home() / ".clawdbot" / "hooks" / "synthesis-preprocessor"
    hook_md = hook_dir / "HOOK.md"
    hook_js = hook_dir / "index.js"
    
    check("Hook directory", hook_dir.exists(), str(hook_dir))
    check("Hook HOOK.md", hook_md.exists(), str(hook_md))
    check("Hook index.js", hook_js.exists(), str(hook_js))


def run_live_synthesis():
    """Run a live end-to-end synthesis test."""
    if not PYTHON_PATH.exists() or not SYNTHESIZER.exists():
        check("Live synthesis", False, "python or synthesizer not found")
        return
    
    api_key = os.environ.get("TOGETHER_API_KEY", "")
    if not api_key and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("TOGETHER_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
    
    if not api_key:
        check("Live synthesis", False, "no API key available")
        return
    
    try:
        env = os.environ.copy()
        env["TOGETHER_API_KEY"] = api_key
        env["ENABLE_SYNTHESIS"] = "1"
        
        result = subprocess.run(
            [str(PYTHON_PATH), str(SYNTHESIZER), "Integration test: What's the status of the dream garden?"],
            capture_output=True, text=True, timeout=60, env=env
        )
        
        if result.returncode != 0:
            check("Live synthesis", False, f"exit {result.returncode}: {result.stderr[:300]}")
            return
        
        try:
            synth = json.loads(result.stdout.strip())
            intent = synth.get("intent", "unknown")
            route = synth.get("route", "unknown")
            seeds = len(synth.get("dream_seeds", []))
            connections = len(synth.get("knowledge_connections", []))
            
            check("Live synthesis", True,
                  f"intent={intent}, route={route}, seeds={seeds}, connections={connections}")
            
            # Verify DB was updated
            if MEMORY_DB.exists():
                conn = sqlite3.connect(str(MEMORY_DB))
                latest = conn.execute(
                    "SELECT content FROM messages ORDER BY id DESC LIMIT 1"
                ).fetchone()
                conn.close()
                if latest and "Integration test" in latest[0]:
                    check("DB updated from synthesis", True, "test message found in DB")
                else:
                    check("DB updated from synthesis", False, "test message not found")
        except json.JSONDecodeError:
            check("Live synthesis", False, f"invalid JSON output: {result.stdout[:200]}")
    except subprocess.TimeoutExpired:
        check("Live synthesis", False, "timed out after 60s")
    except Exception as e:
        check("Live synthesis", False, str(e))


def main():
    global json_mode
    
    live = "--live" in sys.argv
    json_mode = "--json" in sys.argv
    
    if not json_mode:
        print(f"\n{'='*60}")
        print(f"  Kimi K2 Synthesis Integration Check")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        print("📋 Environment Variables:")
    check_env_vars()
    
    if not json_mode:
        print("\n🐍 Python Environment:")
    check_python_env()
    
    if not json_mode:
        print("\n🗄️  Memory Database:")
    check_memory_db()
    
    if not json_mode:
        print("\n🔌 Clawdbot Plugin:")
    check_plugin_config()
    
    if not json_mode:
        print("\n🪝 Hook Registration:")
    check_hook_registration()
    
    if not json_mode:
        print("\n🌐 Services:")
    check_service("Graph Kernel (:8001)", GRAPH_KERNEL_URL)
    check_service("RAG++ (:8000)", RAG_PP_URL)
    
    if live:
        if not json_mode:
            print("\n🧪 Live Synthesis Test:")
        run_live_synthesis()
    
    # Summary
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    
    if json_mode:
        print(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "passed": passed,
            "failed": failed,
            "total": total,
            "healthy": failed == 0,
            "checks": results,
        }, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  Results: {passed}/{total} passed, {failed} failed")
        print(f"  Status: {'🟢 HEALTHY' if failed == 0 else '🔴 ISSUES FOUND'}")
        print(f"{'='*60}\n")
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    json_mode = False
    main()
