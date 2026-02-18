"""Tests for dream_engine.quality_gate."""

from dream_engine.quality_gate import validate_evolution


# --- passing proposals ---

def test_valid_proposal():
    proposal = {
        "strength_delta": 0.10,
        "new_connections": ["a", "b"],
        "insight": "Dream deepened its exploration of haptic patterns.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is True
    assert msg == "ok"


def test_boundary_strength_delta():
    """Exactly 0.15 should pass (reject is strictly greater)."""
    proposal = {
        "strength_delta": 0.15,
        "new_connections": [],
        "insight": "Some insight.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is True


def test_boundary_five_connections():
    """Exactly 5 connections should pass."""
    proposal = {
        "strength_delta": 0.05,
        "new_connections": ["a", "b", "c", "d", "e"],
        "insight": "Insight text.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is True


def test_zero_strength_delta():
    proposal = {
        "strength_delta": 0.0,
        "new_connections": [],
        "insight": "No change.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is True


def test_minimal_valid_proposal():
    """A proposal with only insight should pass (defaults kick in)."""
    proposal = {"insight": "Just an insight."}
    ok, msg = validate_evolution(proposal)
    assert ok is True


# --- rejections: strength_delta ---

def test_reject_high_strength_delta():
    proposal = {
        "strength_delta": 0.20,
        "new_connections": [],
        "insight": "Massive jump.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "strength_delta" in msg


def test_reject_negative_strength_delta():
    proposal = {
        "strength_delta": -0.05,
        "new_connections": [],
        "insight": "Shrink.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "negative" in msg


def test_reject_non_numeric_strength_delta():
    proposal = {
        "strength_delta": "high",
        "new_connections": [],
        "insight": "Bad type.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "number" in msg


# --- rejections: new_connections ---

def test_reject_too_many_connections():
    proposal = {
        "strength_delta": 0.05,
        "new_connections": ["a", "b", "c", "d", "e", "f"],
        "insight": "Tags explosion.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "new_connections" in msg


def test_reject_non_list_connections():
    proposal = {
        "strength_delta": 0.05,
        "new_connections": "not-a-list",
        "insight": "Bad type.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "new_connections" in msg


def test_reject_non_string_tag():
    proposal = {
        "strength_delta": 0.05,
        "new_connections": ["valid", 42],
        "insight": "One bad tag.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "new_connections[1]" in msg


def test_reject_empty_string_tag():
    proposal = {
        "strength_delta": 0.05,
        "new_connections": ["valid", "   "],
        "insight": "Whitespace tag.",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "new_connections[1]" in msg


# --- rejections: insight ---

def test_reject_empty_insight():
    proposal = {
        "strength_delta": 0.05,
        "new_connections": [],
        "insight": "",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "insight" in msg


def test_reject_whitespace_only_insight():
    proposal = {
        "strength_delta": 0.05,
        "new_connections": [],
        "insight": "   \n\t  ",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "insight" in msg


def test_reject_missing_insight():
    """If insight key is absent, treat as empty."""
    proposal = {
        "strength_delta": 0.05,
        "new_connections": [],
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "insight" in msg


def test_reject_non_string_insight():
    proposal = {
        "strength_delta": 0.05,
        "new_connections": [],
        "insight": 42,
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "insight" in msg


# --- first failure wins ---

def test_first_failure_is_strength():
    """When multiple things are wrong, strength_delta check runs first."""
    proposal = {
        "strength_delta": 0.50,
        "new_connections": ["a"] * 10,
        "insight": "",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "strength_delta" in msg


def test_first_failure_connections_before_insight():
    """new_connections check runs before insight check."""
    proposal = {
        "strength_delta": 0.05,
        "new_connections": "bad-type",
        "insight": "",
    }
    ok, msg = validate_evolution(proposal)
    assert ok is False
    assert "new_connections" in msg
