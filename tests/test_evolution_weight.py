"""Tests for EvoCube.evolution_weight static method."""

from datetime import datetime, timedelta

from dream_engine.evo_cube import EvoCube
from dream_engine.models import Dream, DreamStage, GardenState


# --- weight formula ---


def _dream(strength=0.1, evolution_count=0, last_evolved=None, **kw):
    """Helper to build a Dream with sensible defaults."""
    return Dream(
        id=kw.get("id", "test"),
        title=kw.get("title", "Test Dream"),
        essence="test essence",
        strength=strength,
        evolution_count=evolution_count,
        last_evolved=last_evolved,
    )


def test_never_evolved_seed_max_weight():
    """A fresh seed (str=0.1, evos=0, never evolved) should get ~0.9."""
    d = _dream(strength=0.1, evolution_count=0, last_evolved=None)
    w = EvoCube.evolution_weight(d)
    assert abs(w - 0.9) < 1e-6


def test_bloom_at_full_strength_zero_weight():
    """A bloom at strength 1.0 should always get weight 0.0."""
    d = _dream(strength=1.0, evolution_count=100)
    w = EvoCube.evolution_weight(d)
    assert w == 0.0


def test_recency_penalty_zero_when_just_evolved():
    """A dream evolved 0 seconds ago gets recency_penalty = 0 → weight 0."""
    now = datetime(2026, 2, 18, 12, 0, 0)
    d = _dream(strength=0.1, evolution_count=0, last_evolved=now)
    w = EvoCube.evolution_weight(d, now=now)
    assert w == 0.0


def test_recency_penalty_full_after_six_hours():
    """After 6 hours the recency penalty saturates at 1.0."""
    now = datetime(2026, 2, 18, 12, 0, 0)
    d = _dream(strength=0.1, evolution_count=0, last_evolved=now - timedelta(hours=6))
    w = EvoCube.evolution_weight(d, now=now)
    assert abs(w - 0.9) < 1e-6


def test_recency_penalty_scales_linearly():
    """3 hours → recency_penalty = 0.5."""
    now = datetime(2026, 2, 18, 12, 0, 0)
    d = _dream(strength=0.1, evolution_count=0, last_evolved=now - timedelta(hours=3))
    w = EvoCube.evolution_weight(d, now=now)
    expected = 0.9 * 1.0 * 0.5  # (1-0.1) * (1/1) * (3/6)
    assert abs(w - expected) < 1e-6


def test_recency_penalty_caps_at_one():
    """Even 100 hours shouldn't push penalty above 1.0."""
    now = datetime(2026, 2, 18, 12, 0, 0)
    d = _dream(strength=0.5, evolution_count=3, last_evolved=now - timedelta(hours=100))
    w = EvoCube.evolution_weight(d, now=now)
    expected = 0.5 * (1 / 4) * 1.0
    assert abs(w - expected) < 1e-6


def test_evolution_count_dampens_weight():
    """More evolutions → lower weight due to 1/(count+1)."""
    d0 = _dream(strength=0.3, evolution_count=0)
    d5 = _dream(strength=0.3, evolution_count=5)
    w0 = EvoCube.evolution_weight(d0)
    w5 = EvoCube.evolution_weight(d5)
    assert w0 > w5


def test_seeds_above_blooms_typical():
    """Typical seeds outrank typical blooms.

    Seeds have low strength and few evolutions; blooms have high strength
    and many evolutions. The formula naturally ranks seeds above blooms
    in realistic scenarios.
    """
    seed = _dream(strength=0.15, evolution_count=1)
    bloom = _dream(strength=0.85, evolution_count=10)
    ws = EvoCube.evolution_weight(seed)
    wb = EvoCube.evolution_weight(bloom)
    assert ws > wb


def test_full_bloom_always_zero():
    """strength=1.0 always yields weight=0 regardless of other factors."""
    d = _dream(strength=1.0, evolution_count=0, last_evolved=None)
    assert EvoCube.evolution_weight(d) == 0.0


def test_strength_zero_gives_max_base():
    """strength=0 → (1-0)=1 → max base weight."""
    d = _dream(strength=0.0, evolution_count=0)
    w = EvoCube.evolution_weight(d)
    assert abs(w - 1.0) < 1e-6


# --- rank_evolution_queue ---


def test_rank_evolution_queue_order():
    """rank_evolution_queue should return dreams sorted by weight descending."""
    state = GardenState()
    now = datetime(2026, 2, 18, 12, 0, 0)

    d1 = _dream(id="seed", title="Fresh Seed", strength=0.1, evolution_count=0)
    d2 = _dream(id="mid", title="Mid Dream", strength=0.5, evolution_count=3,
                last_evolved=now - timedelta(hours=12))
    d3 = _dream(id="bloom", title="Near Bloom", strength=0.9, evolution_count=10,
                last_evolved=now - timedelta(hours=12))

    state.add_dream(d1)
    state.add_dream(d2)
    state.add_dream(d3)

    cube = EvoCube.__new__(EvoCube)  # Avoid __init__ side effects
    cube.enable_depth = False
    cube.stats = {}

    ranked = cube.rank_evolution_queue(state, max_count=10)
    titles = [d.title for d in ranked]
    assert titles == ["Fresh Seed", "Mid Dream", "Near Bloom"]


def test_rank_evolution_queue_excludes_archived():
    """Archived dreams should not appear in the queue."""
    state = GardenState()
    d1 = _dream(id="active", title="Active", strength=0.1)
    d2 = _dream(id="archived", title="Archived", strength=0.1)
    d2.stage = DreamStage.ARCHIVED
    state.add_dream(d1)
    state.add_dream(d2)

    cube = EvoCube.__new__(EvoCube)
    cube.enable_depth = False
    cube.stats = {}

    ranked = cube.rank_evolution_queue(state, max_count=10)
    assert len(ranked) == 1
    assert ranked[0].id == "active"


def test_rank_evolution_queue_respects_max_count():
    state = GardenState()
    for i in range(10):
        state.add_dream(_dream(id=f"d{i}", title=f"Dream {i}", strength=0.1))

    cube = EvoCube.__new__(EvoCube)
    cube.enable_depth = False
    cube.stats = {}

    ranked = cube.rank_evolution_queue(state, max_count=3)
    assert len(ranked) == 3
