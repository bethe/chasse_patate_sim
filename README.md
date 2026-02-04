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
# Chasse Patate - Game Balance Simulator

A comprehensive simulation framework for testing and balancing the Chasse Patate cycling board game through AI agent play.

## Overview

This simulator allows you to:
- Run thousands of simulated games with different AI strategies
- Track detailed statistics: moves, scores, card usage, positions, game over reasons
- Identify dominant strategies and balance issues
- Compare different agent behaviors head-to-head
- Generate comprehensive analysis reports
- Test game mechanics like drafting, team actions, and sprint scoring

## Project Structure

```
.
├── game_state.py          # Core game state and data structures
├── game_engine.py         # Game rules and move validation
├── agents.py              # AI agent implementations
├── simulator.py           # Game simulation and logging
├── analysis.py            # Statistical analysis tools
├── quick_test.py          # Fast balance testing script
├── example_usage.py       # Example scripts and tutorials
├── generate_report.py     # Standalone report generation
├── requirements.txt       # Python dependencies
└── game_logs/             # Generated game logs (created automatically)
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run a Quick Balance Test

```bash
python quick_test.py
```

This runs 50 games and shows:
- Win rates by agent
- Score distribution
- Action usage statistics
- Game over reasons

### Generate Comprehensive Report

```bash
python generate_report.py
```

Creates `game_logs/analysis_report.txt` with detailed statistics.

## Available AI Agents

The simulator includes 12 different AI agent types:

1. **random** - Plays randomly (baseline)
2. **greedy** - Maximizes total advancement (distance × riders moved)
3. **lead_rider** - Focuses on advancing the leading rider
4. **balanced** - Keeps all three riders advancing together
5. **sprint_hunter** - Prioritizes sprint points
6. **conservative** - Rarely uses TeamCar
7. **aggressive** - Uses TeamCar frequently
8. **adaptive** - Adjusts strategy based on terrain ahead
9. **wheelsucker** - Prioritizes drafting off other riders
10. **rouleur_focus** - Prefers playing Rouleur cards
11. **sprinter_focus** - Prefers playing Sprinter cards
12. **climber_focus** - Prefers playing Climber cards

## Game Actions

Players can choose from 6 action types:

### 1. **Pull** (1-3 cards)
- Advance a single rider
- Movement based on cards and terrain
- Most common advancing move

### 2. **Attack** (exactly 3 cards)
- Advance a single rider with a burst
- Requires at least one matching rider card
- Higher movement bonus

### 3. **Draft**
- Free movement following another player's Pull/Draft/TeamPull/TeamDraft
- Must start from same position as previous move
- No cards required

### 4. **TeamPull**
- One rider Pulls, teammates at same position Draft
- Player chooses which teammates follow
- Powerful for grouped riders

### 5. **TeamDraft**
- Multiple riders Draft together
- Must be at position where opponent just moved from
- Efficient team movement

### 6. **TeamCar**
- Draw 2 cards, discard 1
- Used when hand is low (<3 cards)
- Only if no Draft/TeamDraft available

## Game Mechanics

### Checkpoints
- Every 10 fields (10, 20, 30, ...)
- Each rider crossing draws 3 cards
- In team moves, EACH rider crossing gets 3 cards

### Sprint Points
- Intermediate sprints (last field of non-final tiles): 3/2/1 points
- Final sprint (finish line): 12/8/5/3/1 points
- Points awarded by arrival order

### Track Configuration
- Default: 3 tiles × 20 fields = 60 positions
- Each tile: 14 Flat + 5 Climb + 1 Sprint
- Configurable terrain distribution

### Game End Conditions
1. **5 riders finished** - 5+ riders crossed finish line
2. **Turn limit reached** - 150 turns completed
3. **Players out of cards** - Deck empty, all hands empty

## Usage Examples

### 1. Run a Single Game (with verbose output)

```python
from simulator import GameSimulator
from agents import create_agent

simulator = GameSimulator(num_players=2, verbose=True)

agents = [
    create_agent('greedy', 0),
    create_agent('wheelsucker', 1)
]

game_log = simulator.run_game(agents, game_id=0)
```

### 2. Run a Batch of Games

```python
simulator = GameSimulator(num_players=2)

results = simulator.run_batch_simulation(
    agent_types=['greedy', 'balanced'],
    num_games=100
)

# Results include win counts and matchup statistics
```

### 3. Run a Tournament

```python
simulator = GameSimulator(num_players=2)

tournament_results = simulator.run_tournament(
    agent_types=['greedy', 'balanced', 'wheelsucker', 'sprint_hunter'],
    games_per_matchup=20
)
```

### 4. Analyze Results

```python
from analysis import GameAnalyzer

analyzer = GameAnalyzer(log_dir="game_logs")
logs = analyzer.load_game_logs()

# Generate comprehensive report
report_path = analyzer.generate_report(logs)

# Analyze specific aspects
win_rates = analyzer.analyze_win_rates(logs)
action_usage = analyzer.analyze_action_usage(logs)
game_over_reasons = analyzer.analyze_game_over_reasons(logs)
```

## Game Logs

All games are logged in detail as JSON files in the `game_logs/` directory:

- `game_0.json`, `game_1.json`, etc. - Individual game logs
- `analysis_report.txt` - Comprehensive analysis report

### Game Log Structure

Each game log contains:
- Game metadata (ID, timestamp, players, agents)
- Move-by-move history with full state
- Action details (Pull, Attack, Draft, TeamPull, TeamDraft, TeamCar)
- Checkpoint tracking and card drawing
- Sprint point awards
- Game over reason
- Final scores and winner

Example move entry:
```json
{
  "turn": 5,
  "player": 1,
  "move": {
    "success": true,
    "action": "TeamPull",
    "rider": "P1R0",
    "old_position": 7,
    "new_position": 11,
    "cards_played": ["Energy", "Energy", "Rouleur"],
    "movement": 4,
    "drafting_riders": [
      {"rider": "P1R1", "old_position": 7, "new_position": 11},
      {"rider": "P1R2", "old_position": 7, "new_position": 11}
    ],
    "checkpoints_reached": [10],
    "cards_drawn": 9,
    "points_earned": 0
  }
}
```

## Analysis Report Contents

The generated report includes:

### 1. Win Rates by Agent Type
- Games played
- Wins
- Win rate
- Average score
- Average finishing position

### 2. Game Length Statistics
- Mean, median, min, max turns
- Standard deviation

### 3. Game Over Reasons
- Turn limit reached
- 5 riders finished
- Players out of cards
- Percentages for each reason

### 4. Card Usage Statistics
- Times played for each card type
- Usage rates

### 5. Action Usage Statistics
- Pull, Attack, Draft, TeamPull, TeamDraft, TeamCar
- Count and percentage for each action

### 6. Score Distribution
- Mean, median, standard deviation
- Winning score patterns

### 7. Dominant Strategy Detection
- Flags agents with win rates >15% above expected
- Identifies balance issues

## Customization

### Create a Custom Agent

```python
from agents import Agent
from game_engine import GameEngine, Move
from game_state import Player, ActionType
from typing import Optional

class CustomAgent(Agent):
    def __init__(self, player_id: int):
        super().__init__(player_id, "Custom")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
        
        # Your custom logic here
        # Examples:
        # - Prioritize certain action types
        # - Consider rider positions
        # - Evaluate terrain ahead
        # - Manage hand size strategically
        
        return your_chosen_move

# Register in agents.py factory
```

### Adjust Game Parameters

```python
from game_state import DEFAULT_RACE_CONFIG

simulator = GameSimulator(
    num_players=2,              # 2-5 players
    tile_config=[1, 2, 3],      # Tile types (see game_state.py)
    verbose=True,               # Enable detailed output
    max_turns=200               # Adjust turn limit
)
```

### Custom Track Configuration

Create custom tile configurations in `game_state.py`:

```python
CUSTOM_CONFIG = [1, 2, 2, 3]  # Mixed terrain race
simulator = GameSimulator(num_players=2, tile_config=CUSTOM_CONFIG)
```

## Interpreting Results

### Balanced Game Indicators
- Win rates within ±10% of expected (50% for 2 players, 33% for 3, etc.)
- Similar average scores across strategies
- Multiple viable strategies
- <50% games hitting turn limit
- Diverse action usage

### Warning Signs
- One agent type wins >60% of games
- Average scores differ by >30%
- >90% games hit turn limit (games too slow)
- One action dominates >70% (e.g., all TeamCar)
- Average scores <5 (insufficient sprint opportunities)

## Tips for Game Balancing

1. **Run large samples** - Use at least 50 games per matchup for statistical significance
2. **Test multiple player counts** - Balance may differ with 2-5 players
3. **Monitor game over reasons** - Too many turn limits = games too slow
4. **Check action diversity** - Healthy games use multiple action types
5. **Evaluate agent performance** - Wheelsucker should differ from Greedy
6. **Test checkpoint impact** - Multiple riders crossing = huge card advantage
7. **Verify sprint scoring** - Early arrival = more points

## Advanced Features

### Testing Specific Scenarios

```python
# Test checkpoint crossing with team moves
game = GameState(num_players=2)
engine = GameEngine(game)

# Position riders just before checkpoint
for rider in game.players[0].riders:
    rider.position = 7

# Execute TeamPull crossing checkpoint 10
# Expect 9 cards drawn (3 riders × 3 cards each)
```

### Analyze Draft Chaining

```python
# Draft chains occur when multiple players draft in sequence
# Monitor in game logs: Pull → Draft → Draft → Draft
# Efficient movement without card usage
```

### Compare Agent Strategies

```python
# Run head-to-head matchups
simulator.run_batch_simulation(
    agent_types=['greedy', 'wheelsucker'],
    num_games=100
)

# Greedy: Aggressive, high total advancement
# Wheelsucker: Conservative, drafts frequently
```

## Performance Notes

- Single game: ~0.1-1 second
- 50 games: ~5-30 seconds
- 100 games: ~10-60 seconds
- Tournament (4 agents, 20 games each): ~2-5 minutes

Times vary based on:
- Player count (2-5)
- Agent complexity
- Game length (turn limit)
- Logging verbosity

## Troubleshooting

### Games hitting turn limit frequently
- Lower TeamCar threshold in agents (currently <3)
- Increase turn limit from 150 to 200+
- Check if drafting is working (should see Draft/TeamDraft actions)

### Unexpected win rates
- Verify agent logic in `agents.py`
- Check move validation in `game_engine.py`
- Review game logs for specific turns
- Run more games for statistical significance

### Checkpoint cards not awarded
- Fixed in latest version - all riders crossing get 3 cards each
- Verify `checkpoints_reached` and `cards_drawn` in logs

### Memory issues with large simulations
- Process games in smaller batches
- Clear log files between runs
- Use `quick_test.py` for rapid testing

## Recent Updates

### Latest Changes
- ✅ Added Draft, TeamPull, TeamDraft actions
- ✅ Fixed checkpoint card drawing for team moves (all riders get cards)
- ✅ Added Wheelsucker agent (drafting specialist)
- ✅ Updated Greedy agent (maximizes total advancement)
- ✅ Fixed win rate calculation in analysis
- ✅ Added action usage statistics to reports
- ✅ Added game over reason tracking
- ✅ Agents now prioritize Draft/TeamDraft over TeamCar when hand low

## Quick Reference Scripts

### Fast Balance Check
```bash
python quick_test.py
```

### Comprehensive Analysis
```bash
python generate_report.py
```

### Learning Examples
```bash
python example_usage.py
```

## Contributing

To add new features:
1. **New agent types**: Add to `agents.py` and factory function
2. **New analysis metrics**: Add methods to `analysis.py`
3. **Rule modifications**: Edit `game_engine.py`
4. **Track variants**: Edit tile configurations in `game_state.py`
5. **New actions**: Add to ActionType enum and implement in engine

## License

This simulator is provided as-is for game development and testing purposes.