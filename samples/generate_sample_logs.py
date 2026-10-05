"""Synthetic log generator script to produce large-scale log files for benchmarking."""

import random
from datetime import datetime, timedelta
from pathlib import Path
import argparse


LOG_LEVELS = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]
LEVEL_WEIGHTS = [0.65, 0.15, 0.10, 0.08, 0.02]

COMPONENTS = ["auth", "db_pool", "payment_gw", "cache", "api_gateway", "worker_node"]

MESSAGES = {
    "INFO": [
        "User logged in successfully: user_id={user_id}",
        "GET /api/v1/resource - 200 OK (latency={latency}ms)",
        "Background job completed: job_id={uuid}",
        "Cache warmed up for namespace '{comp}'",
    ],
    "DEBUG": [
        "SQL query executed: SELECT * FROM items WHERE id={user_id}",
        "Redis ping response time: {latency}ms",
        "Payload deserialized: size={latency}KB",
    ],
    "WARNING": [
        "Database pool utilization high: {latency}%",
        "Slow query detected: {latency}ms execution time",
        "High memory threshold warning on node worker-{user_id}",
    ],
    "ERROR": [
        "Connection refused: host=db-replica-{user_id}:5432",
        "Read timed out while contacting payment gateway after {latency}ms",
        "Unauthorized: 401 Invalid JWT token signature for request from 192.168.1.{user_id}",
        "Unhandled AttributeError: 'NoneType' object has no attribute 'process'",
    ],
    "CRITICAL": [
        "Out of memory: Heap space exhausted on worker-{user_id}",
        "Database cluster failover initiated for primary node",
    ],
}


def generate_logs(output_file: str, line_count: int = 10000) -> None:
    """Generate synthetic log file with realistic distribution and timestamps."""
    start_time = datetime(2026, 9, 30, 8, 0, 0)
    current_time = start_time
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {line_count:,} log lines into {output_file}...")
    with open(path, "w", encoding="utf-8") as f:
        for i in range(line_count):
            current_time += timedelta(milliseconds=random.randint(50, 800))
            ts_str = current_time.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]

            # Inoculate occasional malformed line every ~200 lines
            if i > 0 and i % 250 == 0:
                f.write(f"MALFORMED_LOG_ENTRY_CORRUPT_PACKET_AT_INDEX_{i}\n")
                continue

            level = random.choices(LOG_LEVELS, weights=LEVEL_WEIGHTS)[0]
            comp = random.choice(COMPONENTS)
            template = random.choice(MESSAGES[level])
            msg = template.format(
                user_id=random.randint(1000, 9999),
                latency=random.randint(5, 5000),
                uuid=f"job-{random.randint(100, 999)}",
                comp=comp,
            )

            f.write(f"{ts_str} - {level} - [{comp}] - {msg}\n")

    print(f"Generated {line_count:,} lines successfully. File size: {path.stat().st_size / (1024*1024):.2f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic application log files.")
    parser.add_argument("--output", "-o", default="samples/large_sample.log", help="Output file path")
    parser.add_argument("--lines", "-n", type=int, default=10000, help="Number of lines to generate")
    args = parser.parse_args()
    generate_logs(args.output, args.lines)
