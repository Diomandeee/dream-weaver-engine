"""Quality gate for evolution proposals.

Validates that an evolution proposal stays within safe bounds
before it gets applied to a dream. Tier 1 — structural validation.
"""

MAX_STRENGTH_DELTA = 0.15
MAX_NEW_CONNECTIONS = 5
MIN_INSIGHT_LENGTH = 1  # after stripping whitespace


def validate_evolution(proposal: dict) -> tuple[bool, str]:
    """Validate an evolution proposal before applying it.

    Args:
        proposal: dict with keys like strength_delta, new_connections, insight.

    Returns:
        (True, 'ok') if the proposal passes all checks.
        (False, reason) if any check fails.
    """
    # --- strength_delta ---
    strength_delta = proposal.get("strength_delta", 0)
    if not isinstance(strength_delta, (int, float)):
        return (False, f"strength_delta must be a number, got {type(strength_delta).__name__}")
    if strength_delta > MAX_STRENGTH_DELTA:
        return (False, f"strength_delta {strength_delta} exceeds max {MAX_STRENGTH_DELTA}")
    if strength_delta < 0:
        return (False, f"strength_delta {strength_delta} is negative")

    # --- new_connections ---
    new_connections = proposal.get("new_connections", [])
    if not isinstance(new_connections, list):
        return (False, f"new_connections must be a list, got {type(new_connections).__name__}")
    if len(new_connections) > MAX_NEW_CONNECTIONS:
        return (False, f"new_connections has {len(new_connections)} tags, max is {MAX_NEW_CONNECTIONS}")
    for i, tag in enumerate(new_connections):
        if not isinstance(tag, str) or not tag.strip():
            return (False, f"new_connections[{i}] is not a valid tag")

    # --- insight ---
    insight = proposal.get("insight", "")
    if not isinstance(insight, str) or not insight.strip():
        return (False, "insight is empty")

    return (True, "ok")
