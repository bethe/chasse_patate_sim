# Game Configuration System - Implementation Summary

A comprehensive configuration system has been added to the Chasse Patate simulator, allowing you to customize game parameters without modifying code.

## What Was Added

### Core Files

1. **`game_config.py`** - Configuration module
   - `GameConfig` - Main configuration dataclass
   - `StartingHandConfig` - Starting hand composition
   - `CheckpointConfig` - Checkpoint card draw amounts
   - `ConfigLoader` - Loads and validates configuration from JSON
   - Global config management functions

2. **`config.json`** - Main configuration file
   - Active configuration used by all game scripts
   - Automatically loaded when games are created
   - Edit this file to change game parameters

3. **`config_manager.py`** - Command-line utility
   - View current configuration
   - Validate configuration files
   - Create preset configurations
   - Reset to defaults

4. **`config.example.json`** - Example configuration
   - Shows all available options with inline comments
   - Use as a reference when editing `config.json`

### Documentation

5. **`CONFIG_GUIDE.md`** - Comprehensive user guide
   - Detailed explanation of all configuration options
   - Usage examples and troubleshooting
   - Preset configuration examples

6. **`CLAUDE.md`** - Updated with configuration section
7. **`CONFIGURATION_SYSTEM.md`** - This file

### Modified Files

- **`game_state.py`** - Updated to load and use configuration
  - Accepts optional `config` parameter
  - Auto-loads `config.json` if not provided
  - Uses config for tile selection and starting hands

- **`game_engine.py`** - Updated checkpoint card draws
  - Uses config for checkpoint amounts (field 10, 20, 40)
  - Applies to all move types (Pull, TeamPull, TeamDraft)

## Configuration Options

### 1. Tile Configuration
```json
"tile_config": [1, 5, 4]
```
- Choose which race tiles and in what order
- Tiles: 1=Flat, 2=Mountaintop, 3=Champs Elysees, 4=Up&Down, 5=Paris-Roubaix
- Each tile is 20 fields

### 2. Starting Hand
```json
"starting_hand": {
  "energy_cards": 3,
  "rouleur_cards": 1,
  "sprinter_cards": 1,
  "climber_cards": 1,
  "random_cards": 3
}
```
- Customize initial cards for each player
- Mix specific card types with random draws
- Default: 9 cards total (3 Energy + 3 rider types + 3 random)

### 3. Checkpoint Card Draws
```json
"checkpoints": {
  "checkpoint_10_cards": 3,
  "checkpoint_20_cards": 3,
  "checkpoint_40_cards": 3
}
```
- Control resource flow during the game
- Field 10, 30, 50... use `checkpoint_10_cards`
- Field 20, 60, 100... use `checkpoint_20_cards`
- Field 40, 80, 120... use `checkpoint_40_cards`

## How to Use

### Quick Start
```bash
# View current settings
python config_manager.py show

# Edit config.json with your preferred text editor
# Then validate your changes
python config_manager.py validate

# Run any game script - config is automatically loaded
python quick_test.py
python run_tournament.py
python play.py
```

### Create Presets
```bash
# Create a quick game preset
python config_manager.py preset quick

# Create a marathon preset
python config_manager.py preset marathon marathon_config.json

# Available presets: quick, marathon, mountain, cobbles
```

### Reset to Defaults
```bash
python config_manager.py reset
```

## Backward Compatibility

- All existing code continues to work without modification
- If `config.json` is missing or invalid, default values are used
- All `GameState()` calls automatically load `config.json`
- You can still override with explicit parameters:
  ```python
  state = GameState(num_players=2, tile_config=[1, 2, 3])
  ```

## Validation

The system validates your configuration:
- Tile IDs must be 1-5
- Starting hand total should fit within deck size (90 cards)
- Checkpoint card draws cannot be negative
- Invalid configs fall back to defaults with error messages

## Examples

### Short High-Resource Game
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
    "checkpoint_10_cards": 5,
    "checkpoint_20_cards": 5,
    "checkpoint_40_cards": 5
  }
}
```
Result: 20-field track, 16 cards/player, 5 cards per checkpoint

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
    "checkpoint_10_cards": 4,
    "checkpoint_20_cards": 4,
    "checkpoint_40_cards": 4
  }
}
```
Result: 60-field climb-heavy track, climber-focused starting hands

### Resource Scarcity
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
    "checkpoint_10_cards": 1,
    "checkpoint_20_cards": 1,
    "checkpoint_40_cards": 2
  }
}
```
Result: 100-field marathon, scarce resources, strategic card management

## Programmatic Usage

### Load from File
```python
from game_config import ConfigLoader
from game_state import GameState

# Auto-load from config.json
state = GameState(num_players=2)

# Load from custom path
config = ConfigLoader.load("custom_config.json")
state = GameState(num_players=2, config=config)
```

### Create Programmatically
```python
from game_config import GameConfig, StartingHandConfig, CheckpointConfig

config = GameConfig(
    tile_config=[1, 2, 3],
    starting_hand=StartingHandConfig(
        energy_cards=5,
        rouleur_cards=2,
        sprinter_cards=2,
        climber_cards=2,
        random_cards=3
    ),
    checkpoints=CheckpointConfig(
        checkpoint_10_cards=5,
        checkpoint_20_cards=5,
        checkpoint_40_cards=5
    )
)

state = GameState(num_players=2, config=config)
```

### Set Global Config
```python
from game_config import set_config, reload_config

# Set programmatically
set_config(my_config)

# Reload from file
reload_config("new_config.json")
```

## Testing

The configuration system has been tested with:
- ✅ Loading from `config.json`
- ✅ Validation of all parameters
- ✅ Creating games with custom configs
- ✅ Checkpoint card draws at different positions
- ✅ Starting hand composition
- ✅ Tile configuration
- ✅ Preset creation
- ✅ Programmatic config management

All existing tests continue to pass, and the system is fully backward compatible.

## Files Summary

| File | Purpose | Type |
|------|---------|------|
| `config.json` | Active configuration | **Edit this** |
| `config.example.json` | Example with comments | Reference |
| `game_config.py` | Configuration module | Core code |
| `config_manager.py` | CLI utility | Tool |
| `CONFIG_GUIDE.md` | User documentation | Docs |
| `CONFIGURATION_SYSTEM.md` | Implementation summary | Docs |

## Next Steps

1. **Try the default config**: Run `python config_manager.py show`
2. **Experiment**: Edit `config.json` and run `python quick_test.py`
3. **Create presets**: Use `python config_manager.py preset [name]`
4. **Read the guide**: See `CONFIG_GUIDE.md` for detailed examples
5. **Share configs**: Save interesting configurations for different scenarios

Enjoy customizing your Chasse Patate games!
