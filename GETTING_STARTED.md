# Getting Started with Chasse Patate Simulator

## Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install pandas numpy matplotlib
```

### 2. Run Your First Test
```bash
python quick_test.py
```

This will:
- Run 150 games with 5 different agent types
- Identify any obvious balance issues
- Generate detailed logs in `game_logs/` folder

### 3. Review Results

The quick test will show you:
- **Win rates** for each strategy
- **Dominant strategies** (if any)
- **Game length** statistics
- **Score distributions**

### 4. Deep Dive Analysis

For more detailed analysis:

```python
from analysis import GameAnalyzer

analyzer = GameAnalyzer(log_dir="game_logs")
logs = analyzer.load_game_logs()
analyzer.generate_report(logs)
```

This creates a comprehensive text report: `game_logs/analysis_report.txt`

## Common Workflows

### Testing a Specific Rule Change

1. **Modify the rules** in `game_engine.py` or `game_state.py`
2. **Run simulations** before and after the change
3. **Compare results** to see the impact

Example:
```python
from simulator import GameSimulator

# Before rule change
simulator = GameSimulator(num_players=2)
results_before = simulator.run_batch_simulation(
    agent_types=['greedy', 'balanced'],
    num_games=100
)

# (Make your rule change here)

# After rule change  
results_after = simulator.run_batch_simulation(
    agent_types=['greedy', 'balanced'],
    num_games=100
)

# Compare win rates, scores, etc.
```

### Finding Dominant Strategies

Run a tournament with all agent types:

```python
from simulator import GameSimulator
from agents import get_available_agents

simulator = GameSimulator(num_players=2)
all_agents = get_available_agents()

results = simulator.run_tournament(
    agent_types=all_agents,
    games_per_matchup=20
)
```

Check `game_logs/tournament_results.csv` for matchup statistics.

### Testing Different Player Counts

```python
for num_players in [2, 3, 4, 5]:
    print(f"\nTesting with {num_players} players...")
    
    simulator = GameSimulator(num_players=num_players)
    results = simulator.run_batch_simulation(
        agent_types=['greedy'] * num_players,
        num_games=50
    )
    
    # Analyze results...
```

### Custom Track Testing

Modify `_create_track()` in `game_state.py` to test different track layouts:

```python
# Example: More mountain-heavy track
def _create_track(self):
    track = []
    
    # 30% mountains instead of 20%
    for i in range(self.track_length):
        if i < 10:
            terrain = TerrainType.FLAT
        elif i < 30:
            terrain = TerrainType.MOUNTAIN
        else:
            terrain = TerrainType.HILL
        
        track.append(TrackTile(i, terrain))
    
    return track
```

## Understanding the Logs

### Game Log Structure

Each `game_X.json` contains:

```json
{
  "game_id": 0,
  "agents": [...],           // Agent types
  "move_history": [          // Every move
    {
      "turn": 0,
      "player": 0,
      "move": {
        "rider": "P0R0",     // Player 0, Rider 0
        "new_position": 7,
        "card_played": "Rouleur",
        "used_slipstream": false,
        "points_earned": 0
      },
      "state": {             // Game state after move
        "player_scores": [0, 0],
        "rider_positions": {...}
      }
    }
  ],
  "final_result": {...}      // Winner and final scores
}
```

### CSV Summaries

- **tournament_results.csv** - Head-to-head matchup results
- **batch_results.csv** - Summary of each game in batch

## Tips for Finding Balance Issues

### 1. Look for Extreme Win Rates

If one agent consistently wins >60% of games:
- That strategy might be too strong
- OR other strategies might be too weak
- OR the game rewards that playstyle too much

### 2. Check Score Variance

High variance = more luck-dependent
Low variance = more skill-dependent

Adjust based on your design goals.

### 3. Test Edge Cases

- All players use same strategy - does first player advantage dominate?
- Aggressive vs Conservative - is there a clear winner?
- Card-focused strategies - does one card type dominate?

### 4. Watch Game Length

Games too short? Players might be racing too fast.
Games too long? Movement might be too slow.

Aim for 15-30 turns for a good paced game.

### 5. Analyze Card Usage

If one card type is rarely used, it might be:
- Too weak
- Too situational
- Made obsolete by other cards

## Next Steps

1. **Run quick_test.py** to get baseline
2. **Identify any issues** from the report
3. **Make rule adjustments** in game files
4. **Run tests again** to verify improvements
5. **Iterate** until balanced

## Need Help?

Check the full README.md for:
- Complete API documentation
- Custom agent creation
- Advanced analysis techniques
- Troubleshooting guide

Happy balancing!
