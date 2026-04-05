import argparse
import csv
from collections import defaultdict


def analyze(csv_path):
    first_time = None
    last_time = 0.0
    agents = set()
    by_agent_last_seen = defaultdict(float)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = float(row.get("t", 0))
            aid = row.get("agent_id", "")
            agents.add(aid)
            if first_time is None:
                first_time = t
            last_time = max(last_time, t)
            by_agent_last_seen[aid] = max(by_agent_last_seen[aid], t)

    total_evacuation_time = (last_time - first_time) if first_time is not None else 0.0
    avg_completion_time = sum(by_agent_last_seen.values()) / max(len(agents), 1)
    return {
        "agents": len(agents),
        "total_evacuation_time": total_evacuation_time,
        "avg_completion_time": avg_completion_time,
    }


def main():
    p = argparse.ArgumentParser(description="Evacuation analysis from trajectory CSV")
    p.add_argument("csv", help="CSV with columns: t, agent_id, x, y (others optional)")
    args = p.parse_args()
    metrics = analyze(args.csv)
    for k, v in metrics.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
