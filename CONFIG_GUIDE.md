# Game Configuration Guide

The Chasse Patate simulator now supports customizable game parameters through a `config.json` file.

## Quick Start

1. **View current config**: Look at [`config.json`](config.json)
2. **See all options**: Check [`config.example.json`](config.example.json)
3. **Modify settings**: Edit `config.json` and save
4. **Run your game**: All scripts automatically use the config

## Configuration File

The configuration file (`config.json`) controls three main aspects of the game:

### 1. Tile Configuration

Choose which race tiles to use and in what order:

```json
{
  "tile_config": [1, 5, 4]
}
```

**Available tiles:**
- **Tile 1**: "Flat" - All flat terrain (20 fields)
- **Tile 2**: "Mountaintop Finish" - Flat start, long climb
- **Tile 3**: "Champs Elysees" - Flat + cobbles
- **Tile 4**: "Up and Down" - Climb + descent
- **Tile 5**: "Paris-Roubaix" - Mixed cobbles sections

**Examples:**
- `[1, 1, 1]` - All flat, 60 fields total
- `[2]` - Just the mountain tile, 20 fields
- `[1, 2, 3, 4, 5]` - All tiles in order, 100 fields total

### 2. Starting Hand Configuration

Customize what cards each player receives at game start:

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

**Card types:**
- **energy_cards**: Energy cards (always move 1 field)
- **rouleur_cards**: Rouleur rider cards
- **sprinter_cards**: Sprinter rider cards
- **climber_cards**: Climber rider cards
- **random_cards**: Random cards from remaining deck

**Default**: 9 cards total per player (3 Energy + 1 of each rider type + 3 random)

**Examples:**
- More starting cards: `"energy_cards": 5, "random_cards": 5` (11 cards total)
- Rider-focused: `"energy_cards": 0, "rouleur_cards": 2, "sprinter_cards": 2, "climber_cards": 2, "random_cards": 3`
- Energy-only start: `"energy_cards": 9, "rouleur_cards": 0, "sprinter_cards": 0, "climber_cards": 0, "random_cards": 0`

### 3. Checkpoint Card Draws

Configure how many cards are drawn when riders cross checkpoints:

```json
{
  "checkpoints": {
    "mid_tile_checkpoint": 3,
    "new_tile_checkpoint": 3
  }
}
```

**Checkpoint positions:**
- **mid_tile_checkpoint**: Cards at field 10, 30, 50, 70, 90... (middle of each tile)
- **new_tile_checkpoint**: Cards at field 20, 40, 60, 80, 100... (tile boundaries)

**Default**: 3 cards at each checkpoint

**Examples:**
- More resources: Both set to `5`
- Scarce resources: Both set to `1`
- Reward tile transitions: `"mid_tile_checkpoint": 1, "new_tile_checkpoint": 3`

## Using the Configuration

### All Scripts Auto-Load Config

Every script automatically loads `config.json` when creating games:

```bash
# All of these use config.json automatically
python play.py
python quick_test.py
python run_tournament.py
python game_analyzer.py game_0.json
```

### Programmatic Usage

```python
from game_config import GameConfig, ConfigLoader
from game_state import GameState

# Option 1: Auto-load from config.json
state = GameState(num_players=2)  # Uses config.json automatically

# Option 2: Load from custom path
config = ConfigLoader.load("my_custom_config.json")
state = GameState(num_players=2, config=config)

# Option 3: Create config programmatically
config = GameConfig(
    tile_config=[1, 2, 3],
    starting_hand=StartingHandConfig(energy_cards=5),
    checkpoints=CheckpointConfig(mid_tile_checkpoint=5)
)
state = GameState(num_players=2, config=config)
```

### Creating a Custom Config

1. Copy `config.json` to a new file:
   ```bash
   cp config.json custom_config.json
   ```

2. Edit `custom_config.json` with your desired settings

3. Use it programmatically (you'll need to modify the script):
   ```python
   from game_config import ConfigLoader
   config = ConfigLoader.load("custom_config.json")
   ```

## Validation

The config system validates your settings:

- **Tile IDs**: Must be 1-5
- **Starting hands**: Total cards shouldn't exceed deck size (90 cards)
- **Checkpoints**: Card counts cannot be negative

If validation fails, the default configuration is used and errors are printed.

## Restoring Defaults

To restore the default configuration:

```python
from game_config import ConfigLoader
ConfigLoader.save_default("config.json")
```

Or manually edit `config.json` to match the values in `config.example.json`.

## Examples

### Short, High-Resource Game
```json
{
  "tile_config": [1],
  "starting_hand": {
    "energy_cards": 5,
    "rouleur_cards": 2,
    "sprinter_cards": 2,
    "climber_cards": 2,
    "random_cards": 5
  },
  "checkpoints": {
    "mid_tile_checkpoint": 5,
    "new_tile_checkpoint": 5
  }
}
```

### Long, Resource-Scarce Game
```json
{
  "tile_config": [1, 2, 3, 4, 5],
  "starting_hand": {
    "energy_cards": 2,
    "rouleur_cards": 1,
    "sprinter_cards": 1,
    "climber_cards": 1,
    "random_cards": 1
  },
  "checkpoints": {
    "mid_tile_checkpoint": 1,
    "new_tile_checkpoint": 1
  }
}
```

### Mountain Challenge
```json
{
  "tile_config": [2, 2, 2],
  "starting_hand": {
    "energy_cards": 3,
    "rouleur_cards": 2,
    "sprinter_cards": 0,
    "climber_cards": 3,
    "random_cards": 2
  },
  "checkpoints": {
    "mid_tile_checkpoint": 4,
    "new_tile_checkpoint": 4
  }
}
```

## Troubleshooting

**Q: My changes aren't taking effect**
- Make sure you saved `config.json` after editing
- Check that the JSON is valid (no trailing commas, proper quotes)

**Q: I get validation errors**
- Check the error messages printed to console
- Verify tile IDs are 1-5
- Ensure checkpoint card counts are non-negative

**Q: Game crashes on startup**
- Your `config.json` may have invalid JSON syntax
- Try copying from `config.example.json` and editing again
- The system will fall back to defaults if config can't be loaded
