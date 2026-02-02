# Chasse Patate - Game Balance Simulator

A comprehensive simulation framework for testing and balancing the Chasse Patate cycling board game through AI agent play.

## Overview

This simulator allows you to:
- Run thousands of simulated games with different AI strategies
- Track detailed statistics: moves, scores, card usage, positions
- Identify dominant strategies and balance issues
- Compare different agent behaviors head-to-head
- Generate comprehensive analysis reports

## Project Structure

```
.
├── game_state.py      # Core game state and data structures
├── game_engine.py     # Game rules and move validation
├── agents.py          # AI agent implementations
├── simulator.py       # Game simulation and logging
├── analysis.py        # Statistical analysis tools
├── example_usage.py   # Example scripts
├── requirements.txt   # Python dependencies
└── game_logs/         # Generated game logs (created automatically)
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run Your First Simulation

```python
python example_usage.py
```

This will run a tournament between different agent types and generate analysis reports.

## Available AI Agents

The simulator includes 11 different AI agent types:

1. **random** - Plays randomly (baseline)
2. **greedy** - Always moves for maximum distance
3. **lead_rider** - Focuses on advancing the leading rider
4. **balanced** - Keeps all three riders advancing together
5. **sprint_hunter** - Prioritizes sprint points
6. **conservative** - Avoids slipstreaming (exhaustion)
7. **aggressive** - Uses slipstreaming frequently
8. **adaptive** - Adjusts strategy based on terrain ahead
9. **rouleur_focus** - Prefers playing Rouleur cards
10. **sprinteur_focus** - Prefers playing Sprinteur cards
11. **grimpeur_focus** - Prefers playing Grimpeur cards

## Usage Examples

### 1. Run a Single Game (with verbose output)

```python
from simulator import GameSimulator
from agents import create_agent

simulator = GameSimulator(num_players=2, track_length=50, verbose=True)

agents = [
    create_agent('greedy', 0),
    create_agent('balanced', 1)
]

game_log = simulator.run_game(agents, game_id=0)
```

### 2. Run a Batch of Games

```python
simulator = GameSimulator(num_players=3, track_length=50)

results = simulator.run_batch_simulation(
    agent_types=['greedy', 'balanced', 'aggressive'],
    num_games=100
)
```

### 3. Run a Tournament

```python
simulator = GameSimulator(num_players=2, track_length=50)

tournament_results = simulator.run_tournament(
    agent_types=['random', 'greedy', 'lead_rider', 'balanced', 'sprint_hunter'],
    games_per_matchup=20
)
```

### 4. Analyze Results

```python
from analysis import GameAnalyzer

analyzer = GameAnalyzer(log_dir="game_logs")
logs = analyzer.load_game_logs()

# Generate comprehensive report
analyzer.generate_report(logs)

# Create visualizations
analyzer.plot_win_rates(logs)

# Check for dominant strategies
dominant = analyzer.detect_dominant_strategies(logs, significance_threshold=0.15)
```

## Game Logs

All games are logged in detail as JSON files in the `game_logs/` directory:

- `game_0.json`, `game_1.json`, etc. - Individual game logs
- `tournament_results.csv` - Tournament matchup results
- `batch_results.csv` - Batch simulation results
- `analysis_report.txt` - Generated analysis report

### Game Log Structure

Each game log contains:
- Game metadata (ID, timestamp, players)
- Move-by-move history
- Game state after each turn
- Final scores and winner

Example:
```json
{
  "game_id": 0,
  "timestamp": "2024-01-01T12:00:00",
  "num_players": 2,
  "agents": [
    {"player_id": 0, "type": "Greedy"},
    {"player_id": 1, "type": "Balanced"}
  ],
  "move_history": [
    {
      "turn": 0,
      "player": 0,
      "move": {
        "rider": "P0R0",
        "old_position": 0,
        "new_position": 7,
        "card_played": "Rouleur",
        "used_slipstream": false,
        "points_earned": 0
      },
      "state": {
        "player_scores": [0, 0],
        "player_hand_sizes": [5, 5],
        "rider_positions": {...}
      }
    }
  ],
  "final_result": {
    "winner": "Player 0",
    "winner_score": 25,
    "final_scores": {"Player 0": 25, "Player 1": 18}
  }
}
```

## Analysis Metrics

The analyzer tracks:

### Win Rates
- Win percentage by agent type
- Average finishing position
- Average score

### Game Statistics
- Game length (number of turns)
- Score distribution
- Winning score patterns

### Strategic Patterns
- Card usage frequency (Rouleur, Sprinteur, Grimpeur)
- Slipstream usage rates
- Sprint point capture rates

### Balance Detection
- Identifies agents with win rates significantly above expected
- Flags potential dominant strategies
- Highlights imbalanced mechanics

## Customization

### Create a Custom Agent

```python
from agents import Agent
from game_engine import GameEngine, Move

class CustomAgent(Agent):
    def __init__(self, player_id: int):
        super().__init__(player_id, "Custom")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
        
        # Your custom logic here
        return some_move
```

### Adjust Game Parameters

```python
simulator = GameSimulator(
    num_players=4,        # 2-5 players
    track_length=60,      # Longer/shorter race
    log_dir="my_logs",    # Custom log directory
    verbose=True          # Enable detailed output
)
```

### Custom Track Configuration

Edit the `_create_track()` method in `game_state.py` to create custom track layouts with different terrain distributions.

## Interpreting Results

### Balanced Game Indicators
- Win rates within ±10% of expected (50% for 2 players, 33% for 3, etc.)
- Similar average scores across strategies
- Multiple viable strategies
- Game length consistency

### Warning Signs
- One agent type wins >60% of games
- Average scores differ by >30%
- Games consistently end very quickly or very slowly
- One card type dominates usage

## Tips for Game Balancing

1. **Run large samples** - Use at least 100 games per matchup for statistical significance
2. **Test multiple player counts** - Balance may differ with 2, 3, 4, or 5 players
3. **Vary track configurations** - Test different terrain distributions
4. **Compare extreme strategies** - Conservative vs Aggressive, Sprint vs Distance focus
5. **Look for "no-brainer" plays** - If one strategy always dominates, adjust rules

## Advanced Usage

### Test Rule Variants

You can modify the game rules in `game_engine.py` and `game_state.py` to test variants:

```python
# Example: Test with different slipstream rules
# Modify _get_slipstream_moves() in game_engine.py

# Example: Test with different card distributions
# Modify CARD_DISTRIBUTION in game_state.py
```

Run simulations before and after to compare balance.

### Analyze Specific Scenarios

```python
# Load specific games
analyzer = GameAnalyzer()
logs = analyzer.load_game_logs(game_ids=[5, 10, 15, 20])

# Focus on specific metrics
slipstream_stats = analyzer.analyze_slipstream_usage(logs)
card_stats = analyzer.analyze_card_usage(logs)
```

## Performance Notes

- Single game: ~0.1-0.5 seconds
- 100 games: ~10-50 seconds
- 1000 games: ~2-8 minutes
- Tournament (5 agents, 20 games each): ~3-5 minutes

Times vary based on player count and track length.

## Troubleshooting

### No valid moves / Game stuck
- Check track configuration
- Verify card movement values match terrain
- Ensure riders aren't blocked

### Memory issues with large simulations
- Process games in batches
- Clear log files between runs
- Reduce logging verbosity

### Unexpected results
- Verify agent logic in `agents.py`
- Check move validation in `game_engine.py`
- Review game logs for specific turns

## Contributing

To add new features:
1. New agent types: Add to `agents.py`
2. New analysis metrics: Add to `analysis.py`
3. Rule modifications: Edit `game_engine.py`
4. Track variants: Edit `game_state.py`

## License

This simulator is provided as-is for game development and testing purposes.
