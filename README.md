# Chasse Patate - Cycling Board Game Simulator

A simulation framework for testing and balancing the Chasse Patate cycling board game through AI agent play. Also supports interactive human-vs-bot play.

## Overview

This simulator allows you to:
- Run thousands of simulated games with different AI strategies
- Track detailed statistics: moves, scores, card usage, positions
- Identify dominant strategies and balance issues
- Compare different agent behaviors head-to-head
- Generate comprehensive analysis reports
- Play interactively against AI bots

## Project Structure

```
.
├── game_state.py          # Core game state, cards, El Patron rule
├── game_engine.py         # Game rules, move validation, terrain limits
├── game_config.py         # Configuration system and CLI management
├── agents.py              # AI agent implementations (8 types)
├── simulator.py           # Game simulation and logging
├── analysis.py            # Statistical analysis tools
├── play.py                # Interactive play mode
├── game_analyzer.py       # Replay games from logs with visualization
├── quick_test.py          # Fast balance testing script
├── run_tournament.py      # Multi-player tournament runner (2/3/4 players)
├── test_game_rules.py     # Comprehensive unit tests (80+ tests)
├── config.json            # Game configuration file
└── game_logs/             # Generated game logs (created automatically)
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Interactive Play

```bash
python play.py
```

Play against AI bots interactively. Choose number of players (2-5) and assign human or bot to each slot. Press `r` during play to view the card reference table, and `b` to go back to a previous decision.

### Run a Quick Balance Test

```bash
python quick_test.py
```

Runs 50 games and shows win rates, score distribution, action usage, and game over reasons.

### Replay Games from Logs

```bash
python game_analyzer.py              # List available logs
python game_analyzer.py game_0.json  # Replay with turn-by-turn pauses
python game_analyzer.py game_0.json --no-pause  # Fast replay
```

### Run Comprehensive Tournament

```bash
python run_tournament.py
```

Tests all agent combinations across 2, 3, and 4 players (~250 games). Alternates player positions to minimize position bias. Outputs win rates, head-to-head matrix, position bias analysis, and CSV export.

### Run Tests

```bash
python test_game_rules.py
```

Runs 80+ unit tests covering all game mechanics, agents, and tournament features.

## Configuration

The game is configured through `config.json`, which all scripts load automatically.

```bash
python game_config.py show       # View current config
python game_config.py validate   # Validate config.json
python game_config.py reset      # Reset to defaults
python game_config.py preset quick       # Presets: quick, marathon, mountain, cobbles
```

### Tile Configuration

Choose which race tiles to use and in what order (each tile is 20 fields):

```json
{ "tile_config": [1, 5, 4] }
```

| Tile | Name | Terrain |
|------|------|---------|
| 1 | Flat | All flat |
| 2 | Mountaintop Finish | Flat start, long climb |
| 3 | Champs Elysees | Flat + cobbles |
| 4 | Up and Down | Climb + descent |
| 5 | Paris-Roubaix | Mixed cobbles sections |

### Starting Hand

Customize cards each player receives at game start (default: 9 cards):

```json
{
  "starting_hand": {
    "energy_cards": 3,
    "rouleur_cards": 1,
    "sprinter_cards": 1,
    "climber_cards": 1,
    "random_cards": 3
  }
}
```

### Checkpoint Card Draws

Configure cards drawn when riders cross checkpoints (every 10 fields):

```json
{
  "checkpoints": {
    "mid_tile_checkpoint": 3,
    "new_tile_checkpoint": 3
  }
}
```

- **mid_tile_checkpoint**: Fields 10, 30, 50... (middle of each tile)
- **new_tile_checkpoint**: Fields 20, 40, 60... (tile boundaries)

### Programmatic Configuration

```python
from game_config import GameConfig, ConfigLoader
from game_state import GameState

# Auto-load from config.json
state = GameState(num_players=2)

# Load from custom path
config = ConfigLoader.load("my_config.json")
state = GameState(num_players=2, config=config)
```

## Game Rules

### Riders

Each player has 3 riders:
- **Rouleur** - Balanced all-terrain rider
- **Sprinter** - Fast on flat, weak on climbs
- **Climber** - Excels on climbs, limited on cobbles

### Terrain Types

- **Flat** - Standard terrain
- **Climb** - Mountains (Sprinters/Rouleurs limited)
- **Cobbles** - Rough terrain (Climbers limited)
- **Descent** - Downhill (all riders fast)
- **Sprint** - Intermediate sprint points
- **Finish** - Final sprint points

### Terrain Limits

Riders have maximum fields per round on certain terrain:

| Rider    | Terrain  | Max Fields |
|----------|----------|------------|
| Sprinter | Climb    | 3          |
| Rouleur  | Climb    | 4          |
| Climber  | Cobbles  | 3          |

Limits apply only to the portion of movement on limited terrain. In team moves, each rider applies their own limits individually.

### El Patron Rule

- El Patron rotates each round (Player 0 -> 1 -> 2 -> ...)
- Determines turn order when riders are tied at the same position
- El Patron player goes first among tied players

### Turn Order

1. Riders move in order of position (leaders first)
2. When tied, El Patron order determines who moves first
3. All riders must move once before a new round begins

### Actions

| Action     | Cards | Description                                    |
|------------|-------|------------------------------------------------|
| Pull       | 1-3   | Advance a single rider                         |
| Attack     | 3     | Aggressive advance (requires 1+ rider card)    |
| Draft      | 0     | Follow previous move (free movement)           |
| TeamPull   | 1-3   | One rider pulls, teammates draft               |
| TeamDraft  | 0     | Multiple riders draft together                 |
| TeamCar    | 0     | Draw 2 cards, discard 1                        |

### Drafting Rules

- Can draft after Pull, Draft, TeamPull, or TeamDraft
- Must be at the same position the previous move started from
- Same player's different riders CAN draft each other
- A rider cannot draft from its own previous move

### Scoring

- **Intermediate Sprints** (end of each tile): 3/2/1 points for 1st/2nd/3rd
- **Finish Line**: 12/8/5/3/1 points for top 5 finishers
- Points awarded by arrival order

### Game End Conditions

1. **5 riders finished** - 5+ riders crossed finish line
2. **Team finished** - One player has all 3 riders at finish
3. **Player stuck** - Any player has 0 total advancement over 5 consecutive rounds
4. **Out of cards** - Deck empty and all hands empty

## Available AI Agents

8 AI agent types:

| Agent          | Strategy                                      |
|----------------|-----------------------------------------------|
| random         | Plays randomly (baseline)                     |
| marc_soler     | Simple strategy using worst cards first       |
| wheelsucker    | Prioritizes drafting opportunities            |
| **gemini**     | Balanced scoring: advancement + points + efficiency |
| **chatgpt**    | Balanced agent valuing steady advancement and card efficiency |
| **claudebot**  | Multi-factor: terrain awareness, sprint targeting, card economy |
| **claudebot2** | Enhanced multi-factor scoring with improved terrain awareness |
| **tobibot**    | Prioritized strategy: scoring, hand management, efficient moves, grouping |

### Featured Agents

**ClaudeBot** - Multi-factor scoring considering terrain-aware movement, sprint/finish targeting, card economy, drafting efficiency, and rider specialization.

**ClaudeBot2** - Enhanced multi-factor scoring with improved terrain awareness and strategic depth.

**GeminiBot** - Balanced scoring system weighing total advancement, sprint/finish points potential, card efficiency, checkpoint card drawing, and hand management.

**TobiBot** - Prioritized decision-making:
1. Score points at sprints/finish when possible
2. Hand management: TeamCar when ≤6 cards unless efficient move available
3. Prefer efficient moves: TeamDraft > Draft > TeamPull
4. Advance to fields with team riders ahead
5. When El Patron, position with opponent riders
6. Maximize team advancement respecting terrain limits
7. TeamCar if any isolated rider lacks good options

## Simulation API

```python
from simulator import GameSimulator
from agents import create_agent

# Run a single game
sim = GameSimulator(verbose=True)
agents = [create_agent('claudebot', 0), create_agent('gemini', 1)]
result = sim.run_game(agents)

# Run a tournament
results = sim.run_tournament(
    agent_types=['claudebot', 'gemini', 'wheelsucker', 'tobibot'],
    games_per_matchup=20
)

# Generate analysis report
from analysis import GameAnalyzer
analyzer = GameAnalyzer(log_dir="game_logs")
logs = analyzer.load_game_logs()
analyzer.generate_report(logs)
```

## Creating Custom Agents

```python
from agents import Agent
from game_engine import GameEngine, Move
from game_state import Player, Rider
from typing import List, Optional

class MyAgent(Agent):
    def __init__(self, player_id: int):
        super().__init__(player_id, "Custom")

    def choose_move(self, engine: GameEngine, player: Player,
                    eligible_riders: List[Rider] = None) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        # Your custom logic here
        return your_chosen_move

# Register in agents.py create_agent() and get_available_agents()
```

## Game Logs

All games are logged as JSON in `game_logs/`:
- `game_*.json` - Simulated game logs
- `play_*.json` - Interactive game logs (with `mode: "interactive"`)
- `tournament_results_*.csv` - Tournament results
- `analysis_report.txt` - Analysis report

## Performance

- Single game: ~0.1-1 second
- 50 games: ~5-30 seconds
- 100 games: ~10-60 seconds
- Tournament (4 agents, 20 games each): ~2-5 minutes

## License

This simulator is provided as-is for game development and testing purposes.
