#!/usr/bin/env python3
"""
Analyze endgame behavior and key decision points.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any

def load_game_log(filepath: Path) -> Dict[str, Any]:
    """Load a single game log JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_endgame(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the final 1/3 of the game."""

    # Get winner info
    final_result = game_data['final_result']
    winner_str = final_result['winner']
    winner_id = int(winner_str.split('Player ')[-1].rstrip(')'))

    agents = {a['player_id']: a['type'] for a in game_data['agents']}

    total_rounds = final_result['total_rounds']
    endgame_start = (2 * total_rounds) // 3

    endgame = {
        'winner_id': winner_id,
        'winner_agent': agents[winner_id],
        'agents': agents,
        'total_rounds': total_rounds,
        'endgame_start': endgame_start,
        'winner_endgame_actions': Counter(),
        'loser_endgame_actions': Counter(),
        'winner_finish_arrival': None,  # Which round winner reached finish
        'loser_finish_arrival': None,
        'winner_lead_changes': 0,  # Times winner took/lost lead
        'hand_management': {
            'winner_endgame_avg': 0,
            'loser_endgame_avg': 0,
            'winner_final_hand': 0,
            'loser_final_hand': 0,
        },
        'finish_sprint': {
            'winner_finish_points': 0,
            'loser_finish_points': 0,
        }
    }

    # Track when first rider reaches finish (position 40)
    winner_hand_sizes = []
    loser_hand_sizes = []

    for entry in game_data['move_history']:
        player_id = entry['player']
        move = entry['move']
        state = entry['state']
        round_num = entry['round']

        if not move['success']:
            continue

        is_winner = (player_id == winner_id)

        # Endgame actions
        if round_num >= endgame_start:
            action = move['action']
            if is_winner:
                endgame['winner_endgame_actions'][action] += 1
                winner_hand_sizes.append(state['player_hand_sizes'][player_id])
            else:
                endgame['loser_endgame_actions'][action] += 1
                loser_hand_sizes.append(state['player_hand_sizes'][player_id])

        # Check for finish arrival
        new_pos = move.get('new_position', 0)
        if new_pos >= 40:  # Finish line
            if is_winner and endgame['winner_finish_arrival'] is None:
                endgame['winner_finish_arrival'] = round_num
            elif not is_winner and endgame['loser_finish_arrival'] is None:
                endgame['loser_finish_arrival'] = round_num

        # Track finish points
        if 'checkpoints_reached' in move and move['checkpoints_reached']:
            checkpoint_pos = move['checkpoints_reached'][0] if isinstance(move['checkpoints_reached'], list) else move['checkpoints_reached']
            if isinstance(checkpoint_pos, int) and checkpoint_pos >= 30:  # Finish checkpoint
                points = move.get('points_earned', 0)
                if is_winner:
                    endgame['finish_sprint']['winner_finish_points'] += points
                else:
                    endgame['finish_sprint']['loser_finish_points'] += points

    # Calculate endgame hand averages
    if winner_hand_sizes:
        endgame['hand_management']['winner_endgame_avg'] = sum(winner_hand_sizes) / len(winner_hand_sizes)
        endgame['hand_management']['winner_final_hand'] = winner_hand_sizes[-1] if winner_hand_sizes else 0

    if loser_hand_sizes:
        endgame['hand_management']['loser_endgame_avg'] = sum(loser_hand_sizes) / len(loser_hand_sizes)
        endgame['hand_management']['loser_final_hand'] = loser_hand_sizes[-1] if loser_hand_sizes else 0

    return endgame

def main():
    """Analyze endgame patterns across games."""
    game_logs_dir = Path('/Users/tobi/Projects/chasse_patate_sim/game_logs')

    all_endgames = []

    print("Loading and analyzing endgame patterns...\n")

    for i in range(15):
        game_file = game_logs_dir / f'game_{i}.json'
        if not game_file.exists():
            continue

        try:
            game_data = load_game_log(game_file)
            endgame = analyze_endgame(game_data)
            all_endgames.append(endgame)
            print(f"Game {i}: {endgame['winner_agent']} won (reached finish round {endgame['winner_finish_arrival']})")
        except Exception as e:
            import traceback
            print(f"Error analyzing game {i}: {e}")
            print(traceback.format_exc())

    print(f"\n{'='*80}")
    print("ENDGAME INSIGHTS")
    print(f"{'='*80}\n")

    # 1. Endgame Action Preferences
    print("1. ENDGAME ACTION PREFERENCES (final 1/3 of game)")
    print("-" * 40)

    total_winner_actions = Counter()
    total_loser_actions = Counter()

    for eg in all_endgames:
        total_winner_actions += eg['winner_endgame_actions']
        total_loser_actions += eg['loser_endgame_actions']

    num_games = len(all_endgames)

    print("  Winners' endgame actions (avg per game):")
    for action in ['Pull', 'TeamPull', 'Draft', 'TeamDraft', 'Attack', 'TeamCar']:
        avg = total_winner_actions[action] / num_games
        print(f"    {action:12s}: {avg:5.2f}")

    print("\n  Losers' endgame actions (avg per game):")
    for action in ['Pull', 'TeamPull', 'Draft', 'TeamDraft', 'Attack', 'TeamCar']:
        avg = total_loser_actions[action] / num_games
        print(f"    {action:12s}: {avg:5.2f}")

    # 2. Race to Finish Timing
    print(f"\n2. RACE TO FINISH TIMING")
    print("-" * 40)

    winner_arrivals = [eg['winner_finish_arrival'] for eg in all_endgames if eg['winner_finish_arrival']]
    loser_arrivals = [eg['loser_finish_arrival'] for eg in all_endgames if eg['loser_finish_arrival']]

    if winner_arrivals:
        avg_winner = sum(winner_arrivals) / len(winner_arrivals)
        print(f"  Winners reach finish at round: {avg_winner:.1f} (range: {min(winner_arrivals)}-{max(winner_arrivals)})")

    if loser_arrivals:
        avg_loser = sum(loser_arrivals) / len(loser_arrivals)
        print(f"  Losers reach finish at round:  {avg_loser:.1f} (range: {min(loser_arrivals)}-{max(loser_arrivals)})")

    if winner_arrivals and loser_arrivals:
        avg_gap = avg_loser - avg_winner
        print(f"  Average gap: {avg_gap:.1f} rounds")

    # 3. Endgame Hand Management
    print(f"\n3. ENDGAME HAND MANAGEMENT")
    print("-" * 40)

    winner_endgame_hands = [eg['hand_management']['winner_endgame_avg'] for eg in all_endgames]
    loser_endgame_hands = [eg['hand_management']['loser_endgame_avg'] for eg in all_endgames]

    if winner_endgame_hands:
        avg_winner = sum(winner_endgame_hands) / len(winner_endgame_hands)
        print(f"  Winners' avg endgame hand: {avg_winner:.2f} cards")

    if loser_endgame_hands:
        avg_loser = sum(loser_endgame_hands) / len(loser_endgame_hands)
        print(f"  Losers' avg endgame hand:  {avg_loser:.2f} cards")

    winner_final_hands = [eg['hand_management']['winner_final_hand'] for eg in all_endgames if eg['hand_management']['winner_final_hand'] > 0]
    loser_final_hands = [eg['hand_management']['loser_final_hand'] for eg in all_endgames if eg['hand_management']['loser_final_hand'] > 0]

    if winner_final_hands:
        avg_winner_final = sum(winner_final_hands) / len(winner_final_hands)
        print(f"  Winners' final hand: {avg_winner_final:.2f} cards")

    if loser_final_hands:
        avg_loser_final = sum(loser_final_hands) / len(loser_final_hands)
        print(f"  Losers' final hand:  {avg_loser_final:.2f} cards")

    # 4. Finish Sprint Scoring
    print(f"\n4. FINISH LINE SCORING")
    print("-" * 40)

    winner_finish = sum(eg['finish_sprint']['winner_finish_points'] for eg in all_endgames)
    loser_finish = sum(eg['finish_sprint']['loser_finish_points'] for eg in all_endgames)

    print(f"  Winners score {winner_finish/num_games:.2f} finish points per game")
    print(f"  Losers score {loser_finish/num_games:.2f} finish points per game")

    # 5. Agent-specific endgame patterns
    print(f"\n5. AGENT-SPECIFIC ENDGAME PATTERNS")
    print("-" * 40)

    by_agent = defaultdict(list)
    for eg in all_endgames:
        by_agent[eg['winner_agent']].append(eg)

    for agent, endgames in sorted(by_agent.items()):
        print(f"\n  {agent} ({len(endgames)} wins):")

        # Most common endgame actions
        agent_actions = Counter()
        for eg in endgames:
            agent_actions += eg['winner_endgame_actions']

        top_actions = agent_actions.most_common(3)
        print(f"    Top endgame actions:", end='')
        for action, count in top_actions:
            avg = count / len(endgames)
            print(f" {action}({avg:.1f})", end='')
        print()

        # Finish timing
        arrivals = [eg['winner_finish_arrival'] for eg in endgames if eg['winner_finish_arrival']]
        if arrivals:
            avg_arrival = sum(arrivals) / len(arrivals)
            print(f"    Reaches finish: round {avg_arrival:.1f}")

        # Hand management
        endgame_hands = [eg['hand_management']['winner_endgame_avg'] for eg in endgames]
        if endgame_hands:
            avg_hand = sum(endgame_hands) / len(endgame_hands)
            print(f"    Endgame hand size: {avg_hand:.2f} cards")

    print(f"\n6. KEY TAKEAWAYS")
    print("-" * 40)

    # Calculate key differentiators
    winner_pull_rate = total_winner_actions['Pull'] / num_games
    loser_pull_rate = total_loser_actions['Pull'] / num_games
    winner_teampull_rate = total_winner_actions['TeamPull'] / num_games
    loser_teampull_rate = total_loser_actions['TeamPull'] / num_games
    winner_attack_rate = total_winner_actions['Attack'] / num_games
    loser_attack_rate = total_loser_actions['Attack'] / num_games

    print(f"  Winners prioritize:")
    if winner_teampull_rate > loser_teampull_rate:
        diff = winner_teampull_rate - loser_teampull_rate
        print(f"    - TeamPull {diff:.1f}x more than losers in endgame")
    if winner_attack_rate > loser_attack_rate:
        diff = winner_attack_rate - loser_attack_rate
        print(f"    - Attack {diff:.1f}x more than losers in endgame")
    if winner_pull_rate < loser_pull_rate:
        diff = loser_pull_rate - winner_pull_rate
        print(f"    - {diff:.1f} fewer basic Pulls than losers")

    if winner_arrivals and loser_arrivals:
        print(f"    - Reach finish {avg_gap:.1f} rounds earlier on average")

    print(f"\n{'='*80}\n")

if __name__ == '__main__':
    main()
