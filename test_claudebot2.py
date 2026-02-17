#!/usr/bin/env python3
"""
Test ClaudeBot 2.0 against top performing agents
Runs head-to-head matches to validate improvements
"""

from simulator import GameSimulator
from agents import create_agent
from analysis import GameAnalyzer
import json
from collections import defaultdict

def run_head_to_head(agent1_type: str, agent2_type: str, num_games: int = 20):
    """Run head-to-head matches between two agents"""
    print(f"\n{'='*60}")
    print(f"HEAD-TO-HEAD: {agent1_type.upper()} vs {agent2_type.upper()}")
    print(f"{'='*60}")

    sim = GameSimulator(verbose=False)

    # Alternate starting positions to be fair
    wins = {agent1_type: 0, agent2_type: 0}
    scores = {agent1_type: [], agent2_type: []}
    rounds_to_finish = {agent1_type: [], agent2_type: []}

    for i in range(num_games):
        # Alternate who goes first
        if i % 2 == 0:
            agents = [create_agent(agent1_type, 0), create_agent(agent2_type, 1)]
            agent_order = [agent1_type, agent2_type]
        else:
            agents = [create_agent(agent2_type, 0), create_agent(agent1_type, 1)]
            agent_order = [agent2_type, agent1_type]

        result = sim.run_game(agents)

        # Extract winner from name (format: "AgentName (Player N)")
        winner_name = result['final_result']['winner']
        # Parse player ID from winner name
        if "(Player " in winner_name:
            winner_id = int(winner_name.split("(Player ")[1].split(")")[0])
        else:
            # Fallback - find by highest score
            final_scores = result['final_result']['final_scores']
            winner_id = max(range(len(final_scores)),
                           key=lambda i: final_scores[f"Player {i}"])

        winner_type = agent_order[winner_id]
        wins[winner_type] += 1

        # Record scores from final_result
        final_scores = result['final_result']['final_scores']
        for player_num in range(len(agent_order)):
            player_type = agent_order[player_num]
            score = final_scores[f"Player {player_num}"]
            scores[player_type].append(score)

        # TODO: track rounds to finish - would need to parse move_history

    # Print results
    print(f"\n{agent1_type.upper()} Stats:")
    print(f"  Wins: {wins[agent1_type]}/{num_games} ({wins[agent1_type]/num_games*100:.1f}%)")
    print(f"  Avg Score: {sum(scores[agent1_type])/len(scores[agent1_type]):.2f}")

    print(f"\n{agent2_type.upper()} Stats:")
    print(f"  Wins: {wins[agent2_type]}/{num_games} ({wins[agent2_type]/num_games*100:.1f}%)")
    print(f"  Avg Score: {sum(scores[agent2_type])/len(scores[agent2_type]):.2f}")

    return wins


def run_tournament(agents_to_test: list, num_games: int = 50):
    """Run a full tournament with all agents"""
    print(f"\n{'='*60}")
    print(f"TOURNAMENT: {num_games} games")
    print(f"{'='*60}")

    num_players = len(agents_to_test)
    sim = GameSimulator(num_players=num_players, verbose=False)

    # Run tournament
    agents = [create_agent(agent_type, i) for i, agent_type in enumerate(agents_to_test)]

    wins = defaultdict(int)
    scores = defaultdict(list)
    rounds_to_finish = defaultdict(list)

    for i in range(num_games):
        # Rotate starting positions
        start_offset = i % len(agents_to_test)
        rotated_types = agents_to_test[start_offset:] + agents_to_test[:start_offset]
        agents = [create_agent(agent_type, i) for i, agent_type in enumerate(rotated_types)]

        result = sim.run_game(agents)

        # Extract winner from name (format: "AgentName (Player N)")
        winner_name = result['final_result']['winner']
        if "(Player " in winner_name:
            winner_id = int(winner_name.split("(Player ")[1].split(")")[0])
        else:
            # Fallback - find by highest score
            final_scores = result['final_result']['final_scores']
            winner_id = max(range(len(final_scores)),
                           key=lambda i: final_scores[f"Player {i}"])

        winner_type = rotated_types[winner_id]
        wins[winner_type] += 1

        # Record scores from final_result
        final_scores = result['final_result']['final_scores']
        for player_num in range(len(rotated_types)):
            player_type = rotated_types[player_num]
            score = final_scores[f"Player {player_num}"]
            scores[player_type].append(score)

    # Print results
    print(f"\nFinal Standings:")
    print(f"{'Agent':<15} {'Wins':<10} {'Win%':<10} {'Avg Score':<12}")
    print("-" * 60)

    # Sort by wins
    sorted_agents = sorted(agents_to_test, key=lambda a: wins[a], reverse=True)

    for agent_type in sorted_agents:
        win_pct = wins[agent_type] / num_games * 100
        avg_score = sum(scores[agent_type]) / len(scores[agent_type]) if scores[agent_type] else 0

        print(f"{agent_type:<15} {wins[agent_type]:<10} {win_pct:<10.1f} {avg_score:<12.2f}")

    return wins


if __name__ == "__main__":
    print("\n" + "="*60)
    print("CLAUDEBOT 2.0 BENCHMARK TEST")
    print("="*60)
    print("\nTesting against top agents from game log analysis:")
    print("  - ChatGPT (66.7% win rate in logs)")
    print("  - ClaudeBot (26.7% win rate in logs)")
    print("  - TobiBot")
    print("  - Gemini")

    # Test 1: Head-to-head vs ChatGPT (current champion)
    print("\n\n### TEST 1: ClaudeBot 2.0 vs ChatGPT ###")
    run_head_to_head('claudebot2', 'chatgpt', num_games=30)

    # Test 2: Head-to-head vs original ClaudeBot
    print("\n\n### TEST 2: ClaudeBot 2.0 vs ClaudeBot 1.0 ###")
    run_head_to_head('claudebot2', 'claudebot', num_games=30)

    # Test 3: Head-to-head vs TobiBot
    print("\n\n### TEST 3: ClaudeBot 2.0 vs TobiBot ###")
    run_head_to_head('claudebot2', 'tobibot', num_games=30)

    # Test 4: Full tournament
    print("\n\n### TEST 4: 4-Player Tournament ###")
    agents = ['claudebot2', 'chatgpt', 'claudebot', 'tobibot']
    run_tournament(agents, num_games=100)

    print("\n\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)
