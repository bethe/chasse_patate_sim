# TobiBot Agent Implementation

## Overview

TobiBot is a strategic AI agent for the Chasse Patate cycling board game simulator that uses a prioritized decision-making system.

## Implementation Details

### Agent Class
- **Class:** `TobiBotAgent` in [agents.py](agents.py)
- **Agent Type:** `'tobibot'`
- **Display Name:** "TobiBot"

### Decision Priority System

TobiBot makes decisions based on the following priority order:

#### Priority 1: Maximize Sprint/Finish Points
- Identifies moves that can score points at sprint or finish lines
- Calculates potential points for all riders involved in the move
- Selects the move that scores the most points when scoring opportunities exist

#### Priority 2: Hand Management (≤6 cards)
- When hand size is 6 or fewer cards:
  - Checks if any move has efficiency >1 field per card
  - Plays TeamCar if no efficient moves are available
  - Otherwise proceeds to next priority

#### Priority 3: Prefer Efficient Moves
In order of preference:
1. **TeamDraft** - Multiple riders draft together (free movement)
2. **Draft** - Single rider drafts (free movement)
3. **TeamPull** - One rider pulls, teammates draft

#### Priority 4: Group with Team Riders
- Evaluates moves that end at fields where team riders are positioned
- Scores moves based on number of teammates at destination (+50 per teammate)

#### Priority 5: El Patron Positioning
- When current player is El Patron, prioritizes moves to fields with opponent riders
- Scores moves based on number of opponents at destination (+40 per opponent)
- Helps establish turn order advantage in future rounds

#### Priority 6: Maximize Team Advancement
- Calculates total advancement for team moves
- Respects terrain limits for each rider individually
- Ensures group stays together by not moving further than the most limited rider
- Scores moves based on total team advancement (+10 per field)

#### Priority 7: Isolated Lead Rider Check
- Checks if lead rider is alone on its field
- If isolated and cannot draft or advance >4 fields, plays TeamCar
- Prevents lead rider from being stranded without support

## Key Methods

### `choose_move(engine, player, eligible_riders)`
Main decision method that applies the priority system.

### `_get_scoring_moves(valid_moves, engine)`
Filters moves that can score points at sprints or finish.

### `_calculate_points(move, engine)`
Calculates total points a move would score for all riders involved.

### `_get_rider_movement(move, rider, engine)`
Calculates movement for a specific rider, accounting for terrain limits.

### `_is_rider_isolated(rider, engine, player)`
Checks if a rider is alone on its field (no teammates).

### `_select_best_move(moves, engine, player)`
Applies priorities 4-6 to select the best move from a list.

## Usage

### Create TobiBot Agent
```python
from agents import create_agent

# Create TobiBot for player 0
tobibot = create_agent('tobibot', 0)
```

### Run Game with TobiBot
```python
from simulator import GameSimulator
from agents import create_agent

sim = GameSimulator(verbose=True)
agents = [
    create_agent('tobibot', 0),
    create_agent('gemini', 1)
]
result = sim.run_game(agents)
```

### Test TobiBot
```bash
# Run the test script
python test_tobibot.py

# Run example usage with TobiBot
python example_usage.py
```

## Strategic Characteristics

### Strengths
- **Point-focused**: Aggressively pursues sprint and finish points
- **Efficient**: Prioritizes free movement (drafting) when not scoring
- **Team-oriented**: Keeps riders grouped for team move opportunities
- **Hand management**: Balances card usage with hand replenishment
- **Terrain-aware**: Respects terrain limits to avoid wasted movement

### Playstyle
- Opportunistic scorer when sprints/finishes are reachable
- Conservative with cards when hand is low
- Prefers team coordination and drafting over solo advancement
- Uses El Patron status strategically for positioning

## Files Updated

1. **[agents.py](agents.py)**: Added `TobiBotAgent` class
2. **[CLAUDE.md](CLAUDE.md)**: Updated agent count and added TobiBot to featured agents
3. **[README.md](README.md)**: Updated agent count and added TobiBot to agent table
4. **[example_usage.py](example_usage.py)**: Added `example_test_tobibot()` function
5. **[test_tobibot.py](test_tobibot.py)**: Created test script

## Testing

The agent has been tested and successfully:
- ✓ Registers in the agent factory
- ✓ Appears in available agents list
- ✓ Executes valid moves
- ✓ Completes full games
- ✓ Competes against other agents (ClaudeBot, Gemini, ChatGPT)

## Version
- Added: 2026-02-06
- Agent count updated: 14 → 15 agents
