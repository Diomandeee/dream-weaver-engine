"""Visual Dream Garden — ASCII + HTML renderer.

Usage:
  python -m dream_engine.garden_viz          # print ASCII garden
  python -m dream_engine.garden_viz --html   # also open HTML garden

Functions:
  garden_status()            → formatted ASCII string
  generate_garden_html(state) → writes garden.html
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import GardenState, Dream

# ── Stage icons & colours ────────────────────────────────────────────

STAGE_ICON = {
    "seed": "🌰",
    "germinating": "🌱",
    "growing": "🌿",
    "flowering": "🌸",
    "bloom": "🌺",
    "archived": "📦",
}

STAGE_COLOR_CSS = {
    "seed": "#8B4513",
    "germinating": "#90EE90",
    "growing": "#3CB371",
    "flowering": "#FF69B4",
    "bloom": "#FF1493",
    "archived": "#666",
}

# ── Helpers ──────────────────────────────────────────────────────────

def _strength_bar(strength: float, width: int = 10) -> str:
    filled = round(strength * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {strength:.2f}"


def _load_state() -> "GardenState":
    """Load state for the CLI entry point."""
    from .evolve import load_state
    return load_state()


# ── ASCII Garden ─────────────────────────────────────────────────────

def garden_status(state: Optional["GardenState"] = None) -> str:
    """Return a formatted ASCII garden string."""
    if state is None:
        state = _load_state()

    dreams = list(state.dreams.values())
    if not dreams:
        return "🏜️  The garden is empty. Plant some dreams!"

    lines: list[str] = []
    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║            🌙  D R E A M   G A R D E N  🌙            ║")
    lines.append("╠══════════════════════════════════════════════════════════╣")
    lines.append(f"║  Dreams: {len(dreams):<5}  Evolutions: {state.total_evolutions:<6} "
                 f"Blooms: {state.total_blooms:<5}║")
    lines.append("╠══════════════════════════════════════════════════════════╣")

    # Sort: blooms first, then by strength descending
    dreams_sorted = sorted(dreams, key=lambda d: (-d.strength, d.title))

    for d in dreams_sorted:
        icon = STAGE_ICON.get(d.stage.value if hasattr(d.stage, 'value') else d.stage, "❓")
        bar = _strength_bar(d.strength)
        title = d.title[:30].ljust(30)
        stage_label = (d.stage.value if hasattr(d.stage, 'value') else d.stage).upper()[:10].ljust(10)
        lines.append(f"║ {icon} {title} {stage_label} {bar} ║")

    # Connection map
    connections_found = False
    for d in dreams_sorted:
        if d.connections:
            if not connections_found:
                lines.append("╠══════════════════════════════════════════════════════════╣")
                lines.append("║  🔗 Connections                                         ║")
                connections_found = True
            for cid in d.connections:
                target = state.dreams.get(cid)
                target_name = target.title[:20] if target else cid[:20]
                lines.append(f"║    {d.title[:20]:20} ──── {target_name:20}       ║")

    lines.append("╚══════════════════════════════════════════════════════════╝")
    lines.append(f"  Last evolution: {state.last_evolution or 'never'}")

    return "\n".join(lines)


# ── HTML Garden ──────────────────────────────────────────────────────

def generate_garden_html(state: Optional["GardenState"] = None, output: Optional[Path] = None) -> Path:
    """Generate a dark-themed HTML garden dashboard.

    Returns the Path to the written file.
    """
    if state is None:
        state = _load_state()

    output = output or (Path(__file__).parent.parent / "garden.html")

    dreams = list(state.dreams.values())
    dreams_sorted = sorted(dreams, key=lambda d: (-d.strength, d.title))

    # Build dream cards HTML
    cards_html = ""
    for d in dreams_sorted:
        icon = STAGE_ICON.get(d.stage.value if hasattr(d.stage, 'value') else d.stage, "❓")
        stage_val = d.stage.value if hasattr(d.stage, 'value') else d.stage
        color = STAGE_COLOR_CSS.get(stage_val, "#888")
        pct = round(d.strength * 100)
        tags_html = " ".join(f'<span class="tag">{t}</span>' for t in d.tags[:5])
        connections_html = ""
        if d.connections:
            conn_names = []
            for cid in d.connections:
                target = state.dreams.get(cid)
                conn_names.append(target.title if target else cid)
            connections_html = f'<div class="connections">🔗 {", ".join(conn_names)}</div>'

        cards_html += f"""
    <div class="dream-card" style="border-left: 4px solid {color};" data-id="{d.id}">
      <div class="card-header">
        <span class="icon">{icon}</span>
        <span class="title">{_esc(d.title)}</span>
        <span class="stage" style="color:{color}">{stage_val.upper()}</span>
      </div>
      <div class="essence">{_esc(d.essence[:150])}</div>
      <div class="strength-bar-container">
        <div class="strength-bar" style="width:{pct}%; background:{color};"></div>
        <span class="strength-label">{d.strength:.2f}</span>
      </div>
      <div class="meta">
        Evolutions: {d.evolution_count} &middot; Created: {d.created_at.strftime('%Y-%m-%d') if d.created_at else '?'}
      </div>
      <div class="tags">{tags_html}</div>
      {connections_html}
    </div>"""

    # SVG connections
    svg_connections = _build_svg_connections(dreams_sorted, state)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>🌙 Dream Garden</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    padding: 2rem;
  }}
  h1 {{ text-align: center; font-size: 2rem; margin-bottom: 0.5rem; color: #e6edf3; }}
  .stats {{
    text-align: center; margin-bottom: 2rem; color: #8b949e; font-size: 0.95rem;
  }}
  .stats span {{ margin: 0 1rem; }}
  .garden-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.2rem;
    max-width: 1400px; margin: 0 auto;
    position: relative;
  }}
  .dream-card {{
    background: #161b22; border-radius: 8px; padding: 1rem;
    transition: transform 0.15s, box-shadow 0.15s;
  }}
  .dream-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.4); }}
  .card-header {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }}
  .icon {{ font-size: 1.5rem; }}
  .title {{ font-weight: 600; font-size: 1.05rem; flex: 1; color: #e6edf3; }}
  .stage {{ font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em; }}
  .essence {{ color: #8b949e; font-size: 0.85rem; margin-bottom: 0.6rem; line-height: 1.4; }}
  .strength-bar-container {{
    background: #21262d; border-radius: 4px; height: 20px;
    position: relative; overflow: hidden; margin-bottom: 0.5rem;
  }}
  .strength-bar {{ height: 100%; border-radius: 4px; transition: width 0.5s; }}
  .strength-label {{
    position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
    font-size: 0.75rem; font-weight: 600; color: #e6edf3;
  }}
  .meta {{ font-size: 0.75rem; color: #484f58; margin-bottom: 0.4rem; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 0.3rem; }}
  .tag {{
    background: #21262d; color: #8b949e; padding: 2px 8px;
    border-radius: 12px; font-size: 0.7rem;
  }}
  .connections {{ margin-top: 0.4rem; font-size: 0.8rem; color: #58a6ff; }}
  .generated {{ text-align: center; margin-top: 2rem; color: #484f58; font-size: 0.75rem; }}
  svg.conn {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }}
</style>
</head>
<body>
  <h1>🌙 Dream Garden</h1>
  <div class="stats">
    <span>🌿 {len(dreams)} Dreams</span>
    <span>🔄 {state.total_evolutions} Evolutions</span>
    <span>🌺 {state.total_blooms} Blooms</span>
    <span>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</span>
  </div>
  <div class="garden-grid">
    {cards_html}
  </div>
  <div class="generated">Generated by Dream Weaver Engine v3.0.0 &middot; Auto-refreshes every 5 min</div>
</body>
</html>"""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    print(f"[GardenViz] HTML garden written → {output}")
    return output


def _esc(text: str) -> str:
    """Basic HTML escape."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_svg_connections(dreams: list, state) -> str:
    """Placeholder — real SVG connections would need JS layout; skip for static HTML."""
    return ""


# ── CLI entry point ──────────────────────────────────────────────────

def main():
    import sys
    state = _load_state()
    print(garden_status(state))
    print()
    html_path = generate_garden_html(state)
    print(f"HTML garden: {html_path}")
    if "--open" in sys.argv:
        import webbrowser
        webbrowser.open(str(html_path))


if __name__ == "__main__":
    main()
