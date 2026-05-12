"""Quick test to check what error the process endpoint throws."""
import traceback
try:
    # Test imports
    print("Importing models...")
    from models import Athlete, TestSession, TestResult
    print("Models OK")

    print("Importing schemas...")
    from schemas import ProcessRequest, ProcessResponse, MetricResult
    print("Schemas OK")

    print("Importing benchmarks...")
    from ai.sai_benchmarks import compute_grade, get_all_benchmarks
    print("Benchmarks OK:", list(get_all_benchmarks().keys()))

    print("Importing scoring...")
    from ai.scoring import calculate_points, compute_rank, check_badges
    print("Scoring OK")

    print("Importing athletes router...")
    from routers.athletes import router as athletes_router
    print("Athletes router OK")

    print("Importing process router...")
    from routers.process import router as process_router
    print("Process router OK")

    print("Importing main app...")
    from main import app
    print("Main app OK")

    print("\n=== ALL IMPORTS SUCCESSFUL ===")

except Exception as e:
    print(f"\n=== ERROR ===")
    traceback.print_exc()
