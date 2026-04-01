"""
MBTA Boston weather risk scoring heuristics.

Scoring model:
  Each hazard contributes a base score (0-10).
  Scores are summed and capped, then mapped to a risk band.

  Score bands:
    0-3  -> low
    4-6  -> moderate
    7-9  -> high
    10+  -> severe

  Peak-period multiplier: if hazard overlaps morning (6:30-9:30) or evening
  (16:00-19:00) commute and score >= 4, bump score +2.

Mode sensitivity weights (applied on top of base score when relevant modes
are queried):
  bus           +2 for snow, ice, freezing rain, flooding, congestion
  ferry         +3 for high wind/marine conditions
  commuter_rail +2 for snow, wind, ice
  subway        +1 for all hazards (most resilient overall)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Hazard base scores
# ---------------------------------------------------------------------------

HAZARD_SCORES: dict[str, int] = {
    "light rain": 1,
    "rain": 2,
    "heavy rain": 4,
    "flooding": 6,
    "coastal flooding": 7,
    "snow": 5,
    "sleet": 6,
    "freezing rain": 7,
    "ice": 6,
    "wind": 3,
    "high wind": 5,
    "gusts": 4,
    "visibility": 3,
    "extreme cold": 3,
    "extreme heat": 2,
    "fog": 3,
}

# Additional score per mode when certain hazards are present
MODE_EXTRA: dict[str, dict[str, int]] = {
    "bus": {
        "snow": 2,
        "ice": 2,
        "freezing rain": 2,
        "sleet": 2,
        "flooding": 2,
        "heavy rain": 1,
    },
    "ferry": {
        "wind": 3,
        "high wind": 3,
        "gusts": 3,
        "visibility": 2,
        "fog": 2,
    },
    "commuter rail": {
        "snow": 2,
        "wind": 2,
        "high wind": 2,
        "ice": 2,
        "freezing rain": 2,
    },
    "subway": {
        # subway is most resilient; small universal bump
        "freezing rain": 1,
        "ice": 1,
        "flooding": 1,
    },
}

PEAK_BONUS = 2


def score_to_band(score: int) -> str:
    if score <= 3:
        return "low"
    if score <= 6:
        return "moderate"
    if score <= 9:
        return "high"
    return "severe"


def compute_risk(
    hazards: list[str],
    modes: list[str],
    is_peak: bool,
) -> tuple[str, float]:
    """Return (risk_level, confidence) for given hazards, modes, and peak flag."""
    base = sum(HAZARD_SCORES.get(h, 0) for h in hazards)

    # Mode-specific extra score: sum the best-matching hazard bonus per mode
    # so that querying multiple sensitive modes (e.g. bus + commuter rail)
    # accumulates severity rather than capping at a single mode's contribution.
    extra = 0
    for mode in modes:
        mode_map = MODE_EXTRA.get(mode, {})
        mode_best = max((mode_map.get(hazard, 0) for hazard in hazards), default=0)
        extra += mode_best

    score = base + extra
    if is_peak and score >= 4:
        score += PEAK_BONUS

    risk = score_to_band(score)

    # Confidence: higher score = more confident, scaled heuristically
    raw_conf = min(0.95, 0.45 + score * 0.05)
    confidence = round(raw_conf, 2)

    return risk, confidence
