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

## Running

```bash
# Quick balance test (10-50 games, shows win rates)
python quick_test.py

# Generate analysis report from existing game logs
python generate_report.py

# Usage examples and tutorials
python example_usage.py
```

## Project Structure

| File | Purpose |
|---|---|
| `game_state.py` | Core data structures: cards, riders, players, board |
| `game_engine.py` | Game rules, move validation, turn logic |
| `agents.py` | AI agent implementations (12 strategies) |
| `simulator.py` | Game execution, logging, batch runs, tournaments |
| `analysis.py` | Statistical analysis and report generation |
| `quick_test.py` | Fast balance testing script |
| `generate_report.py` | Standalone report generator |
| `example_usage.py` | Usage examples |

Output goes to `game_logs/` (gitignored).

## Key Concepts

- **6 actions:** Pull, Attack, Draft, TeamPull, TeamDraft, TeamCar
- **4 card types:** Energy, Rouleur, Sprinter, Climber
- **3 riders per player**, each with their own hand/deck
- Game ends when 5 riders finish, turn limit (150) hit, or cards run out
- Agents implement `choose_move()` from abstract `Agent` base class
- Factory: `create_agent(agent_type, player_id)` creates agents by name

## Code Conventions

- Dataclasses for all game entities (`Card`, `Rider`, `Player`, `Move`, etc.)
- Enums for constants (`CardType`, `TerrainType`, `ActionType`, `PlayMode`)
- Type hints on all function signatures and class attributes
- Abstract base class pattern for agents (`Agent` ABC → concrete agents)
- JSON for game logs, CSV for tournament results
- No test framework configured; validation via `quick_test.py` runs
