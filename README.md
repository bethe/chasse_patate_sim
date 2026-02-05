# Chasse Patate - Cycling Board Game Simulator

A comprehensive simulation framework for testing and balancing the Chasse Patate cycling board game through AI agent play.

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
├── agents.py              # AI agent implementations (14 types)
├── simulator.py           # Game simulation and logging
├── analysis.py            # Statistical analysis tools
├── play.py                # Interactive play mode
├── quick_test.py          # Fast balance testing script
├── example_usage.py       # Example scripts and tutorials
├── generate_report.py     # Standalone report generation
├── test_terrain_limits.py # Unit tests for terrain limits
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

Play against AI bots interactively. Choose number of players (2-5) and assign human or bot to each slot.

### Run a Quick Balance Test

```bash
python quick_test.py
```

Runs 50 games and shows win rates, score distribution, action usage, and game over reasons.

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

### Terrain Limits (NEW)
Riders have maximum fields per round on certain terrain:
| Rider    | Terrain  | Max Fields |
|----------|----------|------------|
| Sprinter | Climb    | 3          |
| Rouleur  | Climb    | 4          |
| Climber  | Cobbles  | 3          |

**Important**: Limits apply only to the portion of movement on limited terrain. In team moves, each rider applies their own limits individually.

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

### Checkpoints
- Every 10 fields (10, 20, 30, ...)
- Each rider crossing draws 3 cards
- In team moves, EACH rider crossing gets 3 cards

### Game End Conditions
1. **5 riders finished** - 5+ riders crossed finish line
2. **Team finished** - One player has all 3 riders at finish
3. **Out of cards** - Deck empty and all hands empty

## Available AI Agents

14 different AI agent types:

| Agent          | Strategy                                      |
|----------------|-----------------------------------------------|
| random         | Plays randomly (baseline)                     |
| greedy         | Maximizes total advancement                   |
| lead_rider     | Focuses on advancing the leading rider        |
| balanced       | Keeps all three riders advancing together     |
| sprint_hunter  | Prioritizes sprint points                     |
| conservative   | Plays cautiously                              |
| aggressive     | Maximum advancement per move                  |
| adaptive       | Adjusts strategy based on terrain             |
| wheelsucker    | Prioritizes drafting opportunities            |
| **gemini**     | Balanced scoring: advancement + points + efficiency |
| **claudebot**  | Multi-factor: terrain awareness, sprint targeting, card economy |
| rouleur_focus  | Prefers playing Rouleur cards                 |
| sprinter_focus | Prefers playing Sprinter cards                |
| climber_focus  | Prefers playing Climber cards                 |

### Featured Agents

**ClaudeBot** - A sophisticated agent considering:
- Terrain-aware movement (uses terrain limits strategically)
- Sprint/finish targeting based on arrival order
- Card economy and hand management
- Drafting efficiency (free movement is valuable)
- Rider specialization (right rider for right terrain)
- Positioning for future drafts

**GeminiBot** - Balanced scoring system weighing:
- Total advancement (distance x riders)
- Sprint/finish points potential
- Card efficiency (penalizes card usage)
- Checkpoint card drawing
- Hand management (TeamCar when needed)

## Usage Examples

### Interactive Play

```bash
python play.py
```

### Simulation

```python
from simulator import GameSimulator
from agents import create_agent

# Create simulator
sim = GameSimulator(verbose=True)

# Create agents
agents = [
    create_agent('claudebot', 0),
    create_agent('gemini', 1)
]

# Run a game
result = sim.run_game(agents)
print(f"Winner: {result['final_result']['winner']}")
```

### Tournament

```python
sim = GameSimulator()
results = sim.run_tournament(
    agent_types=['claudebot', 'gemini', 'wheelsucker', 'greedy'],
    games_per_matchup=20
)
```

### Analysis

```python
from analysis import GameAnalyzer

analyzer = GameAnalyzer(log_dir="game_logs")
logs = analyzer.load_game_logs()
analyzer.generate_report(logs)
```

## Track Configuration

Default configuration: Tiles 1, 5, 4 (60 fields total)

Available tiles:
1. **Flat** - All flat terrain
2. **Mountaintop Finish** - Flat start, long climb
3. **Champs Elysees** - Flat + cobbles
4. **Up and Down** - Climb + descent
5. **Paris-Roubaix** - Mixed cobbles sections

```python
from game_state import GameState

# Custom track
state = GameState(num_players=2, tile_config=[1, 2, 3])
```

## Creating Custom Agents

```python
from agents import Agent
from game_engine import GameEngine, Move
from game_state import Player, Rider
from typing import List, Optional

class CustomAgent(Agent):
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

## Analysis Report Contents

Generated reports include:
- Win rates by agent type
- Average scores and finishing positions
- Game length statistics
- Game over reason distribution
- Action usage breakdown
- Card usage statistics
- Dominant strategy detection

## Performance

- Single game: ~0.1-1 second
- 50 games: ~5-30 seconds
- 100 games: ~10-60 seconds
- Tournament (4 agents, 20 games each): ~2-5 minutes

## Running Tests

```bash
python test_terrain_limits.py
```

Runs 13 unit tests for terrain limit functionality.

## Recent Updates

- Added **Terrain Limits** rule (Sprinter/Rouleur/Climber terrain restrictions)
- Added **El Patron** rule (rotating turn order for tied positions)
- Added **ClaudeBotAgent** (terrain-aware multi-factor AI)
- Added **GeminiAgent** (balanced scoring AI)
- Round-based game loop (all riders move before new round)
- Same player's riders can draft each other
- Game ends when one player finishes all 3 riders

## License

This simulator is provided as-is for game development and testing purposes.
