#!/usr/bin/env python3
"""
Analyze game logs to identify winning patterns and strategies.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any

def load_game_log(filepath: Path) -> Dict[str, Any]:
    """Load a single game log JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_game(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from a game log."""

    # Get winner info from final_result
    final_result = game_data['final_result']
    winner_str = final_result['winner']  # Format: "AgentName (Player X)"
    winner_id = int(winner_str.split('Player ')[-1].rstrip(')'))

    # Get agent types
    agents = {a['player_id']: a['type'] for a in game_data['agents']}
    winner_agent = agents[winner_id]

    # Analyze moves by player
    player_stats = defaultdict(lambda: {
        'actions': Counter(),
        'cards_used': 0,
        'cards_drawn': 0,
        'sprint_points': 0,
        'finish_points': 0,
        'total_advancement': 0,
        'drafts': 0,
        'team_drafts': 0,
        'pulls': 0,
        'attacks': 0,
        'team_pulls': 0,
        'team_cars': 0,
        'hand_sizes': [],
        'avg_hand_size': 0
    })

    # Process all moves
    for entry in game_data['move_history']:
        player_id = entry['player']
        move = entry['move']
        state = entry['state']

        if move['success']:
            action = move['action']
            player_stats[player_id]['actions'][action] += 1

            # Count specific actions
            if action == 'Draft':
                player_stats[player_id]['drafts'] += 1
            elif action == 'TeamDraft':
                player_stats[player_id]['team_drafts'] += 1
            elif action == 'Pull':
                player_stats[player_id]['pulls'] += 1
            elif action == 'Attack':
                player_stats[player_id]['attacks'] += 1
            elif action == 'TeamPull':
                player_stats[player_id]['team_pulls'] += 1
            elif action == 'TeamCar':
                player_stats[player_id]['team_cars'] += 1

            # Count cards used
            if 'cards_played' in move and move['cards_played']:
                player_stats[player_id]['cards_used'] += len(move['cards_played'])

            # Count cards drawn
            if 'cards_drawn' in move:
                cards_drawn = move['cards_drawn']
                if isinstance(cards_drawn, int):
                    player_stats[player_id]['cards_drawn'] += cards_drawn
                elif isinstance(cards_drawn, list):
                    player_stats[player_id]['cards_drawn'] += len(cards_drawn)

            # Track advancement
            if 'movement' in move and move['movement']:
                player_stats[player_id]['total_advancement'] += move['movement']

            # Also count drafting riders advancement
            if 'drafting_riders' in move and move['drafting_riders']:
                for drafter in move['drafting_riders']:
                    advancement = drafter.get('new_position', 0) - drafter.get('old_position', 0)
                    player_stats[player_id]['total_advancement'] += advancement

            # Track points earned
            if 'points_earned' in move and move['points_earned']:
                # We'll break this down later from final scores
                pass

        # Track hand sizes for each player
        for i, hand_size in enumerate(state['player_hand_sizes']):
            player_stats[i]['hand_sizes'].append(hand_size)

    # Get final scores
    for player_id in range(game_data['num_players']):
        final_score = final_result['final_scores'][f'Player {player_id}']
        player_stats[player_id]['final_score'] = final_score

        # Calculate average hand size
        if player_stats[player_id]['hand_sizes']:
            player_stats[player_id]['avg_hand_size'] = sum(player_stats[player_id]['hand_sizes']) / len(player_stats[player_id]['hand_sizes'])

    # Extract sprint and finish points from move history
    # Checkpoints_reached contains position numbers
    # Position 20 is typically a sprint, position 40 is typically finish
    # But let's just track total points earned via checkpoints vs other means
    for entry in game_data['move_history']:
        player_id = entry['player']
        move = entry['move']

        if move['success'] and 'points_earned' in move and move['points_earned'] > 0:
            # If checkpoints_reached is not None and not empty, these are checkpoint points
            if 'checkpoints_reached' in move and move['checkpoints_reached']:
                # Early checkpoint (position < 30) likely sprint, later likely finish
                checkpoint_pos = move['checkpoints_reached'][0] if isinstance(move['checkpoints_reached'], list) else move['checkpoints_reached']
                if isinstance(checkpoint_pos, int) and checkpoint_pos < 30:
                    player_stats[player_id]['sprint_points'] += move['points_earned']
                else:
                    player_stats[player_id]['finish_points'] += move['points_earned']
            else:
                # Points without checkpoints are arrival order points (sprint/finish)
                # These tend to be finish points since they're arrival-based
                player_stats[player_id]['finish_points'] += move['points_earned']

    return {
        'winner_id': winner_id,
        'winner_agent': winner_agent,
        'agents': agents,
        'player_stats': dict(player_stats),
        'num_rounds': final_result['total_rounds'],
        'end_reason': final_result['game_over_reason']
    }

def main():
    """Analyze first 15 game logs."""
    game_logs_dir = Path('/Users/tobi/Projects/chasse_patate_sim/game_logs')

    # Collect all game analyses
    all_games = []

    print("Loading and analyzing game logs...\n")

    for i in range(15):
        game_file = game_logs_dir / f'game_{i}.json'
        if not game_file.exists():
            continue

        try:
            game_data = load_game_log(game_file)
            analysis = analyze_game(game_data)
            all_games.append(analysis)
            print(f"Game {i}: Winner = {analysis['winner_agent']} (Player {analysis['winner_id']})")
        except Exception as e:
            import traceback
            print(f"Error analyzing game {i}: {e}")
            print(traceback.format_exc())

    print(f"\n{'='*80}")
    print("SUMMARY ANALYSIS")
    print(f"{'='*80}\n")

    # 1. Agent win rates
    print("1. AGENT WIN RATES")
    print("-" * 40)
    agent_wins = Counter([g['winner_agent'] for g in all_games])
    total_games = len(all_games)
    for agent, wins in agent_wins.most_common():
        win_rate = (wins / total_games) * 100
        print(f"  {agent:20s}: {wins:2d} wins ({win_rate:5.1f}%)")

    # 2. Action usage comparison (winners vs non-winners)
    print(f"\n2. ACTION USAGE PATTERNS")
    print("-" * 40)

    winner_actions = Counter()
    loser_actions = Counter()
    winner_count = 0
    loser_count = 0

    for game in all_games:
        for pid, stats in game['player_stats'].items():
            if pid == game['winner_id']:
                winner_actions += stats['actions']
                winner_count += 1
            else:
                loser_actions += stats['actions']
                loser_count += 1

    # Normalize to per-game averages
    print("\n  Winners' average actions per game:")
    for action in ['Draft', 'TeamDraft', 'Pull', 'TeamPull', 'Attack', 'TeamCar']:
        avg = winner_actions[action] / winner_count if winner_count > 0 else 0
        print(f"    {action:12s}: {avg:5.2f}")

    print("\n  Losers' average actions per game:")
    for action in ['Draft', 'TeamDraft', 'Pull', 'TeamPull', 'Attack', 'TeamCar']:
        avg = loser_actions[action] / loser_count if loser_count > 0 else 0
        print(f"    {action:12s}: {avg:5.2f}")

    # 3. Card hand management
    print(f"\n3. CARD HAND MANAGEMENT")
    print("-" * 40)

    winner_avg_hands = []
    loser_avg_hands = []

    for game in all_games:
        for pid, stats in game['player_stats'].items():
            if pid == game['winner_id']:
                winner_avg_hands.append(stats['avg_hand_size'])
            else:
                loser_avg_hands.append(stats['avg_hand_size'])

    if winner_avg_hands:
        print(f"  Winners' average hand size: {sum(winner_avg_hands)/len(winner_avg_hands):.2f} cards")
    if loser_avg_hands:
        print(f"  Losers' average hand size:  {sum(loser_avg_hands)/len(loser_avg_hands):.2f} cards")

    # 4. Sprint vs finish scoring
    print(f"\n4. SPRINT vs FINISH SCORING")
    print("-" * 40)

    winner_sprint_total = sum(game['player_stats'][game['winner_id']]['sprint_points'] for game in all_games)
    winner_finish_total = sum(game['player_stats'][game['winner_id']]['finish_points'] for game in all_games)

    loser_sprint_total = sum(
        stats['sprint_points']
        for game in all_games
        for pid, stats in game['player_stats'].items()
        if pid != game['winner_id']
    )
    loser_finish_total = sum(
        stats['finish_points']
        for game in all_games
        for pid, stats in game['player_stats'].items()
        if pid != game['winner_id']
    )

    print(f"  Winners - Sprint points: {winner_sprint_total/len(all_games):.2f} avg, Finish points: {winner_finish_total/len(all_games):.2f} avg")
    print(f"  Losers  - Sprint points: {loser_sprint_total/loser_count:.2f} avg, Finish points: {loser_finish_total/loser_count:.2f} avg")

    # 5. Total advancement
    print(f"\n5. ADVANCEMENT PATTERNS")
    print("-" * 40)

    winner_advancement = []
    loser_advancement = []

    for game in all_games:
        for pid, stats in game['player_stats'].items():
            if pid == game['winner_id']:
                winner_advancement.append(stats['total_advancement'])
            else:
                loser_advancement.append(stats['total_advancement'])

    if winner_advancement:
        print(f"  Winners' avg total advancement: {sum(winner_advancement)/len(winner_advancement):.1f} fields")
    if loser_advancement:
        print(f"  Losers' avg total advancement:  {sum(loser_advancement)/len(loser_advancement):.1f} fields")

    # 6. Efficiency metrics
    print(f"\n6. EFFICIENCY METRICS")
    print("-" * 40)

    # Calculate free moves (Draft + TeamDraft) vs paid moves
    winner_free_moves = sum(
        game['player_stats'][game['winner_id']]['drafts'] +
        game['player_stats'][game['winner_id']]['team_drafts']
        for game in all_games
    )
    winner_paid_moves = sum(
        game['player_stats'][game['winner_id']]['pulls'] +
        game['player_stats'][game['winner_id']]['attacks'] +
        game['player_stats'][game['winner_id']]['team_pulls']
        for game in all_games
    )

    loser_free_moves = sum(
        stats['drafts'] + stats['team_drafts']
        for game in all_games
        for pid, stats in game['player_stats'].items()
        if pid != game['winner_id']
    )
    loser_paid_moves = sum(
        stats['pulls'] + stats['attacks'] + stats['team_pulls']
        for game in all_games
        for pid, stats in game['player_stats'].items()
        if pid != game['winner_id']
    )

    winner_total = winner_free_moves + winner_paid_moves
    loser_total = loser_free_moves + loser_paid_moves

    if winner_total > 0:
        winner_free_pct = (winner_free_moves / winner_total) * 100
        print(f"  Winners' free moves: {winner_free_pct:.1f}% ({winner_free_moves}/{winner_total})")

    if loser_total > 0:
        loser_free_pct = (loser_free_moves / loser_total) * 100
        print(f"  Losers' free moves:  {loser_free_pct:.1f}% ({loser_free_moves}/{loser_total})")

    # 7. Game-specific insights
    print(f"\n7. DETAILED GAME-BY-GAME INSIGHTS")
    print("-" * 40)

    for i, game in enumerate(all_games[:10]):  # Show first 10 games
        winner_stats = game['player_stats'][game['winner_id']]
        print(f"\n  Game {i}: {game['winner_agent']} won")
        print(f"    Score: {winner_stats['final_score']} pts " +
              f"(Sprint: {winner_stats['sprint_points']}, Finish: {winner_stats['finish_points']})")
        print(f"    Actions: Draft={winner_stats['drafts']}, TeamDraft={winner_stats['team_drafts']}, " +
              f"Pull={winner_stats['pulls']}, TeamPull={winner_stats['team_pulls']}, Attack={winner_stats['attacks']}")
        print(f"    Avg hand: {winner_stats['avg_hand_size']:.1f} cards, Total advancement: {winner_stats['total_advancement']} fields")

    print(f"\n{'='*80}\n")

if __name__ == '__main__':
    main()
