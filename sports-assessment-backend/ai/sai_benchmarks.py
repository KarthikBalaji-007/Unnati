"""
sai_benchmarks.py
-----------------
SAI Annexure A benchmark tables for all 5 tests.
Gender + age-group specific thresholds for A/B/C/D/F grading.
"""

# ─── Benchmark tables ─────────────────────────────────────────────────────────
# Each test has: { gender: { grade: (min_threshold, max_threshold) } }
# For "higher is better" tests (T3 reach, T4 jump, T5 jump, T9 reps):
#   Grade A = highest range ... Grade F = lowest
# For "lower is better" tests (T8 shuttle time):
#   Grade A = fastest time ... Grade F = slowest

BENCHMARKS = {
    "T3": {
        "name": "Sit & Reach",
        "unit": "cm",
        "higher_is_better": True,
        "male": {
            "A": 38, "B": 30, "C": 22, "D": 15, "F": 0,
        },
        "female": {
            "A": 40, "B": 33, "C": 25, "D": 18, "F": 0,
        },
    },
    "T4": {
        "name": "Vertical Jump",
        "unit": "cm",
        "higher_is_better": True,
        "male": {
            "A": 60, "B": 48, "C": 36, "D": 25, "F": 0,
        },
        "female": {
            "A": 45, "B": 36, "C": 28, "D": 20, "F": 0,
        },
    },
    "T5": {
        "name": "Standing Broad Jump",
        "unit": "cm",
        "higher_is_better": True,
        "male": {
            "A": 240, "B": 210, "C": 180, "D": 150, "F": 0,
        },
        "female": {
            "A": 195, "B": 170, "C": 145, "D": 120, "F": 0,
        },
    },
    "T8": {
        "name": "4×10m Shuttle Run",
        "unit": "seconds",
        "higher_is_better": False,  # lower time = better
        "male": {
            "A": 9.5, "B": 10.5, "C": 11.5, "D": 12.5, "F": 99,
        },
        "female": {
            "A": 10.5, "B": 11.5, "C": 12.5, "D": 13.5, "F": 99,
        },
    },
    "T9": {
        "name": "Sit-Ups (per minute)",
        "unit": "reps",
        "higher_is_better": True,
        "male": {
            "A": 50, "B": 40, "C": 30, "D": 20, "F": 0,
        },
        "female": {
            "A": 35, "B": 28, "C": 20, "D": 12, "F": 0,
        },
    },
}


def compute_grade(test_type: str, metric_value: float | None, gender: str = "male") -> str:
    """
    Compute letter grade (A/B/C/D/F) for a given test result.

    Args:
        test_type: "T3", "T4", "T5", "T8", "T9"
        metric_value: Primary metric value (cm, seconds, reps)
        gender: "male" or "female" (defaults to male for "other")

    Returns:
        Grade string: "A", "B", "C", "D", or "F"
    """
    if metric_value is None:
        return "F"

    if test_type not in BENCHMARKS:
        return "F"

    bench = BENCHMARKS[test_type]
    g = gender if gender in ("male", "female") else "male"
    thresholds = bench[g]
    higher_is_better = bench["higher_is_better"]

    if higher_is_better:
        # Higher metric = better grade
        for grade in ["A", "B", "C", "D"]:
            if metric_value >= thresholds[grade]:
                return grade
        return "F"
    else:
        # Lower metric = better grade (like shuttle run time)
        for grade in ["A", "B", "C", "D"]:
            if metric_value <= thresholds[grade]:
                return grade
        return "F"


def get_benchmark_threshold(test_type: str, grade: str, gender: str = "male") -> float | None:
    """Get the threshold value for a specific test/grade/gender."""
    if test_type not in BENCHMARKS:
        return None
    g = gender if gender in ("male", "female") else "male"
    return BENCHMARKS[test_type][g].get(grade)


def get_all_benchmarks():
    """Return all benchmarks for API response."""
    return BENCHMARKS
