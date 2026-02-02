"""
Chasse Patate - Example Usage
Demonstrates how to run simulations and analyze results
"""

from simulator import GameSimulator
from analysis import GameAnalyzer
from agents import get_available_agents


def example_single_game():
    """Run a single game with verbose output"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Single Game with Verbose Output")
    print("="*80)
    
    simulator = GameSimulator(num_players=2, track_length=50, verbose=True)
    
    # Run one game with a greedy agent vs balanced agent
    from agents import create_agent
    agents = [
        create_agent('greedy', 0),
        create_agent('balanced', 1)
    ]
    
    game_log = simulator.run_game(agents, game_id=0)
    print(f"\nGame completed in {len(game_log['move_history'])} turns")


def example_batch_simulation():
    """Run multiple games with same configuration"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Batch Simulation")
    print("="*80)
    
    simulator = GameSimulator(num_players=3, track_length=50, verbose=False)
    
    # Run 50 games with 3 different agents
    results = simulator.run_batch_simulation(
        agent_types=['greedy', 'balanced', 'aggressive'],
        num_games=50
    )
    
    # Quick analysis
    winners = [r['winner_id'] for r in results]
    for player_id in range(3):
        wins = winners.count(player_id)
        print(f"Player {player_id} won {wins} games ({wins/len(results)*100:.1f}%)")


def example_tournament():
    """Run a round-robin tournament"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Round-Robin Tournament")
    print("="*80)
    
    simulator = GameSimulator(num_players=2, track_length=50, verbose=False)
    
    # Test these agent types against each other
    agent_types = [
        'random',
        'greedy', 
        'lead_rider',
        'balanced',
        'sprint_hunter'
    ]
    
    # Run tournament with 10 games per matchup
    tournament_results = simulator.run_tournament(
        agent_types=agent_types,
        games_per_matchup=10
    )
    
    print("\nTournament Results Summary:")
    for matchup in tournament_results['matchups']:
        print(f"\n{matchup['agent1_type']} vs {matchup['agent2_type']}:")
        print(f"  {matchup['agent1_type']}: {matchup['agent1_wins']} wins, "
              f"avg score: {matchup['agent1_total_score']/matchup['games_played']:.1f}")
        print(f"  {matchup['agent2_type']}: {matchup['agent2_wins']} wins, "
              f"avg score: {matchup['agent2_total_score']/matchup['games_played']:.1f}")


def example_full_analysis():
    """Run simulations and perform complete analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Full Simulation & Analysis")
    print("="*80)
    
    # Run a large batch of games
    simulator = GameSimulator(num_players=2, track_length=50, verbose=False)
    
    print("\nRunning 100 games for analysis...")
    results = simulator.run_batch_simulation(
        agent_types=['greedy', 'adaptive'],
        num_games=100
    )
    
    # Analyze results
    analyzer = GameAnalyzer(log_dir="game_logs")
    logs = analyzer.load_game_logs()
    
    print(f"\nAnalyzing {len(logs)} games...")
    
    # Generate comprehensive report
    report_path = analyzer.generate_report(logs)
    print(f"\nReport saved to: {report_path}")
    
    # Create visualizations
    try:
        plot_path = analyzer.plot_win_rates(logs)
        print(f"Win rate plot saved to: {plot_path}")
    except Exception as e:
        print(f"Could not create plot: {e}")


def example_test_specific_matchup():
    """Test a specific agent matchup extensively"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Testing Specific Matchup")
    print("="*80)
    
    simulator = GameSimulator(num_players=2, track_length=50, verbose=False)
    
    # Test if aggressive strategy dominates
    print("\nTesting: Aggressive vs Conservative (100 games)")
    results = simulator.run_batch_simulation(
        agent_types=['aggressive', 'conservative'],
        num_games=100
    )
    
    # Quick stats
    aggressive_wins = sum(1 for r in results if r['winner_id'] == 0)
    conservative_wins = sum(1 for r in results if r['winner_id'] == 1)
    avg_aggressive_score = sum(r['scores'][0] for r in results) / len(results)
    avg_conservative_score = sum(r['scores'][1] for r in results) / len(results)
    
    print(f"\nResults:")
    print(f"  Aggressive: {aggressive_wins} wins ({aggressive_wins/len(results)*100:.1f}%), "
          f"avg score: {avg_aggressive_score:.1f}")
    print(f"  Conservative: {conservative_wins} wins ({conservative_wins/len(results)*100:.1f}%), "
          f"avg score: {avg_conservative_score:.1f}")
    
    if abs(aggressive_wins - conservative_wins) > 20:
        print("\n⚠️  WARNING: Significant imbalance detected!")
    else:
        print("\n✓ Strategies appear balanced")


def show_available_agents():
    """Display all available agent types"""
    print("\n" + "="*80)
    print("AVAILABLE AGENT TYPES")
    print("="*80)
    
    agents = get_available_agents()
    for agent in agents:
        print(f"  - {agent}")
    print()


def main():
    """Run all examples"""
    
    print("\n" + "="*80)
    print("CHASSE PATATE - GAME SIMULATOR")
    print("Testing game balance through AI simulations")
    print("="*80)
    
    show_available_agents()
    
    # Run examples (comment out ones you don't want)
    
    # Quick examples
    # example_single_game()
    # example_batch_simulation()
    
    # More comprehensive examples
    example_tournament()
    # example_full_analysis()
    # example_test_specific_matchup()
    
    print("\n" + "="*80)
    print("All examples complete!")
    print("Check the 'game_logs' directory for detailed results")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
