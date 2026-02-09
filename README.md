# Dream Weaver Engine 🌱

Autonomous dream incubation system that runs independently via GitHub Actions, powered by Kimi-K2-Thinking.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DREAM WEAVER ENGINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TRIGGERS                    PROCESS                  OUTPUT    │
│  ────────                    ───────                  ──────    │
│  ⏰ Cron (30min)    ──▶    🧠 Evolution    ──▶    📢 Discord   │
│  📝 Push (dreams/)          (Kimi-K2)              (webhooks)   │
│  🔘 Manual dispatch          │                        │        │
│                              ▼                        ▼        │
│                         💾 State               #blooms         │
│                         (dreams.json)          #garden         │
│                                                #dream-journal  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Model

**Kimi-K2-Thinking** (`moonshotai/Kimi-K2-Thinking`)
- Context: 256K tokens
- Pricing: $1.20/M input, $4.00/M output
- Provider: Together AI

## Dream Lifecycle

```
SEED (0.1) → GERMINATING (0.3) → GROWING (0.5) → FLOWERING (0.7) → BLOOM (0.9+)
```

Each evolution cycle:
1. Loads all dreams from `dreams/`
2. Selects dreams ready for evolution
3. Calls Kimi-K2 with dream context + cross-pollination
4. Updates strength scores
5. Commits state changes
6. Posts notifications to Discord

## Setup

1. Fork this repo
2. Add secrets:
   - `TOGETHER_API_KEY` - Together AI API key
   - `DISCORD_WEBHOOK_BLOOMS` - Webhook for #blooms channel
   - `DISCORD_WEBHOOK_GARDEN` - Webhook for #garden channel
   - `DISCORD_WEBHOOK_JOURNAL` - Webhook for #dream-journal channel

3. Enable GitHub Actions

## Manual Trigger

```bash
gh workflow run evolve.yml
```

## Local Development

```bash
pip install -r requirements.txt
python -m dream_engine.evolve
```

## File Structure

```
dream-weaver-engine/
├── .github/
│   └── workflows/
│       ├── evolve.yml      # Main evolution cycle (cron)
│       ├── bloom.yml       # Bloom announcements
│       └── seed.yml        # New seed processing
├── dream_engine/
│   ├── __init__.py
│   ├── evolve.py           # Evolution logic
│   ├── models.py           # Dream data models
│   ├── together_client.py  # Kimi-K2 client
│   ├── discord.py          # Discord webhook integration
│   └── prompts/
│       ├── evolve.md       # Evolution prompt
│       ├── cross_pollinate.md
│       └── bloom.md
├── dreams/                 # Dream state files
│   └── .gitkeep
├── state/
│   └── dreams.json         # Master state
├── requirements.txt
└── README.md
```
