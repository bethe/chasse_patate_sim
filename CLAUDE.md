# CLAUDE.md

## Project Overview

Chasse Patate — a cycling board game balance simulator. Runs thousands of AI-vs-AI games to detect dominant strategies and balance issues.

## Tech Stack

- **Language:** Python 3
- **Dependencies:** pandas, numpy, matplotlib (see `requirements.txt`)

## Setup

```bash
pip install -r requirements.txt
```

## Configuration

The game supports customizable parameters through `config.json`.

**Quick start:**
```bash
# View current configuration
python game_config.py show

# Validate configuration
python game_config.py validate

# Create a preset (quick, marathon, mountain, cobbles)
python game_config.py preset quick

# Reset to defaults
python game_config.py reset
```

**Configurable parameters:**
- **Tile configuration**: Which race tiles to use and in what order
- **Starting hand**: Card composition at game start (Energy, Rouleur, Sprinter, Climber, random)
- **Checkpoint draws**: How many cards drawn at mid-tile and new-tile checkpoints

All scripts automatically load `config.json` when creating games.

## Running

```bash
# Quick balance test (10-50 games, shows win rates)
python quick_test.py

# Run comprehensive multi-player tournament (2/3/4 players, 250 games)
python run_tournament.py

# Play interactively against bots (press 'r' during play to view card reference)
python play.py

# Replay a game from logs with full visualization
python game_analyzer.py game_0.json

# Run comprehensive unit tests for all game rules
python test_game_rules.py
```

## Project Structure

| File | Purpose |
|---|---|
| `game_state.py` | Core data structures: cards, riders, players, board, El Patron rule |
| `game_engine.py` | Game rules, move validation, terrain limits |
| `game_config.py` | Configuration system, CLI management, presets |
| `agents.py` | AI agent implementations (8 strategies) |
| `simulator.py` | Game execution, logging, batch runs, tournaments |
| `analysis.py` | Statistical analysis and report generation |
| `quick_test.py` | Fast balance testing script |
| `run_tournament.py` | Multi-player tournament runner (2/3/4 players, all combinations) |
| `play.py` | Interactive play against bots (terminal UI) |
| `game_analyzer.py` | Replay games from logs with full visualization |
| `test_game_rules.py` | Comprehensive unit tests: game rules, mechanics, agents, tournament features |
| `config.json` | Game configuration file (tiles, starting hand, checkpoints) |

Output goes to `game_logs/` (gitignored).

## Tournament Mode

The `run_tournament.py` script runs comprehensive multi-player tournaments:

```bash
python run_tournament.py
```

**What it does:**
- Tests all agent combinations across 2, 3, and 4 players
- 10 games per combination (250 total games)
- **Alternates player positions** to minimize position bias
- Generates detailed statistics and head-to-head comparisons
- Saves results to `game_logs/tournament_results_TIMESTAMP.csv`

**Position Alternation:**
Games are distributed across all permutations of each combination to ensure agents experience different starting positions equally. For example, in 2-player games with 10 games per combination, each agent plays 5 games as Player 0 and 5 games as Player 1.

**Statistics provided:**
- Overall win rates by agent
- Average scores and total scores
- Head-to-head matrix for 2-player matchups
- **Position bias analysis** (wins by player position)
- Results breakdown by player count
- Game length and end reason distribution

**Customization:**
Edit the script to change agents, games per combination, or player counts.

## Key Concepts

### Actions
- **Pull** (1-3 cards): Advance a single rider
- **Attack** (3 cards): Aggressive advance with bonus
- **Draft** (0 cards): Follow previous move (free movement)
- **TeamPull** (1-3 cards): One rider pulls, teammates draft
- **TeamDraft** (0 cards): Multiple riders draft together
- **TeamCar** (0 cards): Draw 2, discard 1

### Card Types
- **Energy** - Wild card, always moves 1
- **Rouleur** - Balanced movement
- **Sprinter** - Fast on flat/descent
- **Climber** - Strong on climbs

### Riders
- 3 riders per player (Rouleur, Sprinter, Climber)
- Each rider has terrain-specific strengths

### Terrain Limits (NEW)
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

### Turn Order (Round-Based)
1. At round start, El Patron rotates (except round 1)
2. Riders move in order of position (leaders first)
3. When tied, El Patron order determines who moves first
4. Same player's different riders CAN draft each other
5. All riders must move once before a new round begins

### Game End Conditions
- 5 riders finish
- One player has all 3 riders at finish
- Player stuck (any player has 0 total advancement over 5 consecutive rounds)
- Round limit (150) hit
- All cards run out

## Available Agents

8 agent types: `random`, `marc_soler`, `wheelsucker`, `gemini`, `chatgpt`, `claudebot`, `claudebot2`, `tobibot`

### Featured Agents

**ClaudeBot** - Multi-factor scoring:
- Terrain-aware movement (uses terrain limits strategically)
- Sprint/finish targeting based on arrival order
- Card economy and hand management
- Drafting efficiency (free movement is valuable)
- Rider specialization (right rider for right terrain)

**ClaudeBot2** - Enhanced multi-factor scoring with improved terrain awareness and strategic depth.

**Gemini** - Balanced scoring:
- Total advancement (distance x riders)
- Sprint/finish points potential
- Card efficiency (penalizes card usage)
- Checkpoint card drawing
- Hand management (TeamCar when needed)

**TobiBot** - Prioritized decision-making:
- Score sprint/finish points when possible
- Hand management (TeamCar when ≤6 cards and no efficient moves)
- Prefer efficient moves (TeamDraft > Draft > TeamPull)
- Group with team riders (only when moving forward to join riders ahead)
- When El Patron, position with opponents
- Maximize team advancement respecting terrain limits (with bonus for card efficiency)
- TeamCar if any isolated rider lacks good options

## Code Conventions

- Dataclasses for all game entities (`Card`, `Rider`, `Player`, `Move`, etc.)
- Enums for constants (`CardType`, `TerrainType`, `ActionType`, `PlayMode`)
- Type hints on all function signatures and class attributes
- Abstract base class pattern for agents (`Agent` ABC -> concrete agents)
- `eligible_riders` parameter in `choose_move()` for round-based turns
- JSON for game logs, CSV for tournament results
- Comprehensive unit tests in `test_game_rules.py` (80+ tests covering all mechanics, agents, and tournament features)

## Key Functions

### game_engine.py
- `TERRAIN_LIMITS` - Dict mapping (CardType, TerrainType) -> max fields
- `_calculate_limited_movement()` - Apply terrain limits field-by-field
- `get_valid_moves(player, eligible_riders)` - Get valid moves for eligible riders
- `execute_move(move)` - Execute a move and return results

### game_state.py
- `start_new_round()` - Begin new round, rotate El Patron
- `determine_next_turn()` - Get (player, eligible_riders) or None if round complete
- `mark_riders_moved(riders, position)` - Mark riders as moved
- `check_game_over()` - Check all end conditions

### agents.py
- `create_agent(agent_type, player_id)` - Factory function
- `get_available_agents()` - List all agent names
- All agents implement `choose_move(engine, player, eligible_riders)`

## Recent Changes

- **Added game configuration system** (`config.json`, `game_config.py`)
  - Customizable tile configuration
  - Configurable starting hand composition
  - Adjustable checkpoint card draws
  - Auto-loaded by all game scripts
- Added terrain limits rule (Sprinter/Rouleur/Climber restrictions)
- Added El Patron rule (rotating turn order for tied positions)
- Added ClaudeBotAgent (terrain-aware multi-factor AI)
- Added GeminiAgent (balanced scoring AI)
- Round-based game loop (all riders move before new round)
- Same player's riders can draft each other
- Game ends when one player finishes all 3 riders
