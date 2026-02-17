#!/usr/bin/env python3
"""
Comprehensive analysis of all game logs in game_logs/ directory.
Analyzes strategic patterns, win rates, and behaviors across all games.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple
import statistics

@dataclass
class GameStats:
    """Statistics for a single game."""
    game_id: int
    winner: str
    winner_id: int
    num_players: int
    agents: List[str]
    rounds: int
    end_reason: str
    final_scores: Dict[int, int]

@dataclass
class PlayerGameStats:
    """Detailed stats for a player in a game."""
    agent: str
    player_id: int
    game_id: int
    won: bool
    final_score: int

    # Action usage
    pulls: int
    attacks: int
    drafts: int
    team_pulls: int
    team_drafts: int
    team_cars: int

    # Movement stats
    total_fields: int
    total_cards_used: int
    cards_per_field: float

    # Hand management
    avg_hand_size: float
    min_hand_size: int
    max_hand_size: int
    team_car_round_avg: float  # Average round when TeamCar used

    # Scoring
    sprint_points: int
    finish_points: int

    # Game progression
    rounds_to_finish: int  # Rounds until first rider finished (or total if didn't finish)
    early_game_fields: int  # Fields in first 1/3 of game
    mid_game_fields: int    # Fields in middle 1/3
    late_game_fields: int   # Fields in last 1/3


def load_game_log(filepath: str) -> dict:
    """Load a game log JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def analyze_player_in_game(game_data: dict, player_id: int, game_id: int) -> PlayerGameStats:
    """Extract detailed statistics for a player in a game."""

    # Get player info from agents list
    agent = game_data['agents'][player_id]['type']

    # Get final score from final_result
    final_result = game_data['final_result']
    final_score = final_result['final_scores'][f'Player {player_id}']

    # Determine if won
    winner_str = final_result['winner']
    winner_id = int(winner_str.split('Player ')[1].rstrip(')'))
    won = player_id == winner_id

    # Initialize counters
    action_counts = defaultdict(int)
    total_fields = 0
    total_cards_used = 0
    hand_sizes = []
    team_car_rounds = []

    sprint_points = 0
    finish_points = 0

    total_rounds = final_result['total_rounds']
    rounds_to_finish = total_rounds  # Default to total
    first_finish_found = False

    early_cutoff = total_rounds // 3
    mid_cutoff = 2 * total_rounds // 3

    early_fields = 0
    mid_fields = 0
    late_fields = 0

    # Process move history
    for move_entry in game_data['move_history']:
        if move_entry['player'] != player_id:
            continue

        round_num = move_entry['round']
        move = move_entry['move']
        state = move_entry['state']

        action = move['action']
        action_counts[action] += 1

        # Track hand size from state
        hand_size = state['player_hand_sizes'][player_id]
        hand_sizes.append(hand_size)

        # Count cards used
        cards_used = move.get('num_cards', 0)
        total_cards_used += cards_used

        # Track TeamCar usage
        if action == 'TeamCar':
            team_car_rounds.append(round_num)

        # Count fields moved
        fields_moved = move.get('movement', 0)
        total_fields += fields_moved

        # For TeamPull and TeamDraft, add drafting riders' movement
        if action == 'TeamPull' or action == 'TeamDraft':
            if 'drafting_riders' in move and move['drafting_riders']:
                for drafting in move['drafting_riders']:
                    drafting_movement = drafting['new_position'] - drafting['old_position']
                    total_fields += drafting_movement

        # Track fields by game phase
        if round_num <= early_cutoff:
            early_fields += fields_moved
            if action in ['TeamPull', 'TeamDraft'] and 'drafting_riders' in move and move['drafting_riders']:
                for drafting in move['drafting_riders']:
                    early_fields += drafting['new_position'] - drafting['old_position']
        elif round_num <= mid_cutoff:
            mid_fields += fields_moved
            if action in ['TeamPull', 'TeamDraft'] and 'drafting_riders' in move and move['drafting_riders']:
                for drafting in move['drafting_riders']:
                    mid_fields += drafting['new_position'] - drafting['old_position']
        else:
            late_fields += fields_moved
            if action in ['TeamPull', 'TeamDraft'] and 'drafting_riders' in move and move['drafting_riders']:
                for drafting in move['drafting_riders']:
                    late_fields += drafting['new_position'] - drafting['old_position']

        # Track scoring
        points_earned = move.get('points_earned', 0)
        # We need to distinguish sprint vs finish points
        # If rider reached finish (position >= finish_line), it's finish points
        # Otherwise it's sprint points
        # For now, we'll check the new_position
        new_pos = move.get('new_position')
        if new_pos is not None:
            # Assume finish line is around 100 (we can adjust)
            # Actually, let's just count all points as combined for now
            # We'll need to check the move more carefully
            pass

        # Check if this is first finish
        # Look for riders finishing
        if not first_finish_found:
            # Check state for riders at finish
            # Actually, just track when we see finish related events
            # For simplicity, we'll use total_rounds
            pass

    # Process scoring from move history more carefully
    for move_entry in game_data['move_history']:
        if move_entry['player'] != player_id:
            continue

        move = move_entry['move']
        points = move.get('points_earned', 0)

        # Check if it's a finish or sprint
        # Sprint points are typically 3/2/1, finish points are 15/12/9/6/3
        if points > 0:
            if points >= 15 or points == 12 or points == 9 or points == 6:
                finish_points += points
            else:
                sprint_points += points

    # Calculate averages
    avg_hand_size = statistics.mean(hand_sizes) if hand_sizes else 0
    min_hand_size = min(hand_sizes) if hand_sizes else 0
    max_hand_size = max(hand_sizes) if hand_sizes else 0
    team_car_round_avg = statistics.mean(team_car_rounds) if team_car_rounds else 0

    cards_per_field = total_cards_used / total_fields if total_fields > 0 else 0

    return PlayerGameStats(
        agent=agent,
        player_id=player_id,
        game_id=game_id,
        won=won,
        final_score=final_score,
        pulls=action_counts.get('Pull', 0),
        attacks=action_counts.get('Attack', 0),
        drafts=action_counts.get('Draft', 0),
        team_pulls=action_counts.get('TeamPull', 0),
        team_drafts=action_counts.get('TeamDraft', 0),
        team_cars=action_counts.get('TeamCar', 0),
        total_fields=total_fields,
        total_cards_used=total_cards_used,
        cards_per_field=cards_per_field,
        avg_hand_size=avg_hand_size,
        min_hand_size=min_hand_size,
        max_hand_size=max_hand_size,
        team_car_round_avg=team_car_round_avg,
        sprint_points=sprint_points,
        finish_points=finish_points,
        rounds_to_finish=rounds_to_finish,
        early_game_fields=early_fields,
        mid_game_fields=mid_fields,
        late_game_fields=late_fields,
    )


def analyze_all_games(logs_dir: str) -> Tuple[List[GameStats], List[PlayerGameStats]]:
    """Analyze all game logs in the directory."""

    game_stats = []
    player_stats = []

    # Find all game_*.json files
    game_files = sorted(
        [f for f in os.listdir(logs_dir) if f.startswith('game_') and f.endswith('.json') and not f.startswith('play_')],
        key=lambda x: int(x.split('_')[1].split('.')[0])
    )

    for filename in game_files:
        filepath = os.path.join(logs_dir, filename)
        game_id = int(filename.split('_')[1].split('.')[0])

        try:
            game_data = load_game_log(filepath)

            # Extract game-level stats
            num_players = game_data['num_players']

            # Build agents list
            agents = [agent_info['type'] for agent_info in game_data['agents']]

            # Extract winner info from final_result
            final_result = game_data['final_result']
            winner_str = final_result['winner']  # Format: "AgentName (Player N)"
            winner_agent = winner_str.split(' (')[0]
            winner_id = int(winner_str.split('Player ')[1].rstrip(')'))

            rounds = final_result['total_rounds']
            end_reason = final_result['game_over_reason']

            # Extract final scores
            final_scores = {}
            for key, score in final_result['final_scores'].items():
                player_num = int(key.split(' ')[1])
                final_scores[player_num] = score

            game_stats.append(GameStats(
                game_id=game_id,
                winner=winner_agent,
                winner_id=winner_id,
                num_players=num_players,
                agents=agents,
                rounds=rounds,
                end_reason=end_reason,
                final_scores=final_scores,
            ))

            # Extract player-level stats
            for player_id in range(num_players):
                player_stats.append(analyze_player_in_game(game_data, player_id, game_id))

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            import traceback
            traceback.print_exc()

    return game_stats, player_stats


def calculate_agent_win_rates(game_stats: List[GameStats]) -> Dict[str, Tuple[int, int, float]]:
    """Calculate win rates for each agent. Returns (wins, games, win_rate)."""

    agent_games = defaultdict(int)
    agent_wins = defaultdict(int)

    for game in game_stats:
        for agent in game.agents:
            agent_games[agent] += 1
        agent_wins[game.winner] += 1

    win_rates = {}
    for agent in agent_games:
        wins = agent_wins[agent]
        games = agent_games[agent]
        win_rate = wins / games if games > 0 else 0
        win_rates[agent] = (wins, games, win_rate)

    return win_rates


def compare_winners_vs_losers(player_stats: List[PlayerGameStats]) -> Dict[str, Tuple[float, float]]:
    """Compare winners vs losers across all metrics. Returns (winner_avg, loser_avg) for each metric."""

    winners = [p for p in player_stats if p.won]
    losers = [p for p in player_stats if not p.won]

    def avg(players, attr):
        values = [getattr(p, attr) for p in players]
        return statistics.mean(values) if values else 0

    metrics = {}
    attrs = [
        'pulls', 'attacks', 'drafts', 'team_pulls', 'team_drafts', 'team_cars',
        'total_fields', 'total_cards_used', 'cards_per_field',
        'avg_hand_size', 'min_hand_size', 'max_hand_size', 'team_car_round_avg',
        'sprint_points', 'finish_points', 'rounds_to_finish',
        'early_game_fields', 'mid_game_fields', 'late_game_fields'
    ]

    for attr in attrs:
        metrics[attr] = (avg(winners, attr), avg(losers, attr))

    return metrics


def generate_report(game_stats: List[GameStats], player_stats: List[PlayerGameStats]) -> str:
    """Generate comprehensive markdown report."""

    win_rates = calculate_agent_win_rates(game_stats)
    metrics = compare_winners_vs_losers(player_stats)

    report = []
    report.append("# FULL DATASET ANALYSIS")
    report.append("")
    report.append("Comprehensive analysis of all game logs in the game_logs/ directory.")
    report.append("")

    # Dataset overview
    report.append("## 1. Dataset Overview")
    report.append("")
    report.append(f"- **Total games analyzed**: {len(game_stats)}")
    report.append(f"- **Total player-game instances**: {len(player_stats)}")

    # Player count distribution
    player_counts = defaultdict(int)
    for game in game_stats:
        player_counts[game.num_players] += 1
    report.append(f"- **Games by player count**:")
    for count in sorted(player_counts.keys()):
        report.append(f"  - {count} players: {player_counts[count]} games")

    # Unique agents
    unique_agents = set()
    for game in game_stats:
        unique_agents.update(game.agents)
    report.append(f"- **Unique agents**: {len(unique_agents)}")
    report.append("")

    # Agent win rates
    report.append("## 2. Agent Win Rates")
    report.append("")
    report.append("| Agent | Wins | Games | Win Rate |")
    report.append("|-------|------|-------|----------|")

    sorted_agents = sorted(win_rates.items(), key=lambda x: x[1][2], reverse=True)
    for agent, (wins, games, rate) in sorted_agents:
        report.append(f"| {agent} | {wins} | {games} | {rate:.1%} |")
    report.append("")

    # Winners vs Losers comparison
    report.append("## 3. Winners vs Losers: Strategic Patterns")
    report.append("")

    report.append("### 3.1 Action Usage")
    report.append("")
    report.append("| Action | Winners (avg) | Losers (avg) | Difference |")
    report.append("|--------|---------------|--------------|------------|")

    action_attrs = ['pulls', 'attacks', 'drafts', 'team_pulls', 'team_drafts', 'team_cars']
    for attr in action_attrs:
        winner_avg, loser_avg = metrics[attr]
        diff = winner_avg - loser_avg
        sign = "+" if diff > 0 else ""
        report.append(f"| {attr.replace('_', ' ').title()} | {winner_avg:.2f} | {loser_avg:.2f} | {sign}{diff:.2f} |")
    report.append("")

    # Total actions
    winner_total_actions = sum(metrics[attr][0] for attr in action_attrs)
    loser_total_actions = sum(metrics[attr][1] for attr in action_attrs)
    report.append(f"**Total actions**: Winners {winner_total_actions:.2f}, Losers {loser_total_actions:.2f}")
    report.append("")

    # Action percentages
    report.append("### 3.2 Action Distribution (Percentage)")
    report.append("")
    report.append("| Action | Winners (%) | Losers (%) |")
    report.append("|--------|-------------|------------|")
    for attr in action_attrs:
        winner_avg, loser_avg = metrics[attr]
        winner_pct = (winner_avg / winner_total_actions * 100) if winner_total_actions > 0 else 0
        loser_pct = (loser_avg / loser_total_actions * 100) if loser_total_actions > 0 else 0
        report.append(f"| {attr.replace('_', ' ').title()} | {winner_pct:.1f}% | {loser_pct:.1f}% |")
    report.append("")

    # Movement efficiency
    report.append("### 3.3 Movement Efficiency")
    report.append("")
    report.append("| Metric | Winners | Losers | Difference |")
    report.append("|--------|---------|--------|------------|")

    efficiency_attrs = ['total_fields', 'total_cards_used', 'cards_per_field']
    for attr in efficiency_attrs:
        winner_avg, loser_avg = metrics[attr]
        diff = winner_avg - loser_avg
        sign = "+" if diff > 0 else ""
        report.append(f"| {attr.replace('_', ' ').title()} | {winner_avg:.2f} | {loser_avg:.2f} | {sign}{diff:.2f} |")
    report.append("")

    # Hand management
    report.append("### 3.4 Hand Management")
    report.append("")
    report.append("| Metric | Winners | Losers | Difference |")
    report.append("|--------|---------|--------|------------|")

    hand_attrs = ['avg_hand_size', 'min_hand_size', 'max_hand_size', 'team_car_round_avg']
    for attr in hand_attrs:
        winner_avg, loser_avg = metrics[attr]
        diff = winner_avg - loser_avg
        sign = "+" if diff > 0 else ""
        report.append(f"| {attr.replace('_', ' ').title()} | {winner_avg:.2f} | {loser_avg:.2f} | {sign}{diff:.2f} |")
    report.append("")

    # Scoring breakdown
    report.append("### 3.5 Scoring Breakdown")
    report.append("")
    report.append("| Metric | Winners | Losers | Difference |")
    report.append("|--------|---------|--------|------------|")

    score_attrs = ['sprint_points', 'finish_points']
    for attr in score_attrs:
        winner_avg, loser_avg = metrics[attr]
        diff = winner_avg - loser_avg
        sign = "+" if diff > 0 else ""
        report.append(f"| {attr.replace('_', ' ').title()} | {winner_avg:.2f} | {loser_avg:.2f} | {sign}{diff:.2f} |")

    # Total points
    winner_total_points = metrics['sprint_points'][0] + metrics['finish_points'][0]
    loser_total_points = metrics['sprint_points'][1] + metrics['finish_points'][1]
    report.append(f"| **Total Points** | **{winner_total_points:.2f}** | **{loser_total_points:.2f}** | **+{winner_total_points - loser_total_points:.2f}** |")
    report.append("")

    # Sprint vs Finish ratio
    winner_sprint_ratio = (metrics['sprint_points'][0] / winner_total_points * 100) if winner_total_points > 0 else 0
    loser_sprint_ratio = (metrics['sprint_points'][1] / loser_total_points * 100) if loser_total_points > 0 else 0
    report.append(f"**Sprint vs Finish ratio**: Winners {winner_sprint_ratio:.1f}% sprint / {100-winner_sprint_ratio:.1f}% finish, Losers {loser_sprint_ratio:.1f}% sprint / {100-loser_sprint_ratio:.1f}% finish")
    report.append("")

    # Game progression
    report.append("### 3.6 Game Progression")
    report.append("")
    report.append("| Metric | Winners | Losers | Difference |")
    report.append("|--------|---------|--------|------------|")

    progression_attrs = ['rounds_to_finish', 'early_game_fields', 'mid_game_fields', 'late_game_fields']
    for attr in progression_attrs:
        winner_avg, loser_avg = metrics[attr]
        diff = winner_avg - loser_avg
        sign = "+" if diff > 0 else ""
        report.append(f"| {attr.replace('_', ' ').title()} | {winner_avg:.2f} | {loser_avg:.2f} | {sign}{diff:.2f} |")
    report.append("")

    # Field distribution across game phases
    winner_early_pct = (metrics['early_game_fields'][0] / metrics['total_fields'][0] * 100) if metrics['total_fields'][0] > 0 else 0
    winner_mid_pct = (metrics['mid_game_fields'][0] / metrics['total_fields'][0] * 100) if metrics['total_fields'][0] > 0 else 0
    winner_late_pct = (metrics['late_game_fields'][0] / metrics['total_fields'][0] * 100) if metrics['total_fields'][0] > 0 else 0

    loser_early_pct = (metrics['early_game_fields'][1] / metrics['total_fields'][1] * 100) if metrics['total_fields'][1] > 0 else 0
    loser_mid_pct = (metrics['mid_game_fields'][1] / metrics['total_fields'][1] * 100) if metrics['total_fields'][1] > 0 else 0
    loser_late_pct = (metrics['late_game_fields'][1] / metrics['total_fields'][1] * 100) if metrics['total_fields'][1] > 0 else 0

    report.append("**Field distribution across game phases**:")
    report.append(f"- Winners: Early {winner_early_pct:.1f}%, Mid {winner_mid_pct:.1f}%, Late {winner_late_pct:.1f}%")
    report.append(f"- Losers: Early {loser_early_pct:.1f}%, Mid {loser_mid_pct:.1f}%, Late {loser_late_pct:.1f}%")
    report.append("")

    # Agent-specific performance
    report.append("## 4. Agent-Specific Performance")
    report.append("")

    # Group player stats by agent
    agent_player_stats = defaultdict(list)
    for ps in player_stats:
        agent_player_stats[ps.agent].append(ps)

    # Calculate averages for each agent
    report.append("### 4.1 Top Performing Agents (by win rate, min 10 games)")
    report.append("")

    agent_metrics = {}
    for agent, stats_list in agent_player_stats.items():
        if len(stats_list) < 10:
            continue

        wins = sum(1 for s in stats_list if s.won)
        games = len(stats_list)
        win_rate = wins / games

        avg_score = statistics.mean(s.final_score for s in stats_list)
        avg_cards_per_field = statistics.mean(s.cards_per_field for s in stats_list if s.cards_per_field > 0)
        avg_drafts = statistics.mean(s.drafts + s.team_drafts for s in stats_list)
        avg_sprint_points = statistics.mean(s.sprint_points for s in stats_list)
        avg_finish_points = statistics.mean(s.finish_points for s in stats_list)

        agent_metrics[agent] = {
            'win_rate': win_rate,
            'games': games,
            'avg_score': avg_score,
            'avg_cards_per_field': avg_cards_per_field,
            'avg_drafts': avg_drafts,
            'avg_sprint_points': avg_sprint_points,
            'avg_finish_points': avg_finish_points,
        }

    sorted_agents_by_wr = sorted(agent_metrics.items(), key=lambda x: x[1]['win_rate'], reverse=True)

    report.append("| Agent | Win Rate | Games | Avg Score | Cards/Field | Avg Drafts | Sprint Pts | Finish Pts |")
    report.append("|-------|----------|-------|-----------|-------------|------------|------------|------------|")
    for agent, am in sorted_agents_by_wr[:10]:
        report.append(f"| {agent} | {am['win_rate']:.1%} | {am['games']} | {am['avg_score']:.1f} | {am['avg_cards_per_field']:.2f} | {am['avg_drafts']:.1f} | {am['avg_sprint_points']:.1f} | {am['avg_finish_points']:.1f} |")
    report.append("")

    # End conditions
    report.append("## 5. Game End Conditions")
    report.append("")

    end_reasons = defaultdict(int)
    for game in game_stats:
        end_reasons[game.end_reason] += 1

    report.append("| End Reason | Count | Percentage |")
    report.append("|------------|-------|------------|")
    total_games = len(game_stats)
    for reason in sorted(end_reasons.keys()):
        count = end_reasons[reason]
        pct = count / total_games * 100
        report.append(f"| {reason} | {count} | {pct:.1f}% |")
    report.append("")

    # Game length distribution
    report.append("## 6. Game Length Distribution")
    report.append("")

    rounds_list = [game.rounds for game in game_stats]
    report.append(f"- **Mean**: {statistics.mean(rounds_list):.1f} rounds")
    report.append(f"- **Median**: {statistics.median(rounds_list):.1f} rounds")
    report.append(f"- **Min**: {min(rounds_list)} rounds")
    report.append(f"- **Max**: {max(rounds_list)} rounds")
    report.append(f"- **Std Dev**: {statistics.stdev(rounds_list):.1f} rounds")
    report.append("")

    return "\n".join(report)


def main():
    """Main entry point."""
    logs_dir = '/Users/tobi/Projects/chasse_patate_sim/game_logs'

    print("Analyzing all game logs...")
    game_stats, player_stats = analyze_all_games(logs_dir)

    print(f"Found {len(game_stats)} games and {len(player_stats)} player-game instances")

    print("Generating report...")
    report = generate_report(game_stats, player_stats)

    # Save report
    output_path = '/Users/tobi/Projects/chasse_patate_sim/FULL_ANALYSIS.md'
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"Report saved to {output_path}")


if __name__ == '__main__':
    main()
