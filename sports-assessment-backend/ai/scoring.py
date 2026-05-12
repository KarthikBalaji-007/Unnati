"""
scoring.py
----------
Points calculation, rank progression, and badge awards.
"""

# ─── Points per grade ──────────────────────────────────────────────────────────
GRADE_POINTS = {
    "A": 50,
    "B": 35,
    "C": 20,
    "D": 10,
    "F": 2,
}

# ─── Rank thresholds ───────────────────────────────────────────────────────────
RANK_THRESHOLDS = [
    (600, "Platinum"),
    (300, "Gold"),
    (100, "Silver"),
    (0,   "Bronze"),
]

# ─── Badge definitions ─────────────────────────────────────────────────────────
BADGE_DEFS = {
    "first_test":     {"name": "First Steps",      "icon": "🏁", "desc": "Completed first test",        "condition": lambda stats: stats["tests_completed"] >= 1},
    "five_tests":     {"name": "Getting Serious",   "icon": "🔥", "desc": "Completed 5 tests",           "condition": lambda stats: stats["tests_completed"] >= 5},
    "ten_tests":      {"name": "Dedicated",          "icon": "⭐", "desc": "Completed 10 tests",          "condition": lambda stats: stats["tests_completed"] >= 10},
    "perfect_form":   {"name": "Perfect Form",       "icon": "💎", "desc": "Scored confidence > 0.9",     "condition": lambda stats: stats.get("max_confidence", 0) >= 0.9},
    "grade_a":        {"name": "Top Performer",      "icon": "🏆", "desc": "Earned Grade A",              "condition": lambda stats: stats.get("has_grade_a", False)},
    "all_tests":      {"name": "All-Rounder",        "icon": "🎯", "desc": "Completed all 5 test types",  "condition": lambda stats: stats.get("unique_tests", 0) >= 5},
    "silver_rank":    {"name": "Silver Achiever",     "icon": "🥈", "desc": "Reached Silver rank",         "condition": lambda stats: stats.get("total_points", 0) >= 100},
    "gold_rank":      {"name": "Gold Champion",       "icon": "🥇", "desc": "Reached Gold rank",           "condition": lambda stats: stats.get("total_points", 0) >= 300},
}


def calculate_points(grade: str) -> int:
    """Points awarded for a single test based on grade achieved."""
    return GRADE_POINTS.get(grade, 0)


def compute_rank(total_points: int) -> str:
    """Determine rank level from cumulative points."""
    for threshold, rank in RANK_THRESHOLDS:
        if total_points >= threshold:
            return rank
    return "Bronze"


def compute_rank_progress(total_points: int) -> dict:
    """Return current rank, next rank, and progress percentage."""
    current_rank = compute_rank(total_points)

    # Find next rank threshold
    for i, (threshold, rank) in enumerate(RANK_THRESHOLDS):
        if total_points >= threshold:
            if i == 0:
                # Already at max rank
                return {
                    "current_rank": current_rank,
                    "next_rank": None,
                    "progress_pct": 100,
                    "points_to_next": 0,
                    "current_threshold": threshold,
                }
            next_threshold, next_rank = RANK_THRESHOLDS[i - 1]
            points_in_band = total_points - threshold
            band_size = next_threshold - threshold
            progress = min(100, int((points_in_band / band_size) * 100))
            return {
                "current_rank": current_rank,
                "next_rank": next_rank,
                "progress_pct": progress,
                "points_to_next": next_threshold - total_points,
                "current_threshold": threshold,
            }

    return {"current_rank": "Bronze", "next_rank": "Silver", "progress_pct": 0, "points_to_next": 100, "current_threshold": 0}


def check_badges(stats: dict, existing_badges: list[str]) -> list[str]:
    """
    Check which new badges the athlete has earned.

    Args:
        stats: dict with keys like tests_completed, max_confidence, has_grade_a, etc.
        existing_badges: list of badge IDs already awarded.

    Returns:
        list of newly earned badge IDs.
    """
    new_badges = []
    for badge_id, badge_def in BADGE_DEFS.items():
        if badge_id not in existing_badges:
            try:
                if badge_def["condition"](stats):
                    new_badges.append(badge_id)
            except Exception:
                pass
    return new_badges


def get_badge_info(badge_id: str) -> dict | None:
    """Get display info for a badge."""
    if badge_id in BADGE_DEFS:
        b = BADGE_DEFS[badge_id]
        return {"id": badge_id, "name": b["name"], "icon": b["icon"], "desc": b["desc"]}
    return None


def get_all_badges() -> list[dict]:
    """Get all badge definitions for display."""
    return [{"id": k, "name": v["name"], "icon": v["icon"], "desc": v["desc"]} for k, v in BADGE_DEFS.items()]
