import asyncio
import glob
import json
import os
import re
import statistics
import sys
from collections import defaultdict

from rich.console import Console
from rich.table import Table

from orchestrator import play

console = Console()

IN_RATE = 0.25 / 1_000_000
OUT_RATE = 1.50 / 1_000_000
OUTPUT_FRACTION = 0.10
COST_PER_TOKEN = (1 - OUTPUT_FRACTION) * IN_RATE + OUTPUT_FRACTION * OUT_RATE


def run_batch(scenario, n):
    for i in range(n):
        console.rule(f"Game {i + 1} of {n}")
        asyncio.run(play(scenario))


def load_traces():
    traces = []
    for path in sorted(glob.glob(os.path.join("logs", "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                traces.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return traces


def game_metrics(trace):
    events = trace["events"]
    meta = trace["meta"]
    strikes = cleared = 0
    modules = 1
    latencies = []
    for e in events:
        latencies.append(e.get("seconds", 0.0))
        for a in e["actions"]:
            result = a["result"]
            if result.startswith("Wrong"):
                strikes += 1
            if result.startswith("Correct"):
                cleared += 1
            found = re.search(r"Module \d+ of (\d+)", result)
            if found:
                modules = max(modules, int(found.group(1)))
    tokens = meta.get("total_tokens", 0)
    return {
        "won": meta.get("result") == "won",
        "timeout": meta.get("result") == "timeout",
        "modules": modules,
        "module_pct": 100.0 * cleared / modules,
        "turns": meta.get("turns", len(events)),
        "strikes": strikes,
        "latency": statistics.median(latencies) if latencies else 0.0,
        "tokens": tokens,
        "cost": tokens * COST_PER_TOKEN,
    }


def average(rows, key):
    return sum(r[key] for r in rows) / len(rows)


def rate(rows, key):
    return 100 * sum(1 for r in rows if r[key]) / len(rows)


def report():
    traces = load_traces()
    if not traces:
        console.print("No logs found. Run some games first.")
        return
    groups = defaultdict(list)
    for trace in traces:
        meta = trace["meta"]
        key = (meta.get("model", "?"), os.path.basename(meta.get("scenario", "?")))
        groups[key].append(game_metrics(trace))

    table = Table(title="Escape Room - Agent Metrics")
    for col in ["model", "scenario", "mods", "games", "win%", "mod%", "timeout%", "turns", "strikes", "lat(s)", "tokens", "cost$"]:
        table.add_column(col)

    rows = sorted((g[0]["modules"], scenario, model, g) for (model, scenario), g in groups.items())
    for mods, scenario, model, g in rows:
        table.add_row(
            model, scenario, str(mods), str(len(g)),
            f"{rate(g, 'won'):.0f}",
            f"{average(g, 'module_pct'):.0f}",
            f"{rate(g, 'timeout'):.0f}",
            f"{average(g, 'turns'):.1f}",
            f"{average(g, 'strikes'):.1f}",
            f"{average(g, 'latency'):.2f}",
            f"{average(g, 'tokens'):.0f}",
            f"${average(g, 'cost'):.4f}",
        )
    console.print(table)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        scenario = sys.argv[2] if len(sys.argv) > 2 else "scenarios/tutorial.json"
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        run_batch(scenario, n)
    report()