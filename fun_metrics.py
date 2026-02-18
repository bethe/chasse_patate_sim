"""
fun_metrics.py - Analyze 'fun' metrics from Chasse Patate game logs.

Metrics tracked per game:
  - Lead changes: how often the leader (by points) changed hands during the game.
    A transition from a draw to a solo leader (or vice versa) counts as a change.
  - Points gap 1st vs 2nd: score difference between winner and runner-up at game end.
  - Points gap 1st vs last: score difference between winner and last-place at game end.
  - Turns between 1st and 2nd rider finishing (race suspense).
  - Turns between 1st and 5th rider finishing (race suspense, full field).
  - Whether the player who won the first intermediate sprint also won the game.
  - Total turns per game (avg / min / max).
  - % of turns where TeamCar was used (avg / min / max).
  - % of turns where movement == 0, i.e. no field advancement (avg / min / max).
    Note: skipped turns (no valid moves at all) are not logged and not counted.
  - % of turns using a drafting action: Draft, TeamPull, or TeamDraft (avg / min / max).

Usage:
  python fun_metrics.py [log_dir]   # defaults to game_logs/
"""

import json
import glob
import os
import sys
from typing import List, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Track geometry helpers
# ---------------------------------------------------------------------------

def _load_track_info(config_path: str = "config.json") -> Tuple[int, Optional[int]]:
    """
    Return (finish_position, first_sprint_position) based on config.json.
    first_sprint_position is None for single-tile tracks (no intermediate sprint).
    finish_position = num_tiles * 20 - 1  (0-indexed last field).
    """
    try:
        with open(config_path) as f:
            config = json.load(f)
        tiles = config.get("tile_config", [1, 5, 4])
        num_tiles = len(tiles)
        finish_pos = num_tiles * 20 - 1
        first_sprint_pos = 19 if num_tiles >= 2 else None
        return finish_pos, first_sprint_pos
    except Exception:
        # Sensible default: 3 tiles
        return 59, 19


def _infer_track_info(game_log: dict) -> Tuple[int, Optional[int]]:
    """
    Infer track geometry from a game log when config.json is unavailable.
    Uses the maximum new_position seen in any turn as an approximation of finish_pos.
    """
    max_pos = 0
    for turn in game_log.get("move_history", []):
        move = turn.get("move", {})
        max_pos = max(max_pos, move.get("new_position", 0))
        for d in move.get("drafting_riders", []):
            max_pos = max(max_pos, d.get("new_position", 0))
    finish_pos = max_pos
    # Sprint positions: tile boundaries before the finish (every 20 fields)
    num_tiles = (finish_pos + 1) // 20
    first_sprint_pos = 19 if num_tiles >= 2 else None
    return finish_pos, first_sprint_pos


def _player_from_rider_key(rider_key: str, fallback: int = 0) -> int:
    """Extract player_id from a rider key like 'P0R2' → 0."""
    try:
        return int(rider_key[1])
    except (IndexError, ValueError):
        return fallback


# ---------------------------------------------------------------------------
# Per-game metric computation
# ---------------------------------------------------------------------------

def _compute_lead_changes(move_history: List[dict]) -> int:
    """
    Count lead changes by points score throughout the game.

    A lead change is any transition between leader states, where the state is:
      'tie'      — two or more players share the highest score (including all-zero start)
      <player_id> — a single player holds the highest score

    Transitions: tie→solo, solo→tie, solo A→solo B each count as one change.
    """
    current_leader = "tie"  # Initial state: all players at 0 (tie)
    lead_changes = 0

    for turn in move_history:
        scores = turn["state"]["player_scores"]
        max_score = max(scores)
        leaders = [i for i, s in enumerate(scores) if s == max_score]
        new_leader = "tie" if len(leaders) > 1 else leaders[0]

        if new_leader != current_leader:
            lead_changes += 1
            current_leader = new_leader

    return lead_changes


def _compute_finish_order(move_history: List[dict], finish_pos: int) -> List[Tuple[str, int, int]]:
    """
    Determine the order in which riders crossed the finish line.

    Returns a list of (rider_key, player_id, turn_number) sorted by turn_number.
    Only includes riders that actually reached finish_pos during the game.
    """
    finished: Dict[str, Tuple[int, int]] = {}  # rider_key → (player_id, turn_number)

    for turn in move_history:
        turn_num = turn["turn"]
        player_id = turn["player"]
        move = turn["move"]

        # Check the primary rider
        rider_key = move.get("rider")
        new_pos = move.get("new_position", -1)
        if rider_key and rider_key not in finished and new_pos >= finish_pos:
            finished[rider_key] = (player_id, turn_num)

        # Check drafting riders (TeamPull / TeamDraft)
        for drafter in move.get("drafting_riders", []):
            d_key = drafter.get("rider", "")
            d_new = drafter.get("new_position", -1)
            if d_key and d_key not in finished and d_new >= finish_pos:
                d_player = _player_from_rider_key(d_key, fallback=player_id)
                finished[d_key] = (d_player, turn_num)

    return sorted(
        [(key, pid, t) for key, (pid, t) in finished.items()],
        key=lambda x: x[2],
    )


def _compute_first_sprint_winner(
    move_history: List[dict], first_sprint_pos: int
) -> Optional[int]:
    """
    Return the player_id of whoever first crossed first_sprint_pos (the first
    intermediate sprint tile), or None if nobody crossed it during the game.
    """
    for turn in move_history:
        move = turn["move"]
        player_id = turn["player"]
        old_pos = move.get("old_position", -1)
        new_pos = move.get("new_position", -1)

        if old_pos < first_sprint_pos <= new_pos:
            return player_id

        # Drafters can also cross the sprint on the same turn
        for drafter in move.get("drafting_riders", []):
            if drafter.get("old_position", -1) < first_sprint_pos <= drafter.get("new_position", -1):
                return player_id

    return None


def compute_game_metrics(
    game_log: dict,
    finish_pos: int,
    first_sprint_pos: Optional[int],
) -> dict:
    """
    Compute all fun metrics for a single game log dict.

    Args:
        game_log:         Parsed JSON game log.
        finish_pos:       0-indexed track position of the finish line.
        first_sprint_pos: 0-indexed position of the first intermediate sprint,
                          or None for single-tile tracks.

    Returns a dict with all metrics (values may be None when not applicable).
    """
    move_history = game_log["move_history"]
    final_result = game_log["final_result"]
    num_players = game_log["num_players"]

    # --- Lead changes ---
    lead_changes = _compute_lead_changes(move_history)

    # --- Points gaps at game end ---
    final_scores_dict: Dict[str, int] = final_result["final_scores"]
    sorted_scores = sorted(final_scores_dict.values(), reverse=True)
    gap_1st_2nd = (sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) >= 2 else None
    gap_1st_last = sorted_scores[0] - sorted_scores[-1]

    # --- Rider finish order ---
    finish_order = _compute_finish_order(move_history, finish_pos)
    finish_turns = [t for _, _, t in finish_order]

    turns_1st_to_2nd: Optional[int] = None
    turns_1st_to_5th: Optional[int] = None
    if len(finish_turns) >= 2:
        turns_1st_to_2nd = finish_turns[1] - finish_turns[0]
    if len(finish_turns) >= 5:
        turns_1st_to_5th = finish_turns[4] - finish_turns[0]

    # --- Game length and TeamCar usage ---
    total_turns = final_result.get("total_turns") or len(move_history)
    teamcar_count = sum(1 for t in move_history if t["move"].get("action") == "TeamCar")
    teamcar_pct = teamcar_count / total_turns * 100 if total_turns else None

    zero_adv_count = sum(1 for t in move_history if t["move"].get("movement", 0) == 0)
    zero_adv_pct = zero_adv_count / total_turns * 100 if total_turns else None

    _DRAFT_ACTIONS = {"Draft", "TeamPull", "TeamDraft"}
    draft_count = sum(1 for t in move_history if t["move"].get("action") in _DRAFT_ACTIONS)
    draft_pct = draft_count / total_turns * 100 if total_turns else None

    # --- First sprint winner also won the game? ---
    first_sprint_winner_won: Optional[bool] = None
    if first_sprint_pos is not None:
        sprint_winner = _compute_first_sprint_winner(move_history, first_sprint_pos)
        if sprint_winner is not None:
            max_score = max(final_scores_dict.values())
            game_winners = [k for k, v in final_scores_dict.items() if v == max_score]
            if len(game_winners) == 1:
                # "Player 0" → 0
                winner_player_id = int(game_winners[0].split()[-1])
                first_sprint_winner_won = sprint_winner == winner_player_id
            # If game ends in a tie, leave first_sprint_winner_won as None

    return {
        "game_id": game_log.get("game_id", "?"),
        "num_players": num_players,
        "lead_changes": lead_changes,
        "gap_1st_2nd": gap_1st_2nd,
        "gap_1st_last": gap_1st_last,
        "turns_1st_to_2nd_finish": turns_1st_to_2nd,
        "turns_1st_to_5th_finish": turns_1st_to_5th,
        "first_sprint_winner_won": first_sprint_winner_won,
        "total_turns": total_turns,
        "teamcar_pct": teamcar_pct,
        "zero_adv_pct": zero_adv_pct,
        "draft_pct": draft_pct,
        # Contextual info
        "total_rounds": final_result.get("total_rounds"),
        "game_over_reason": final_result.get("game_over_reason", ""),
        "riders_finished": len(finish_order),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _avg(values: list) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _pct_true(bools: list) -> Optional[float]:
    vals = [v for v in bools if v is not None]
    return sum(vals) / len(vals) * 100 if vals else None


def _count_not_none(values: list) -> int:
    return sum(1 for v in values if v is not None)


def aggregate_metrics(metrics_list: List[dict]) -> dict:
    """Aggregate per-game metrics into summary statistics across many games."""
    if not metrics_list:
        return {}

    n = len(metrics_list)

    def field(key):
        return [m[key] for m in metrics_list]

    lead_changes = field("lead_changes")
    gap_12 = field("gap_1st_2nd")
    gap_1last = field("gap_1st_last")
    t12 = field("turns_1st_to_2nd_finish")
    t15 = field("turns_1st_to_5th_finish")
    sprint_won = field("first_sprint_winner_won")
    total_turns = field("total_turns")
    teamcar_pct = field("teamcar_pct")
    zero_adv_pct = field("zero_adv_pct")
    draft_pct = field("draft_pct")

    return {
        "num_games": n,
        # Game length
        "avg_total_turns": _avg(total_turns),
        "min_total_turns": min((v for v in total_turns if v is not None), default=None),
        "max_total_turns": max((v for v in total_turns if v is not None), default=None),
        # TeamCar usage
        "avg_teamcar_pct": _avg(teamcar_pct),
        "min_teamcar_pct": min((v for v in teamcar_pct if v is not None), default=None),
        "max_teamcar_pct": max((v for v in teamcar_pct if v is not None), default=None),
        # Zero-advancement turns
        "avg_zero_adv_pct": _avg(zero_adv_pct),
        "min_zero_adv_pct": min((v for v in zero_adv_pct if v is not None), default=None),
        "max_zero_adv_pct": max((v for v in zero_adv_pct if v is not None), default=None),
        # Draft / TeamPull / TeamDraft turns
        "avg_draft_pct": _avg(draft_pct),
        "min_draft_pct": min((v for v in draft_pct if v is not None), default=None),
        "max_draft_pct": max((v for v in draft_pct if v is not None), default=None),
        # Lead changes
        "avg_lead_changes": _avg(lead_changes),
        "min_lead_changes": min(lead_changes),
        "max_lead_changes": max(lead_changes),
        # Points gaps
        "avg_gap_1st_2nd": _avg(gap_12),
        "min_gap_1st_2nd": min((v for v in gap_12 if v is not None), default=None),
        "max_gap_1st_2nd": max((v for v in gap_12 if v is not None), default=None),
        "avg_gap_1st_last": _avg(gap_1last),
        "min_gap_1st_last": min((v for v in gap_1last if v is not None), default=None),
        "max_gap_1st_last": max((v for v in gap_1last if v is not None), default=None),
        # Finish spread
        "avg_turns_1st_to_2nd_finish": _avg(t12),
        "n_games_2nd_finish": _count_not_none(t12),
        "avg_turns_1st_to_5th_finish": _avg(t15),
        "n_games_5th_finish": _count_not_none(t15),
        # First sprint → game win
        "pct_first_sprint_winner_won": _pct_true(sprint_won),
        "n_games_with_sprint": _count_not_none(sprint_won),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_fun_report(metrics_list: List[dict]) -> None:
    """Print a formatted fun-metrics report to stdout."""
    if not metrics_list:
        print("No metrics to report.")
        return

    agg = aggregate_metrics(metrics_list)
    n = agg["num_games"]

    print()
    print("=" * 62)
    print("  FUN METRICS REPORT")
    print("=" * 62)
    print(f"  Games analyzed: {n}")
    print()

    # Game length
    print("GAME LENGTH (turns)")
    print(f"  Average : {agg['avg_total_turns']:.1f}")
    print(f"  Range   : {agg['min_total_turns']} – {agg['max_total_turns']}")
    print()

    # TeamCar usage
    print("TEAMCAR USAGE (% of turns)")
    print(f"  Average : {agg['avg_teamcar_pct']:.1f}%")
    print(f"  Range   : {agg['min_teamcar_pct']:.1f}% – {agg['max_teamcar_pct']:.1f}%")
    print()

    # Zero-advancement turns
    print("ZERO-ADVANCEMENT TURNS (movement == 0, % of turns)")
    print(f"  Average : {agg['avg_zero_adv_pct']:.1f}%")
    print(f"  Range   : {agg['min_zero_adv_pct']:.1f}% – {agg['max_zero_adv_pct']:.1f}%")
    print(f"  Note: nearly all zero-adv turns are TeamCar; any remainder are truly stuck moves")
    print()

    # Draft family
    print("DRAFT-FAMILY TURNS (Draft + TeamPull + TeamDraft, % of turns)")
    print(f"  Average : {agg['avg_draft_pct']:.1f}%")
    print(f"  Range   : {agg['min_draft_pct']:.1f}% – {agg['max_draft_pct']:.1f}%")
    print()

    # Lead changes
    print("LEAD CHANGES (by points)")
    print(f"  Average : {agg['avg_lead_changes']:.1f}")
    print(f"  Range   : {agg['min_lead_changes']} – {agg['max_lead_changes']}")
    print()

    # Points gaps
    print("POINTS GAP AT END OF GAME")
    if agg["avg_gap_1st_2nd"] is not None:
        print(f"  1st vs 2nd  : avg {agg['avg_gap_1st_2nd']:.1f} pts"
              f"  (range {agg['min_gap_1st_2nd']}–{agg['max_gap_1st_2nd']})")
    if agg["avg_gap_1st_last"] is not None:
        print(f"  1st vs last : avg {agg['avg_gap_1st_last']:.1f} pts"
              f"  (range {agg['min_gap_1st_last']}–{agg['max_gap_1st_last']})")
    print()

    # Finish spread
    print("RIDER FINISH SPREAD (turns between finishers)")
    n2 = agg["n_games_2nd_finish"]
    if agg["avg_turns_1st_to_2nd_finish"] is not None:
        print(f"  1st → 2nd rider : avg {agg['avg_turns_1st_to_2nd_finish']:.1f} turns"
              f"  ({n2}/{n} games)")
    else:
        print(f"  1st → 2nd rider : N/A")
    n5 = agg["n_games_5th_finish"]
    if agg["avg_turns_1st_to_5th_finish"] is not None:
        print(f"  1st → 5th rider : avg {agg['avg_turns_1st_to_5th_finish']:.1f} turns"
              f"  ({n5}/{n} games)")
    else:
        print(f"  1st → 5th rider : N/A  (fewer than 5 riders finished in most games)")
    print()

    # First sprint → game win
    print("FIRST SPRINT → GAME WIN CORRELATION")
    ns = agg["n_games_with_sprint"]
    if agg["pct_first_sprint_winner_won"] is not None:
        print(f"  First sprint winner also won game: {agg['pct_first_sprint_winner_won']:.1f}%"
              f"  ({ns}/{n} games with an intermediate sprint)")
    else:
        print("  N/A  (no intermediate sprints in these games)")
    print()

    print("=" * 62)

    # Per-game breakdown if few games
    if n <= 20:
        print()
        print("PER-GAME BREAKDOWN")
        header = (f"{'Game':>5}  {'Players':>7}  {'Turns':>5}  {'TC%':>5}  "
                  f"{'0Adv%':>5}  {'Dft%':>5}  "
                  f"{'Leads':>5}  {'Gap12':>5}  {'Gap1L':>5}  "
                  f"{'T→2nd':>5}  {'T→5th':>5}  {'Sprint→Win':>10}")
        print(header)
        print("-" * len(header))
        for m in metrics_list:
            sprint_str = ("yes" if m["first_sprint_winner_won"] is True
                          else "no" if m["first_sprint_winner_won"] is False
                          else "N/A")
            t2 = str(m["turns_1st_to_2nd_finish"]) if m["turns_1st_to_2nd_finish"] is not None else "N/A"
            t5 = str(m["turns_1st_to_5th_finish"]) if m["turns_1st_to_5th_finish"] is not None else "N/A"
            g12 = str(m["gap_1st_2nd"]) if m["gap_1st_2nd"] is not None else "N/A"
            tc = f"{m['teamcar_pct']:.1f}" if m["teamcar_pct"] is not None else "N/A"
            za = f"{m['zero_adv_pct']:.1f}" if m["zero_adv_pct"] is not None else "N/A"
            dp = f"{m['draft_pct']:.1f}" if m["draft_pct"] is not None else "N/A"
            print(f"{m['game_id']:>5}  {m['num_players']:>7}  {m['total_turns']:>5}  {tc:>5}  "
                  f"{za:>5}  {dp:>5}  "
                  f"{m['lead_changes']:>5}  {g12:>5}  {m['gap_1st_last']:>5}  "
                  f"{t2:>5}  {t5:>5}  {sprint_str:>10}")
        print()


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_game_logs(log_dir: str = "game_logs") -> List[dict]:
    """Load all game_*.json files from log_dir, sorted by game id."""
    logs = []
    pattern = os.path.join(log_dir, "game_*.json")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path) as f:
                logs.append(json.load(f))
        except Exception as e:
            print(f"Warning: could not load {path}: {e}", file=sys.stderr)
    return logs


def analyze_logs(
    path: str = "game_logs",
    config_path: str = "config.json",
) -> List[dict]:
    """
    Load game logs and compute fun metrics for each.

    path can be:
      - a directory  → loads all game_*.json files inside it
      - a .json file → loads just that one file
    """
    finish_pos, first_sprint_pos = _load_track_info(config_path)

    if os.path.isfile(path):
        try:
            with open(path) as f:
                logs = [json.load(f)]
        except Exception as e:
            print(f"Error: could not load '{path}': {e}", file=sys.stderr)
            return []
    else:
        logs = load_game_logs(path)

    if not logs:
        print(f"No game logs found at '{path}'", file=sys.stderr)
        return []

    metrics_list = []
    for log in logs:
        try:
            m = compute_game_metrics(log, finish_pos, first_sprint_pos)
            metrics_list.append(m)
        except Exception as e:
            print(
                f"Warning: could not compute metrics for game "
                f"{log.get('game_id', '?')}: {e}",
                file=sys.stderr,
            )

    return metrics_list


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "game_logs"
    config_path = sys.argv[2] if len(sys.argv) > 2 else "config.json"

    metrics = analyze_logs(path, config_path)
    if metrics:
        print_fun_report(metrics)
