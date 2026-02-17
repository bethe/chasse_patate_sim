#!/usr/bin/env python3
"""
Deep strategic analysis of game patterns - when winners make key decisions.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any

def load_game_log(filepath: Path) -> Dict[str, Any]:
    """Load a single game log JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_strategic_patterns(game_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze when and how winners make strategic decisions."""

    # Get winner info
    final_result = game_data['final_result']
    winner_str = final_result['winner']
    winner_id = int(winner_str.split('Player ')[-1].rstrip(')'))

    agents = {a['player_id']: a['type'] for a in game_data['agents']}
    winner_agent = agents[winner_id]

    patterns = {
        'winner_id': winner_id,
        'winner_agent': winner_agent,
        'agents': agents,
        'winner_teamcar_timing': [],  # When winner uses TeamCar (hand sizes)
        'winner_attack_timing': [],   # When winner attacks (positions, terrain)
        'winner_draft_opportunities': 0,  # How many times winner could draft
        'winner_drafts_taken': 0,
        'loser_draft_opportunities': 0,
        'loser_drafts_taken': 0,
        'winner_sprint_attempts': 0,   # Times winner reached sprint checkpoint
        'winner_sprint_scores': 0,
        'loser_sprint_attempts': 0,
        'loser_sprint_scores': 0,
        'winner_aggressive_early': 0,  # Attacks in first 1/3 of game
        'winner_aggressive_late': 0,   # Attacks in last 1/3 of game
        'loser_aggressive_early': 0,
        'loser_aggressive_late': 0,
        'winner_uses_terrain_limits': 0,  # Moves that hit terrain limits
        'winner_card_efficiency': [],  # Cards per field moved
        'loser_card_efficiency': [],
        'winner_grouped_moves': 0,  # Times multiple riders move together
        'loser_grouped_moves': 0,
    }

    total_rounds = final_result['total_rounds']
    early_cutoff = total_rounds // 3
    late_cutoff = (2 * total_rounds) // 3

    # Track positions to detect drafting opportunities
    last_positions = {}  # rider -> position

    for entry in game_data['move_history']:
        player_id = entry['player']
        move = entry['move']
        state = entry['state']
        round_num = entry['round']

        if not move['success']:
            continue

        action = move['action']
        is_winner = (player_id == winner_id)

        # TeamCar timing - track hand size when TeamCar is used
        if action == 'TeamCar' and is_winner:
            hand_size = state['player_hand_sizes'][player_id]
            patterns['winner_teamcar_timing'].append(hand_size)

        # Attack timing and terrain
        if action == 'Attack':
            if is_winner:
                patterns['winner_attack_timing'].append({
                    'round': round_num,
                    'position': move.get('old_position', 0),
                    'terrain': move.get('old_terrain', ''),
                    'movement': move.get('movement', 0)
                })
                if round_num <= early_cutoff:
                    patterns['winner_aggressive_early'] += 1
                elif round_num >= late_cutoff:
                    patterns['winner_aggressive_late'] += 1
            else:
                if round_num <= early_cutoff:
                    patterns['loser_aggressive_early'] += 1
                elif round_num >= late_cutoff:
                    patterns['loser_aggressive_late'] += 1

        # Draft opportunities - could this move have been a draft?
        # A draft opportunity exists when there's a rider ahead at a position you could reach
        rider_id = move.get('rider', '')
        old_pos = move.get('old_position', 0)
        new_pos = move.get('new_position', 0)

        # Check if there was a rider at new_pos that this rider could draft from
        had_draft_opportunity = False
        for other_rider, other_pos in last_positions.items():
            if other_rider != rider_id and other_pos == new_pos:
                had_draft_opportunity = True
                break

        if had_draft_opportunity:
            if is_winner:
                patterns['winner_draft_opportunities'] += 1
                if action in ['Draft', 'TeamDraft']:
                    patterns['winner_drafts_taken'] += 1
            else:
                patterns['loser_draft_opportunities'] += 1
                if action in ['Draft', 'TeamDraft']:
                    patterns['loser_drafts_taken'] += 1

        # Sprint scoring
        if 'checkpoints_reached' in move and move['checkpoints_reached']:
            checkpoint_pos = move['checkpoints_reached'][0] if isinstance(move['checkpoints_reached'], list) else move['checkpoints_reached']
            if isinstance(checkpoint_pos, int) and checkpoint_pos < 30:  # Sprint checkpoint
                if is_winner:
                    patterns['winner_sprint_attempts'] += 1
                    if move.get('points_earned', 0) > 0:
                        patterns['winner_sprint_scores'] += 1
                else:
                    patterns['loser_sprint_attempts'] += 1
                    if move.get('points_earned', 0) > 0:
                        patterns['loser_sprint_scores'] += 1

        # Card efficiency
        if 'cards_played' in move and move['cards_played'] and 'movement' in move:
            cards_used = len(move['cards_played'])
            movement = move['movement']
            if movement > 0:
                efficiency = cards_used / movement
                if is_winner:
                    patterns['winner_card_efficiency'].append(efficiency)
                else:
                    patterns['loser_card_efficiency'].append(efficiency)

        # Grouped moves (TeamPull, TeamDraft)
        if action in ['TeamPull', 'TeamDraft']:
            if is_winner:
                patterns['winner_grouped_moves'] += 1
            else:
                patterns['loser_grouped_moves'] += 1

        # Update positions
        last_positions[rider_id] = new_pos
        if 'drafting_riders' in move and move['drafting_riders']:
            for drafter in move['drafting_riders']:
                drafter_id = drafter['rider']
                last_positions[drafter_id] = drafter['new_position']

    return patterns

def main():
    """Analyze strategic patterns across games."""
    game_logs_dir = Path('/Users/tobi/Projects/chasse_patate_sim/game_logs')

    all_patterns = []

    print("Loading and analyzing strategic patterns...\n")

    for i in range(15):
        game_file = game_logs_dir / f'game_{i}.json'
        if not game_file.exists():
            continue

        try:
            game_data = load_game_log(game_file)
            patterns = analyze_strategic_patterns(game_data)
            all_patterns.append(patterns)
            print(f"Game {i}: {patterns['winner_agent']} won")
        except Exception as e:
            import traceback
            print(f"Error analyzing game {i}: {e}")
            print(traceback.format_exc())

    print(f"\n{'='*80}")
    print("STRATEGIC INSIGHTS")
    print(f"{'='*80}\n")

    # 1. TeamCar Usage Timing
    print("1. TEAMCAR USAGE TIMING (hand size when used)")
    print("-" * 40)
    all_teamcar_hands = []
    for p in all_patterns:
        all_teamcar_hands.extend(p['winner_teamcar_timing'])

    if all_teamcar_hands:
        avg_hand = sum(all_teamcar_hands) / len(all_teamcar_hands)
        print(f"  Winners use TeamCar at avg hand size: {avg_hand:.2f} cards")
        print(f"  Hand sizes when TeamCar used: min={min(all_teamcar_hands)}, max={max(all_teamcar_hands)}")
    else:
        print("  No TeamCar usage found in winners")

    # 2. Drafting Efficiency
    print(f"\n2. DRAFTING EFFICIENCY")
    print("-" * 40)

    winner_opp = sum(p['winner_draft_opportunities'] for p in all_patterns)
    winner_taken = sum(p['winner_drafts_taken'] for p in all_patterns)
    loser_opp = sum(p['loser_draft_opportunities'] for p in all_patterns)
    loser_taken = sum(p['loser_drafts_taken'] for p in all_patterns)

    if winner_opp > 0:
        winner_draft_rate = (winner_taken / winner_opp) * 100
        print(f"  Winners draft {winner_draft_rate:.1f}% of opportunities ({winner_taken}/{winner_opp})")

    if loser_opp > 0:
        loser_draft_rate = (loser_taken / loser_opp) * 100
        print(f"  Losers draft {loser_draft_rate:.1f}% of opportunities ({loser_taken}/{loser_opp})")

    # 3. Sprint Point Strategy
    print(f"\n3. SPRINT POINT STRATEGY")
    print("-" * 40)

    winner_sprint_att = sum(p['winner_sprint_attempts'] for p in all_patterns)
    winner_sprint_score = sum(p['winner_sprint_scores'] for p in all_patterns)
    loser_sprint_att = sum(p['loser_sprint_attempts'] for p in all_patterns)
    loser_sprint_score = sum(p['loser_sprint_scores'] for p in all_patterns)

    if winner_sprint_att > 0:
        winner_sprint_rate = (winner_sprint_score / winner_sprint_att) * 100
        print(f"  Winners score sprints {winner_sprint_rate:.1f}% of time ({winner_sprint_score}/{winner_sprint_att} attempts)")

    if loser_sprint_att > 0:
        loser_sprint_rate = (loser_sprint_score / loser_sprint_att) * 100
        print(f"  Losers score sprints {loser_sprint_rate:.1f}% of time ({loser_sprint_score}/{loser_sprint_att} attempts)")

    # 4. Attack Timing (early vs late)
    print(f"\n4. AGGRESSION TIMING (Attacks)")
    print("-" * 40)

    winner_early = sum(p['winner_aggressive_early'] for p in all_patterns)
    winner_late = sum(p['winner_aggressive_late'] for p in all_patterns)
    loser_early = sum(p['loser_aggressive_early'] for p in all_patterns)
    loser_late = sum(p['loser_aggressive_late'] for p in all_patterns)

    print(f"  Winners: {winner_early} early attacks, {winner_late} late attacks")
    print(f"  Losers:  {loser_early} early attacks, {loser_late} late attacks")

    if winner_early + winner_late > 0:
        winner_late_pct = (winner_late / (winner_early + winner_late)) * 100
        print(f"  Winners attack late {winner_late_pct:.1f}% of the time")

    # 5. Card Efficiency
    print(f"\n5. CARD EFFICIENCY (cards per field moved)")
    print("-" * 40)

    all_winner_eff = []
    all_loser_eff = []
    for p in all_patterns:
        all_winner_eff.extend(p['winner_card_efficiency'])
        all_loser_eff.extend(p['loser_card_efficiency'])

    if all_winner_eff:
        avg_winner_eff = sum(all_winner_eff) / len(all_winner_eff)
        print(f"  Winners: {avg_winner_eff:.3f} cards per field (lower is better)")

    if all_loser_eff:
        avg_loser_eff = sum(all_loser_eff) / len(all_loser_eff)
        print(f"  Losers:  {avg_loser_eff:.3f} cards per field")

    # 6. Team Movement
    print(f"\n6. TEAM MOVEMENT (TeamPull/TeamDraft usage)")
    print("-" * 40)

    winner_grouped = sum(p['winner_grouped_moves'] for p in all_patterns)
    loser_grouped = sum(p['loser_grouped_moves'] for p in all_patterns)

    print(f"  Winners use team moves {winner_grouped/len(all_patterns):.1f} times per game")
    print(f"  Losers use team moves {loser_grouped/len(all_patterns):.1f} times per game")

    # 7. Attack Analysis
    print(f"\n7. ATTACK PATTERN ANALYSIS")
    print("-" * 40)

    attack_terrains = Counter()
    attack_positions = []

    for p in all_patterns:
        for attack in p['winner_attack_timing']:
            attack_terrains[attack['terrain']] += 1
            attack_positions.append(attack['position'])

    print(f"  Winners attack on terrain:")
    for terrain, count in attack_terrains.most_common():
        print(f"    {terrain:12s}: {count:3d} times")

    if attack_positions:
        print(f"  Average attack position: {sum(attack_positions)/len(attack_positions):.1f}")
        print(f"  Attack position range: {min(attack_positions)} to {max(attack_positions)}")

    print(f"\n8. AGENT-SPECIFIC PATTERNS")
    print("-" * 40)

    # Group by agent type
    by_agent = defaultdict(list)
    for p in all_patterns:
        by_agent[p['winner_agent']].append(p)

    for agent, patterns in by_agent.items():
        print(f"\n  {agent} ({len(patterns)} wins):")

        avg_teamcar = sum(len(p['winner_teamcar_timing']) for p in patterns) / len(patterns)
        print(f"    Avg TeamCar uses per game: {avg_teamcar:.1f}")

        avg_attacks = sum(len(p['winner_attack_timing']) for p in patterns) / len(patterns)
        print(f"    Avg attacks per game: {avg_attacks:.1f}")

        avg_grouped = sum(p['winner_grouped_moves'] for p in patterns) / len(patterns)
        print(f"    Avg team moves per game: {avg_grouped:.1f}")

        sprint_att = sum(p['winner_sprint_attempts'] for p in patterns)
        sprint_score = sum(p['winner_sprint_scores'] for p in patterns)
        if sprint_att > 0:
            sprint_rate = (sprint_score / sprint_att) * 100
            print(f"    Sprint scoring: {sprint_rate:.1f}% ({sprint_score}/{sprint_att})")

    print(f"\n{'='*80}\n")

if __name__ == '__main__':
    main()
