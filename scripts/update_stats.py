#!/usr/bin/env python3
"""
Recalculates goals, assists, and appearances in data/players.csv from:
  - data/baseline_stats.csv  (stats accumulated before event-level tracking started)
  - data/match_events.csv    (every goal/assist logged match by match, growing over the season)

Usage (after you add new rows to match_events.csv for a finished matchday):
    python scripts/update_stats.py

Safe to run as many times as you want - it always recomputes players.csv
from scratch (baseline + all events), so there's no double-counting and no
more manually hunting down a player's row to bump a number by one.
"""
import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BASELINE_PATH = DATA_DIR / "baseline_stats.csv"
EVENTS_PATH = DATA_DIR / "match_events.csv"
PLAYERS_PATH = DATA_DIR / "players.csv"


def load_baseline():
    baseline = {}
    with open(BASELINE_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            baseline[row["id"]] = {
                "goals": int(row["goals"]),
                "assists": int(row["assists"]),
                "appearances": int(row["appearances"]),
            }
    return baseline


def aggregate_events():
    """goals/assists per player, plus appearances = distinct matches the
    player registered at least one event in (so 3 assists in one match
    only counts as 1 appearance, not 3)."""
    goals, assists = {}, {}
    matches_seen = {}  # player_id -> set of (date, home_team, away_team)

    with open(EVENTS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["player_id"]
            match_key = (row["date"], row["home_team"], row["away_team"])
            matches_seen.setdefault(pid, set()).add(match_key)
            if row["event_type"] == "goal":
                goals[pid] = goals.get(pid, 0) + 1
            elif row["event_type"] == "assist":
                assists[pid] = assists.get(pid, 0) + 1

    appearances = {pid: len(matches) for pid, matches in matches_seen.items()}
    return goals, assists, appearances


def main():
    baseline = load_baseline()
    goals, assists, appearances = aggregate_events()

    rows = []
    fieldnames = None
    with open(PLAYERS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            pid = row["id"]
            b = baseline.get(pid, {"goals": 0, "assists": 0, "appearances": 0})
            row["goals"] = str(b["goals"] + goals.get(pid, 0))
            row["assists"] = str(b["assists"] + assists.get(pid, 0))
            row["appearances"] = str(b["appearances"] + appearances.get(pid, 0))
            rows.append(row)

    with open(PLAYERS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {len(rows)} players in {PLAYERS_PATH}")


if __name__ == "__main__":
    main()
