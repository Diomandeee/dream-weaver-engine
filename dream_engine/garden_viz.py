"""Visual Dream Garden v2 — Interactive HTML + ASCII renderer.

Usage:
  python -m dream_engine.garden_viz          # print ASCII garden
  python -m dream_engine.garden_viz --html   # also open HTML garden

v2 additions:
- Interactive filtering by stage
- SVG connection lines between related dreams
- Particle animations for bloom/flowering stages
- Dream detail panel on click
- Evolution timeline per dream
- Garden health metrics
- Dark mode with organic color palette

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


# ── HTML Garden v2 ───────────────────────────────────────────────────

def generate_garden_html(state: Optional["GardenState"] = None, output: Optional[Path] = None) -> Path:
    """Generate an interactive dark-themed HTML garden dashboard.

    Returns the Path to the written file.
    """
    if state is None:
        state = _load_state()

    output = output or (Path(__file__).parent.parent / "garden.html")

    dreams = list(state.dreams.values())
    dreams_sorted = sorted(dreams, key=lambda d: (-d.strength, d.title))

    # Stage counts for filter badges
    stage_counts = {}
    for d in dreams:
        sv = d.stage.value if hasattr(d.stage, 'value') else d.stage
        stage_counts[sv] = stage_counts.get(sv, 0) + 1

    # Build dream data as JSON for JS interactivity
    dreams_json = []
    for d in dreams_sorted:
        sv = d.stage.value if hasattr(d.stage, 'value') else d.stage
        dreams_json.append({
            "id": d.id,
            "title": d.title,
            "essence": d.essence[:300],
            "context": (d.context[:200] if hasattr(d, 'context') and d.context else ""),
            "strength": round(d.strength, 3),
            "stage": sv,
            "evolution_count": d.evolution_count,
            "tags": list(d.tags[:8]),
            "connections": list(d.connections) if d.connections else [],
            "created_at": d.created_at.strftime('%Y-%m-%d') if d.created_at else "?",
            "last_evolved": d.last_evolved.strftime('%Y-%m-%d %H:%M') if d.last_evolved else "never",
            "evolution_notes": list(d.evolution_notes[-5:]) if d.evolution_notes else [],
        })

    # Garden health metrics
    avg_strength = sum(d.strength for d in dreams) / len(dreams) if dreams else 0
    active_count = sum(1 for d in dreams if d.stage.value != "archived") if dreams else 0
    bloom_count = sum(1 for d in dreams if d.stage.value == "bloom") if dreams else 0
    stale_count = sum(1 for d in dreams 
                      if d.last_evolved and (datetime.utcnow() - d.last_evolved).days > 7
                      and d.stage.value not in ("bloom", "archived")) if dreams else 0

    html = _build_html(
        dreams_json=json.dumps(dreams_json),
        total_dreams=len(dreams),
        total_evolutions=state.total_evolutions,
        total_blooms=state.total_blooms,
        stage_counts=json.dumps(stage_counts),
        avg_strength=round(avg_strength, 3),
        active_count=active_count,
        bloom_count=bloom_count,
        stale_count=stale_count,
        generated_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    print(f"[GardenViz] HTML garden written → {output}")
    return output


def _build_html(**ctx) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>🌙 Dream Garden</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0a0e14; color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    padding: 1.5rem;
    min-height: 100vh;
  }}

  /* Header */
  .header {{
    text-align: center;
    margin-bottom: 1.5rem;
    position: relative;
  }}
  h1 {{
    font-size: 2.2rem;
    color: #e6edf3;
    letter-spacing: 0.15em;
    text-shadow: 0 0 30px rgba(255,20,147,0.3);
  }}

  /* Health metrics bar */
  .health-bar {{
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin: 1rem 0;
    flex-wrap: wrap;
  }}
  .metric {{
    text-align: center;
    padding: 0.5rem 1rem;
    background: rgba(22,27,34,0.8);
    border-radius: 12px;
    border: 1px solid #21262d;
  }}
  .metric .value {{
    font-size: 1.8rem;
    font-weight: 700;
    color: #e6edf3;
  }}
  .metric .label {{
    font-size: 0.75rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  .metric.health-good .value {{ color: #3fb950; }}
  .metric.health-warn .value {{ color: #d29922; }}
  .metric.health-bad .value  {{ color: #f85149; }}

  /* Filter bar */
  .filter-bar {{
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }}
  .filter-btn {{
    padding: 6px 16px;
    border-radius: 20px;
    border: 1px solid #30363d;
    background: #161b22;
    color: #8b949e;
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;
    user-select: none;
  }}
  .filter-btn:hover {{ border-color: #58a6ff; color: #58a6ff; }}
  .filter-btn.active {{
    background: #1f6feb;
    border-color: #1f6feb;
    color: #fff;
  }}
  .filter-btn .count {{
    background: rgba(255,255,255,0.15);
    padding: 1px 6px;
    border-radius: 10px;
    font-size: 0.7rem;
    margin-left: 4px;
  }}

  /* Garden grid */
  .garden-container {{
    position: relative;
    max-width: 1500px;
    margin: 0 auto;
  }}
  .garden-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
    position: relative;
  }}

  /* Dream cards */
  .dream-card {{
    background: #161b22;
    border-radius: 10px;
    padding: 1rem;
    border-left: 4px solid #888;
    transition: all 0.2s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
  }}
  .dream-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 6px 24px rgba(0,0,0,0.5);
  }}
  .dream-card.stage-bloom {{
    animation: bloom-glow 3s ease-in-out infinite alternate;
  }}
  @keyframes bloom-glow {{
    from {{ box-shadow: 0 0 8px rgba(255,20,147,0.2); }}
    to   {{ box-shadow: 0 0 20px rgba(255,20,147,0.5); }}
  }}
  .dream-card.hidden {{ display: none; }}

  .card-header {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }}
  .icon {{ font-size: 1.5rem; }}
  .title {{
    font-weight: 600;
    font-size: 1rem;
    flex: 1;
    color: #e6edf3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .stage {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(255,255,255,0.05);
  }}
  .essence {{
    color: #8b949e;
    font-size: 0.82rem;
    margin-bottom: 0.6rem;
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .strength-bar-container {{
    background: #21262d;
    border-radius: 4px;
    height: 18px;
    position: relative;
    overflow: hidden;
    margin-bottom: 0.5rem;
  }}
  .strength-bar {{
    height: 100%;
    border-radius: 4px;
    transition: width 1s ease;
    position: relative;
  }}
  .strength-bar::after {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%);
    animation: shimmer 2s infinite;
  }}
  @keyframes shimmer {{
    from {{ transform: translateX(-100%); }}
    to   {{ transform: translateX(100%); }}
  }}
  .strength-label {{
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.72rem;
    font-weight: 600;
    color: #e6edf3;
    text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  }}
  .meta {{
    font-size: 0.72rem;
    color: #484f58;
    margin-bottom: 0.4rem;
  }}
  .tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }}
  .tag {{
    background: #21262d;
    color: #8b949e;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.68rem;
  }}
  .connections {{
    margin-top: 0.4rem;
    font-size: 0.78rem;
    color: #58a6ff;
  }}

  /* Evolution trail (mini sparkline) */
  .evo-trail {{
    font-size: 0.7rem;
    color: #484f58;
    margin-top: 0.3rem;
  }}
  .evo-trail span {{
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-right: 2px;
    vertical-align: middle;
  }}

  /* Detail panel */
  .detail-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7);
    z-index: 100;
    backdrop-filter: blur(4px);
  }}
  .detail-overlay.visible {{ display: flex; align-items: center; justify-content: center; }}
  .detail-panel {{
    background: #161b22;
    border-radius: 16px;
    padding: 2rem;
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    border: 1px solid #30363d;
    box-shadow: 0 16px 48px rgba(0,0,0,0.6);
  }}
  .detail-panel h2 {{
    color: #e6edf3;
    margin-bottom: 0.5rem;
    font-size: 1.4rem;
  }}
  .detail-panel .detail-essence {{
    color: #8b949e;
    line-height: 1.6;
    margin-bottom: 1rem;
  }}
  .detail-panel .detail-context {{
    color: #6e7681;
    font-style: italic;
    margin-bottom: 1rem;
    padding: 0.8rem;
    background: rgba(255,255,255,0.03);
    border-radius: 8px;
  }}
  .detail-panel .evo-notes {{
    margin-top: 1rem;
  }}
  .detail-panel .evo-note {{
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.5rem;
    background: rgba(255,255,255,0.03);
    border-left: 3px solid #30363d;
    border-radius: 0 6px 6px 0;
    font-size: 0.85rem;
    color: #8b949e;
    line-height: 1.5;
  }}
  .close-btn {{
    float: right;
    background: none;
    border: none;
    color: #8b949e;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0 8px;
  }}
  .close-btn:hover {{ color: #f85149; }}

  /* SVG connections overlay */
  .connections-svg {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
  }}
  .connections-svg line {{
    stroke: rgba(88,166,255,0.3);
    stroke-width: 1.5;
    stroke-dasharray: 5 5;
    animation: dash 20s linear infinite;
  }}
  @keyframes dash {{
    to {{ stroke-dashoffset: -100; }}
  }}

  /* Particles for blooming dreams */
  .particle-container {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    overflow: hidden;
  }}
  .particle {{
    position: absolute;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    opacity: 0;
    animation: float-up 4s ease-in-out infinite;
  }}
  @keyframes float-up {{
    0%   {{ opacity: 0; transform: translateY(0) scale(0); }}
    20%  {{ opacity: 0.8; }}
    100% {{ opacity: 0; transform: translateY(-60px) scale(1.5); }}
  }}

  .generated {{
    text-align: center;
    margin-top: 2rem;
    color: #484f58;
    font-size: 0.72rem;
  }}

  /* Responsive */
  @media (max-width: 768px) {{
    .health-bar {{ gap: 0.5rem; }}
    .metric {{ padding: 0.3rem 0.6rem; }}
    .metric .value {{ font-size: 1.3rem; }}
    .garden-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🌙 Dream Garden</h1>
</div>

<div class="health-bar">
  <div class="metric">
    <div class="value">🌿 {ctx['total_dreams']}</div>
    <div class="label">Dreams</div>
  </div>
  <div class="metric">
    <div class="value">🔄 {ctx['total_evolutions']}</div>
    <div class="label">Evolutions</div>
  </div>
  <div class="metric">
    <div class="value">🌺 {ctx['total_blooms']}</div>
    <div class="label">Blooms</div>
  </div>
  <div class="metric {'health-good' if ctx['avg_strength'] > 0.5 else 'health-warn' if ctx['avg_strength'] > 0.3 else 'health-bad'}">
    <div class="value">{ctx['avg_strength']:.0%}</div>
    <div class="label">Avg Strength</div>
  </div>
  <div class="metric {'health-bad' if ctx['stale_count'] > 3 else 'health-warn' if ctx['stale_count'] > 0 else 'health-good'}">
    <div class="value">{ctx['stale_count']}</div>
    <div class="label">Stale (7d+)</div>
  </div>
</div>

<div class="filter-bar" id="filterBar"></div>

<div class="garden-container">
  <svg class="connections-svg" id="connectionsSvg"></svg>
  <div class="garden-grid" id="gardenGrid"></div>
</div>

<!-- Detail overlay -->
<div class="detail-overlay" id="detailOverlay">
  <div class="detail-panel" id="detailPanel">
    <button class="close-btn" onclick="closeDetail()">&times;</button>
    <div id="detailContent"></div>
  </div>
</div>

<div class="generated">
  Dream Weaver Engine v3.1.0 &middot; {ctx['generated_at']} &middot; Auto-refreshes every 5 min
</div>

<script>
const DREAMS = {ctx['dreams_json']};
const STAGE_COUNTS = {ctx['stage_counts']};
const STAGE_ICONS = {{
  seed: '🌰', germinating: '🌱', growing: '🌿',
  flowering: '🌸', bloom: '🌺', archived: '📦'
}};
const STAGE_COLORS = {{
  seed: '#8B4513', germinating: '#90EE90', growing: '#3CB371',
  flowering: '#FF69B4', bloom: '#FF1493', archived: '#666'
}};

let activeFilter = 'all';

// Build filter bar
function buildFilters() {{
  const bar = document.getElementById('filterBar');
  const total = DREAMS.length;
  bar.innerHTML = `<button class="filter-btn active" data-stage="all">All <span class="count">${{total}}</span></button>`;
  for (const [stage, count] of Object.entries(STAGE_COUNTS)) {{
    const icon = STAGE_ICONS[stage] || '❓';
    bar.innerHTML += `<button class="filter-btn" data-stage="${{stage}}">${{icon}} ${{stage}} <span class="count">${{count}}</span></button>`;
  }}
  bar.querySelectorAll('.filter-btn').forEach(btn => {{
    btn.addEventListener('click', () => filterByStage(btn.dataset.stage));
  }});
}}

// Filter dreams by stage
function filterByStage(stage) {{
  activeFilter = stage;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-stage="${{stage}}"]`).classList.add('active');

  document.querySelectorAll('.dream-card').forEach(card => {{
    if (stage === 'all' || card.dataset.stage === stage) {{
      card.classList.remove('hidden');
    }} else {{
      card.classList.add('hidden');
    }}
  }});
  drawConnections();
}}

// Build dream cards
function buildCards() {{
  const grid = document.getElementById('gardenGrid');
  grid.innerHTML = '';

  DREAMS.forEach((d, idx) => {{
    const color = STAGE_COLORS[d.stage] || '#888';
    const icon = STAGE_ICONS[d.stage] || '❓';
    const pct = Math.round(d.strength * 100);

    const tagsHtml = d.tags.map(t => `<span class="tag">${{esc(t)}}</span>`).join('');
    const connHtml = d.connections.length > 0
      ? `<div class="connections">🔗 ${{d.connections.length}} connection${{d.connections.length > 1 ? 's' : ''}}</div>`
      : '';

    // Evolution trail dots
    const trailDots = Array.from({{length: Math.min(d.evolution_count, 20)}}, (_, i) => {{
      const opacity = 0.3 + (i / 20) * 0.7;
      return `<span style="background:${{color}};opacity:${{opacity}}"></span>`;
    }}).join('');
    const trailHtml = d.evolution_count > 0
      ? `<div class="evo-trail">${{trailDots}} ${{d.evolution_count}} evolutions</div>`
      : '';

    const cardClass = d.stage === 'bloom' ? 'dream-card stage-bloom' : 'dream-card';

    const card = document.createElement('div');
    card.className = cardClass;
    card.dataset.id = d.id;
    card.dataset.stage = d.stage;
    card.dataset.idx = idx;
    card.style.borderLeftColor = color;
    card.innerHTML = `
      <div class="card-header">
        <span class="icon">${{icon}}</span>
        <span class="title">${{esc(d.title)}}</span>
        <span class="stage" style="color:${{color}}">${{d.stage.toUpperCase()}}</span>
      </div>
      <div class="essence">${{esc(d.essence)}}</div>
      <div class="strength-bar-container">
        <div class="strength-bar" style="width:${{pct}}%; background: linear-gradient(90deg, ${{color}}88, ${{color}});"></div>
        <span class="strength-label">${{d.strength.toFixed(2)}}</span>
      </div>
      <div class="meta">
        Evolutions: ${{d.evolution_count}} · Created: ${{d.created_at}} · Last: ${{d.last_evolved}}
      </div>
      <div class="tags">${{tagsHtml}}</div>
      ${{connHtml}}
      ${{trailHtml}}
      ${{d.stage === 'bloom' ? buildParticles(color) : ''}}
    `;
    card.addEventListener('click', () => showDetail(d));
    grid.appendChild(card);
  }});
}}

// Build particle HTML for bloom cards
function buildParticles(color) {{
  let html = '<div class="particle-container">';
  for (let i = 0; i < 6; i++) {{
    const left = 10 + Math.random() * 80;
    const delay = Math.random() * 4;
    const size = 3 + Math.random() * 3;
    html += `<div class="particle" style="left:${{left}}%;bottom:0;width:${{size}}px;height:${{size}}px;background:${{color}};animation-delay:${{delay}}s;"></div>`;
  }}
  return html + '</div>';
}}

// Draw SVG connection lines
function drawConnections() {{
  const svg = document.getElementById('connectionsSvg');
  svg.innerHTML = '';
  const grid = document.getElementById('gardenGrid');
  const gridRect = grid.getBoundingClientRect();

  DREAMS.forEach(d => {{
    if (d.connections.length === 0) return;
    const sourceCard = document.querySelector(`[data-id="${{d.id}}"]`);
    if (!sourceCard || sourceCard.classList.contains('hidden')) return;

    d.connections.forEach(connId => {{
      const targetCard = document.querySelector(`[data-id="${{connId}}"]`);
      if (!targetCard || targetCard.classList.contains('hidden')) return;

      const sRect = sourceCard.getBoundingClientRect();
      const tRect = targetCard.getBoundingClientRect();

      const x1 = sRect.left + sRect.width / 2 - gridRect.left;
      const y1 = sRect.top + sRect.height / 2 - gridRect.top;
      const x2 = tRect.left + tRect.width / 2 - gridRect.left;
      const y2 = tRect.top + tRect.height / 2 - gridRect.top;

      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', x1);
      line.setAttribute('y1', y1);
      line.setAttribute('x2', x2);
      line.setAttribute('y2', y2);
      svg.appendChild(line);
    }});
  }});

  // Size SVG to grid
  svg.style.height = grid.scrollHeight + 'px';
}}

// Detail panel
function showDetail(dream) {{
  const overlay = document.getElementById('detailOverlay');
  const content = document.getElementById('detailContent');
  const icon = STAGE_ICONS[dream.stage] || '❓';
  const color = STAGE_COLORS[dream.stage] || '#888';
  const pct = Math.round(dream.strength * 100);

  const tagsHtml = dream.tags.map(t => `<span class="tag">${{esc(t)}}</span>`).join(' ');
  const notesHtml = dream.evolution_notes.map(n =>
    `<div class="evo-note">${{esc(n)}}</div>`
  ).join('');

  content.innerHTML = `
    <h2>${{icon}} ${{esc(dream.title)}}</h2>
    <div class="stage" style="color:${{color}};display:inline-block;margin-bottom:1rem;">
      ${{dream.stage.toUpperCase()}} · ${{dream.evolution_count}} evolutions
    </div>

    <div class="detail-essence">${{esc(dream.essence)}}</div>
    ${{dream.context ? `<div class="detail-context">${{esc(dream.context)}}</div>` : ''}}

    <div class="strength-bar-container" style="margin-bottom:1rem;">
      <div class="strength-bar" style="width:${{pct}}%; background: linear-gradient(90deg, ${{color}}88, ${{color}});"></div>
      <span class="strength-label">${{dream.strength.toFixed(3)}}</span>
    </div>

    <div style="margin-bottom:1rem;">
      <strong style="color:#e6edf3;">Stage Progression:</strong>
      <div style="font-size:1.5rem;margin-top:0.3rem;">
        ${{['seed','germinating','growing','flowering','bloom'].map(s => {{
          const active = ['seed','germinating','growing','flowering','bloom'].indexOf(dream.stage) >= ['seed','germinating','growing','flowering','bloom'].indexOf(s);
          return `<span style="opacity:${{active ? 1 : 0.25}}">${{STAGE_ICONS[s]}}</span>`;
        }}).join(' → ')}}
      </div>
    </div>

    <div class="tags" style="margin-bottom:1rem;">${{tagsHtml}}</div>

    <div style="font-size:0.82rem;color:#484f58;margin-bottom:0.5rem;">
      Created: ${{dream.created_at}} · Last Evolved: ${{dream.last_evolved}}
    </div>

    ${{dream.connections.length > 0 ? `
      <div style="margin-bottom:1rem;">
        <strong style="color:#58a6ff;">🔗 Connections:</strong>
        ${{dream.connections.map(c => {{
          const target = DREAMS.find(d => d.id === c);
          return `<span class="tag" style="background:#1f6feb22;color:#58a6ff;">${{target ? esc(target.title) : c}}</span>`;
        }}).join(' ')}}
      </div>
    ` : ''}}

    ${{notesHtml ? `
      <div class="evo-notes">
        <strong style="color:#e6edf3;">Recent Evolution Notes:</strong>
        ${{notesHtml}}
      </div>
    ` : ''}}
  `;
  overlay.classList.add('visible');
}}

function closeDetail() {{
  document.getElementById('detailOverlay').classList.remove('visible');
}}

// Close on overlay click (not panel click)
document.getElementById('detailOverlay').addEventListener('click', (e) => {{
  if (e.target === document.getElementById('detailOverlay')) closeDetail();
}});

// Escape key closes detail
document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') closeDetail();
}});

function esc(text) {{
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}}

// Init
buildFilters();
buildCards();
setTimeout(drawConnections, 100);
window.addEventListener('resize', drawConnections);
</script>
</body>
</html>"""


def _esc(text: str) -> str:
    """Basic HTML escape."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


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
