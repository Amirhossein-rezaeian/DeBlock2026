import os
import sqlite3
import statistics
import time

from verify_blockchain import DB_FILE, verify_database


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def main():
    run_count = 20
    elapsed_times = []

    with sqlite3.connect(DB_FILE, timeout=10) as db:
        db.execute("PRAGMA busy_timeout = 10000")

        for run_number in range(1, run_count + 1):
            started = time.perf_counter()
            result = verify_database(db)
            elapsed = (time.perf_counter() - started) * 1000
            elapsed_times.append(elapsed)
            print(f"Run {run_number:02d}: {elapsed:.3f} ms")

    mean_time = statistics.mean(elapsed_times)
    median_time = statistics.median(elapsed_times)
    standard_deviation = statistics.stdev(elapsed_times)
    minimum_time = min(elapsed_times)
    maximum_time = max(elapsed_times)
    p95 = percentile(elapsed_times, 0.95)
    database_size = os.path.getsize(DB_FILE) / 1024

    print()
    print("Verification Performance")
    print("=" * 36)
    print("Source records:", result["source_records"])
    print("Total blocks:", result["total_blocks"])
    print("Anchored records:", result["anchored_records"])
    print("Pending records:", result["pending_records"])
    print("Integrity:", result["integrity"])
    print("Coverage:", result["coverage"])
    print(f"Mean: {mean_time:.3f} ms")
    print(f"Median: {median_time:.3f} ms")
    print(f"Sample SD: {standard_deviation:.3f} ms")
    print(f"Minimum: {minimum_time:.3f} ms")
    print(f"Maximum: {maximum_time:.3f} ms")
    print(f"Empirical p95: {p95:.3f} ms")
    print(f"Database size: {database_size:.1f} KB")


if __name__ == "__main__":
    main()
