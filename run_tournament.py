"""
Multi-player Tournament Script for Chasse Patate

Runs comprehensive tournament with all combinations of agents across
different player counts (2, 3, and 4 players).

Usage:
    python run_tournament.py

This will run:
- All 2-player combinations (C(5,2) = 10 combos × 10 games = 100 games)
- All 3-player combinations (C(5,3) = 10 combos × 10 games = 100 games)
- All 4-player combinations (C(5,4) = 5 combos × 10 games = 50 games)
Total: 250 games

Results saved to: game_logs/tournament_results_TIMESTAMP.csv
"""

from itertools import combinations
from simulator import GameSimulator
from agents import create_agent
import pandas as pd
from datetime import datetime
import os


def run_multiplayer_tournament(agent_types, games_per_combination=10):
    """
    Run tournament with all combinations of agents for 2, 3, and 4 players

    Args:
        agent_types: List of agent type strings (e.g., ['chatgpt', 'gemini', 'claudebot'])
        games_per_combination: Number of games to run per agent combination

    Returns:
        pandas.DataFrame with all tournament results
    """

    print("\n" + "="*80)
    print("CHASSE PATATE - MULTI-PLAYER TOURNAMENT")
    print("="*80)
    print(f"Agents: {', '.join(agent_types)}")
    print(f"Games per combination: {games_per_combination}")
    print("="*80 + "\n")

    # Ensure game_logs directory exists
    os.makedirs("game_logs", exist_ok=True)

    all_results = []
    total_games = 0

    # Run tournaments for 2, 3, and 4 players
    for num_players in [2, 3, 4]:
        print(f"\n{'='*80}")
        print(f"{num_players}-PLAYER GAMES")
        print(f"{'='*80}")

        # Generate all combinations
        combos = list(combinations(agent_types, num_players))
        total_combo_games = len(combos) * games_per_combination
        print(f"Combinations: {len(combos)}")
        print(f"Total games: {len(combos)} × {games_per_combination} = {total_combo_games}")
        print()

        # Create simulator for this player count
        sim = GameSimulator(num_players=num_players, verbose=False)

        combo_num = 0
        for combo in combos:
            combo_num += 1
            combo_str = ' vs '.join(combo)
            print(f"[{combo_num}/{len(combos)}] {combo_str}")

            # Run multiple games for this combination
            for game_num in range(games_per_combination):
                try:
                    # Create agents
                    agents = [create_agent(agent_type, player_id)
                             for player_id, agent_type in enumerate(combo)]

                    # Run game
                    game_log = sim.run_game(agents, game_id=total_games)
                    total_games += 1

                    # Extract results
                    final_result = game_log['final_result']
                    final_scores = final_result['final_scores']
                    winner = final_result['winner']
                    game_over_reason = final_result.get('game_over_reason', 'unknown')

                    # Record result
                    result = {
                        'game_id': total_games - 1,
                        'num_players': num_players,
                        'combination': combo_str,
                        'winner': winner,
                        'game_over_reason': game_over_reason,
                        'total_turns': len(game_log.get('move_history', []))
                    }

                    # Add individual player results
                    for i, agent_type in enumerate(combo):
                        result[f'player_{i}_agent'] = agent_type
                        result[f'player_{i}_score'] = final_scores.get(f'Player {i}', 0)

                    all_results.append(result)

                except Exception as e:
                    print(f"  ERROR in game {total_games}: {e}")
                    continue

            print(f"  Completed: {games_per_combination} games\n")

    # Create DataFrame
    df = pd.DataFrame(all_results)

    # Save results to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"game_logs/tournament_results_{timestamp}.csv"
    df.to_csv(filename, index=False)

    print("\n" + "="*80)
    print("TOURNAMENT COMPLETE")
    print("="*80)
    print(f"Total games played: {total_games}")
    print(f"Results saved to: {filename}")
    print("="*80 + "\n")

    # Print summary statistics
    print_summary(df, agent_types)

    return df, filename


def print_summary(df, agent_types):
    """Print comprehensive summary statistics for the tournament"""

    print("\n" + "="*80)
    print("TOURNAMENT SUMMARY")
    print("="*80 + "\n")

    # 1. Overall Win Counts by Agent
    print("=" * 80)
    print("1. OVERALL WINS BY AGENT")
    print("=" * 80)
    win_counts = {}
    for agent in agent_types:
        # Count wins where winner string contains the agent name
        wins = len(df[df['winner'].str.contains(agent, case=False, na=False)])
        win_counts[agent] = wins
        print(f"  {agent:20s}: {wins:4d} wins")

    # Find best performer
    best_agent = max(win_counts, key=win_counts.get)
    print(f"\n  🏆 Most wins: {best_agent} ({win_counts[best_agent]} wins)")

    # 2. Average Scores by Agent
    print("\n" + "=" * 80)
    print("2. AVERAGE SCORES BY AGENT")
    print("=" * 80)
    agent_stats = {}
    for agent in agent_types:
        scores = []
        games_played = 0

        # Collect scores from all player positions
        for i in range(4):  # Max 4 players
            agent_col = f'player_{i}_agent'
            score_col = f'player_{i}_score'
            if agent_col in df.columns and score_col in df.columns:
                agent_games = df[df[agent_col] == agent]
                scores.extend(agent_games[score_col].dropna().tolist())
                games_played += len(agent_games)

        if scores:
            avg_score = sum(scores) / len(scores)
            total_score = sum(scores)
            agent_stats[agent] = {
                'avg_score': avg_score,
                'total_score': total_score,
                'games': games_played
            }
            print(f"  {agent:20s}: {avg_score:6.2f} avg | {total_score:6.0f} total | {games_played:3d} games")

    # 3. Results by Player Count
    print("\n" + "=" * 80)
    print("3. RESULTS BY PLAYER COUNT")
    print("=" * 80)
    for num_players in [2, 3, 4]:
        subset = df[df['num_players'] == num_players]
        print(f"\n  {num_players}-Player Games ({len(subset)} total):")
        print("  " + "-" * 76)

        for agent in agent_types:
            wins = len(subset[subset['winner'].str.contains(agent, case=False, na=False)])
            win_rate = (wins / len(subset) * 100) if len(subset) > 0 else 0
            print(f"    {agent:20s}: {wins:3d} wins ({win_rate:5.1f}%)")

    # 4. Head-to-Head (2-Player Only)
    print("\n" + "=" * 80)
    print("4. HEAD-TO-HEAD RESULTS (2-Player Games)")
    print("=" * 80)
    two_player = df[df['num_players'] == 2]

    if len(two_player) > 0:
        h2h_matrix = {}
        for agent1 in agent_types:
            h2h_matrix[agent1] = {}
            for agent2 in agent_types:
                if agent1 == agent2:
                    h2h_matrix[agent1][agent2] = '-'
                else:
                    # Find games with these two agents
                    matches = two_player[
                        ((two_player['player_0_agent'] == agent1) & (two_player['player_1_agent'] == agent2)) |
                        ((two_player['player_0_agent'] == agent2) & (two_player['player_1_agent'] == agent1))
                    ]

                    agent1_wins = len(matches[matches['winner'].str.contains(agent1, case=False, na=False)])
                    total_matches = len(matches)

                    if total_matches > 0:
                        h2h_matrix[agent1][agent2] = f"{agent1_wins}/{total_matches}"
                    else:
                        h2h_matrix[agent1][agent2] = "0/0"

        # Print matrix
        print("\n  Win/Total (rows beat columns):")
        print("  " + " " * 15 + "  ".join(f"{agent[:8]:>8s}" for agent in agent_types))
        print("  " + "-" * (15 + 10 * len(agent_types)))
        for agent1 in agent_types:
            row = f"  {agent1[:15]:15s}"
            for agent2 in agent_types:
                row += f" {h2h_matrix[agent1][agent2]:>8s}"
            print(row)

    # 5. Game Over Reasons
    print("\n" + "=" * 80)
    print("5. GAME OVER REASONS")
    print("=" * 80)
    reason_counts = df['game_over_reason'].value_counts()
    for reason, count in reason_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {reason:45s}: {count:4d} ({pct:5.1f}%)")

    # 6. Game Length Statistics
    print("\n" + "=" * 80)
    print("6. GAME LENGTH STATISTICS")
    print("=" * 80)
    if 'total_turns' in df.columns:
        for num_players in [2, 3, 4]:
            subset = df[df['num_players'] == num_players]
            if len(subset) > 0:
                avg_turns = subset['total_turns'].mean()
                min_turns = subset['total_turns'].min()
                max_turns = subset['total_turns'].max()
                print(f"  {num_players}-Player: avg={avg_turns:.1f}, min={min_turns:.0f}, max={max_turns:.0f} turns")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    # Define agents for tournament
    agents = ['chatgpt', 'gemini', 'claudebot', 'tobibot', 'marc_soler']

    print("\nStarting comprehensive tournament...")
    print(f"This will run approximately 250 games (may take 10-20 minutes)\n")

    # Run tournament
    results_df, results_file = run_multiplayer_tournament(
        agent_types=agents,
        games_per_combination=10
    )

    print("✓ Tournament complete!")
    print(f"✓ Detailed results saved to: {results_file}")
    print(f"✓ Individual game logs saved to: game_logs/game_*.json")
    print(f"\nTo analyze further, load the CSV in pandas:")
    print(f"  df = pd.read_csv('{results_file}')")
