# Chasse Patate - Game Balance Simulator

A simulation framework for testing and balancing the Chasse Patate cycling board game through AI agent play. Also supports interactive human-vs-bot play.

## Overview

- Run thousands of AI-vs-AI games to detect dominant strategies
- Play interactively against bots in the terminal
- Track detailed statistics: moves, scores, card usage, sprint points
- Generate analysis reports with balance assessments

## Quick Start

```bash
pip install -r requirements.txt

# Play against bots
python play.py

# Fast balance test (50 games, win rates, balance assessment)
python quick_test.py

# Generate analysis report from game logs
python generate_report.py

# Usage examples and tutorials
python example_usage.py
```

## Project Structure

```
.
├── game_state.py        # Core data structures: cards, riders, players, board
├── game_engine.py       # Game rules, move validation, turn logic
├── agents.py            # AI agent implementations (12 strategies)
├── simulator.py         # Game execution, logging, batch runs, tournaments
├── analysis.py          # Statistical analysis and report generation
├── play.py              # Interactive play against bots (terminal UI)
├── quick_test.py        # Fast balance testing script
├── generate_report.py   # Standalone report generator
├── example_usage.py     # Usage examples
├── requirements.txt     # Python dependencies (pandas, numpy, matplotlib)
└── game_logs/           # Generated game logs (gitignored)
```

## Game Rules

### Riders and Cards

- **3 riders per player**: Rouleur, Sprinter, Climber
- **4 card types**: Energy (always 1 movement), Rouleur, Sprinter, Climber
- Cards can only be played on matching rider types (Energy works on any rider)
- Movement values depend on the current terrain and action mode (Pull vs Attack)

### Actions

| Action | Cards | Description |
|---|---|---|
| **Pull** | 1-3 | Advance a single rider |
| **Attack** | 3 | Burst advance (higher values on some terrains) |
| **Draft** | 0 | Copy the previous player's movement for free |
| **TeamPull** | 1-3 | One rider pulls, teammates at same position draft along |
| **TeamDraft** | 0 | Multiple riders draft together off another player's move |
| **TeamCar** | 0 | Draw 2 cards, discard 1 (rider does not move) |

### Rounds and Turns

The game is played in **rounds**. One round completes when every rider has been part of a move.

- **Turn order**: the rider most advanced on the track moves first
- **Tied positions**: players alternate turns by player index; after one move, the turn passes to the next player before the same player can move again at that position
- **Team actions**: all riders involved (lead + drafters) count as having moved

### Scoring

- **Intermediate sprints** (last field of each tile): top 3 riders earn 3/2/1 points (6 total)
- **Finish line** (last field of final tile): top 5 riders earn 12/8/5/3/1 points (29 total)
- Points are awarded per rider as they cross or land on sprint/finish fields
- Multiple riders from the same player can score in the same turn

### Checkpoints

Every 10 fields (10, 20, 30, ...), each rider crossing draws 3 cards. In team moves, every rider that crosses a checkpoint draws independently.

### Game End

1. **5 riders finished** - crossed the finish line
2. **Round limit** - 150 rounds completed
3. **Out of cards** - deck empty and all hands empty

## Interactive Play

```bash
python play.py
```

1. Choose number of players (2-5)
2. Assign each slot as "human" or a bot type
3. On your turn: pick a rider, then an action, then cards
4. Press `b` to go back to the previous decision at any step

## AI Agents

12 bot strategies available via `create_agent(type, player_id)`:

| Agent | Strategy |
|---|---|
| `random` | Random moves (baseline) |
| `greedy` | Maximizes total advancement |
| `lead_rider` | Focuses on the leading rider |
| `balanced` | Keeps riders grouped together |
| `sprint_hunter` | Prioritizes sprint points |
| `conservative` | Rarely uses TeamCar |
| `aggressive` | Uses TeamCar frequently |
| `adaptive` | Adjusts strategy to terrain |
| `wheelsucker` | Prioritizes drafting |
| `rouleur_focus` | Prefers Rouleur cards |
| `sprinter_focus` | Prefers Sprinter cards |
| `climber_focus` | Prefers Climber cards |

## Simulation API

### Single Game

```python
from simulator import GameSimulator
from agents import create_agent

sim = GameSimulator(num_players=2, verbose=True)
agents = [create_agent('greedy', 0), create_agent('wheelsucker', 1)]
result = sim.run_game(agents, game_id=0)
```

### Tournament

```python
sim = GameSimulator(num_players=2)
results = sim.run_tournament(
    agent_types=['greedy', 'balanced', 'wheelsucker', 'sprint_hunter'],
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

## Game Logs

Games are logged as JSON in `game_logs/`. Each move entry includes both round and turn numbers:

```json
{
  "round": 3,
  "turn": 12,
  "player": 1,
  "move": {
    "action": "TeamPull",
    "rider": "P1R0",
    "old_position": 7,
    "new_position": 11,
    "movement": 4,
    "cards_played": ["Energy", "Energy", "Rouleur"],
    "drafting_riders": [
      {"rider": "P1R1", "old_position": 7, "new_position": 11}
    ],
    "points_earned": 0,
    "checkpoints_reached": [10],
    "cards_drawn": 6
  }
}
```

Final results include `total_rounds` and `total_turns` separately.

## Custom Agents

```python
from agents import Agent
from game_engine import GameEngine, Move
from game_state import Player, Rider
from typing import List, Optional

class MyAgent(Agent):
    def __init__(self, player_id: int):
        super().__init__(player_id, "MyAgent")

    def choose_move(self, engine: GameEngine, player: Player,
                    eligible_riders: List[Rider] = None) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        # Your logic here
        return valid_moves[0]
```

## Balance Indicators

**Healthy game:**
- Win rates within +-10% of expected
- Multiple viable strategies
- Diverse action usage
- Games end by riders finishing (not round limit)

**Warning signs:**
- One agent wins >60% of games
- >90% games hit round limit
- One action dominates >70% of usage
