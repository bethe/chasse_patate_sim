"""
Quick Balance Test
Run this to quickly test for obvious balance issues
"""

from simulator import GameSimulator
from analysis import GameAnalyzer
from agents import get_available_agents

def quick_balance_test():
    """Run a quick balance test with default agents"""
    
    print("\n" + "="*80)
    print("QUICK BALANCE TEST")
    print("="*80)
    print("\nThis will run 50 games between different agent types")
    print("and identify any obvious balance issues.\n")
    
    # Test 2-player games
    print("Testing 2-player games...")
    simulator = GameSimulator(num_players=2, verbose=False)
    
    # Test most common strategies
    test_agents = ['random', 'greedy', 'balanced', 'aggressive', 'adaptive']
    
    print(f"\nRunning tournament with agents: {test_agents}")
    tournament_results = simulator.run_tournament(
        agent_types=test_agents,
        games_per_matchup=10
    )
    
    # Analyze results
    print("\nAnalyzing results...")
    analyzer = GameAnalyzer(log_dir="game_logs")
    logs = analyzer.load_game_logs()
    
    # Check win rates
    win_rates = analyzer.analyze_win_rates(logs)
    print("\n" + "-"*80)
    print("WIN RATES")
    print("-"*80)
    print(win_rates.to_string())
    
    # Check for dominant strategies
    dominant = analyzer.detect_dominant_strategies(logs, significance_threshold=0.15)
    
    print("\n" + "-"*80)
    print("BALANCE ASSESSMENT")
    print("-"*80)
    
    if dominant:
        print("\n⚠️  WARNING: Potential balance issues detected!\n")
        for strat in dominant:
            print(f"{strat['agent']}:")
            print(f"  Win rate: {strat['win_rate']:.1%} (expected: {strat['expected']:.1%})")
            print(f"  Advantage: +{strat['advantage']:.1%}")
            print()
        print("These strategies may be too strong. Consider adjusting:")
        print("  - Card values for terrain types")
        print("  - Sprint point values")
        print("  - Slipstream mechanics")
        print("  - Track composition")
    else:
        print("\n✓ No obvious dominant strategies detected!")
        print("\nGame appears reasonably balanced based on this quick test.")
        print("For more thorough testing, run larger simulations (100+ games).")
    
    # Check game length
    length_stats = analyzer.analyze_game_length(logs)
    print("\n" + "-"*80)
    print("GAME LENGTH")
    print("-"*80)
    print(f"Average turns: {length_stats['mean_turns']:.1f}")
    print(f"Range: {length_stats['min_turns']}-{length_stats['max_turns']} turns")
    
    if length_stats['mean_turns'] < 10:
        print("\n⚠️  Games are very short - consider longer track or adjust card values")
    elif length_stats['mean_turns'] > 50:
        print("\n⚠️  Games are very long - consider shorter track or increase movement")
    else:
        print("\n✓ Game length seems reasonable")
    
    # Check score distribution
    scores = analyzer.analyze_score_distribution(logs)
    print("\n" + "-"*80)
    print("SCORES")
    print("-"*80)
    print(f"Average score: {scores['mean_score']:.1f}")
    print(f"Average winning score: {scores['mean_winning_score']:.1f}")
    print(f"Score range: {scores['score_range'][0]}-{scores['score_range'][1]}")
    
    score_spread = scores['score_range'][1] - scores['score_range'][0]
    if score_spread > 50:
        print(f"\n⚠️  Large score spread ({score_spread} points) - high variance in outcomes")
    else:
        print("\n✓ Score distribution looks reasonable")
    
    print("\n" + "="*80)
    print("QUICK TEST COMPLETE")
    print("="*80)
    print(f"\nDetailed logs saved to: {simulator.logger.log_dir}")
    print("For comprehensive analysis, run: analyzer.generate_report(logs)")
    print("="*80 + "\n")


if __name__ == "__main__":
    quick_balance_test()
