"""
Chasse Patate - Game Configuration Module
Handles loading, validation, and management of game configuration from config.json

Usage as CLI:
    python game_config.py show                    # Show current config
    python game_config.py validate                # Validate config.json
    python game_config.py reset                   # Reset to defaults
    python game_config.py preset quick            # Create quick game preset
    python game_config.py preset marathon config.json  # Save preset as config.json
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class StartingHandConfig:
    """Configuration for starting hand composition"""
    energy_cards: int = 3
    rouleur_cards: int = 1
    sprinter_cards: int = 1
    climber_cards: int = 1
    random_cards: int = 3

    def total_cards(self) -> int:
        """Calculate total starting hand size"""
        return (self.energy_cards + self.rouleur_cards +
                self.sprinter_cards + self.climber_cards + self.random_cards)


@dataclass
class CheckpointConfig:
    """Configuration for card drawing at checkpoints"""
    mid_tile_checkpoint: int = 3  # Cards drawn at mid-tile (field 10, 30, 50, ...)
    new_tile_checkpoint: int = 3  # Cards drawn at tile boundary (field 20, 40, 60, ...)

    def get_cards_for_checkpoint(self, checkpoint: int) -> int:
        """Get number of cards to draw for a specific checkpoint position"""
        # Checkpoints are at positions 10, 20, 30, 40, 50, 60...
        # Mid-tile checkpoints: 10, 30, 50, ... (field 10 within each tile)
        # New-tile checkpoints: 20, 40, 60, ... (last field of each tile)
        field_in_tile = checkpoint % 20

        if field_in_tile == 10:
            return self.mid_tile_checkpoint
        else:
            return self.new_tile_checkpoint


@dataclass
class GameConfig:
    """Main game configuration"""
    tile_config: List[int] = field(default_factory=lambda: [1, 5, 4])
    starting_hand: StartingHandConfig = field(default_factory=StartingHandConfig)
    checkpoints: CheckpointConfig = field(default_factory=CheckpointConfig)

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'GameConfig':
        """Create GameConfig from dictionary"""
        starting_hand = StartingHandConfig(**config_dict.get('starting_hand', {}))
        checkpoints = CheckpointConfig(**config_dict.get('checkpoints', {}))

        return cls(
            tile_config=config_dict.get('tile_config', [1, 5, 4]),
            starting_hand=starting_hand,
            checkpoints=checkpoints
        )

    def to_dict(self) -> dict:
        """Convert GameConfig to dictionary"""
        return {
            'tile_config': self.tile_config,
            'starting_hand': {
                'energy_cards': self.starting_hand.energy_cards,
                'rouleur_cards': self.starting_hand.rouleur_cards,
                'sprinter_cards': self.starting_hand.sprinter_cards,
                'climber_cards': self.starting_hand.climber_cards,
                'random_cards': self.starting_hand.random_cards
            },
            'checkpoints': {
                'mid_tile_checkpoint': self.checkpoints.mid_tile_checkpoint,
                'new_tile_checkpoint': self.checkpoints.new_tile_checkpoint
            }
        }

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # Validate tile configuration
        if not self.tile_config:
            errors.append("tile_config cannot be empty")

        for tile_id in self.tile_config:
            if tile_id not in [1, 2, 3, 4, 5]:
                errors.append(f"Invalid tile_id {tile_id}. Must be 1-5.")

        # Validate starting hand
        if self.starting_hand.total_cards() > 90:
            errors.append(f"Starting hand total ({self.starting_hand.total_cards()}) "
                         f"exceeds total deck size (90)")

        # Validate checkpoint configuration
        if self.checkpoints.mid_tile_checkpoint < 0:
            errors.append("mid_tile_checkpoint cannot be negative")
        if self.checkpoints.new_tile_checkpoint < 0:
            errors.append("new_tile_checkpoint cannot be negative")

        return errors


class ConfigLoader:
    """Loads game configuration from config.json"""

    DEFAULT_CONFIG_PATH = "config.json"

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> GameConfig:
        """Load configuration from file, falling back to defaults if not found"""
        if config_path is None:
            config_path = cls.DEFAULT_CONFIG_PATH

        config_file = Path(config_path)

        if not config_file.exists():
            # Return default configuration
            return GameConfig()

        try:
            with open(config_file, 'r') as f:
                config_dict = json.load(f)

            config = GameConfig.from_dict(config_dict)

            # Validate configuration
            errors = config.validate()
            if errors:
                print(f"Configuration validation errors in {config_path}:")
                for error in errors:
                    print(f"  - {error}")
                print("Using default configuration instead.")
                return GameConfig()

            return config

        except json.JSONDecodeError as e:
            print(f"Error parsing {config_path}: {e}")
            print("Using default configuration instead.")
            return GameConfig()
        except Exception as e:
            print(f"Error loading {config_path}: {e}")
            print("Using default configuration instead.")
            return GameConfig()

    @classmethod
    def save_default(cls, config_path: Optional[str] = None):
        """Save default configuration to file"""
        if config_path is None:
            config_path = cls.DEFAULT_CONFIG_PATH

        config = GameConfig()
        config_dict = config.to_dict()

        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)

        print(f"Default configuration saved to {config_path}")


# Global configuration instance (loaded on module import)
_global_config: Optional[GameConfig] = None


def get_config() -> GameConfig:
    """Get the global game configuration"""
    global _global_config

    if _global_config is None:
        _global_config = ConfigLoader.load()

    return _global_config


def reload_config(config_path: Optional[str] = None):
    """Reload configuration from file"""
    global _global_config
    _global_config = ConfigLoader.load(config_path)
    return _global_config


def set_config(config: GameConfig):
    """Set the global configuration programmatically"""
    global _global_config
    _global_config = config


# ---------------------------------------------------------------------------
# CLI: show / validate / reset / preset
# ---------------------------------------------------------------------------

TILE_NAMES = {
    1: "Flat",
    2: "Mountaintop Finish",
    3: "Champs Elysees",
    4: "Up and Down",
    5: "Paris-Roubaix"
}

PRESETS = {
    "quick": {
        "tile_config": [1],
        "starting_hand": {
            "energy_cards": 5, "rouleur_cards": 2, "sprinter_cards": 2,
            "climber_cards": 2, "random_cards": 3
        },
        "checkpoints": {"mid_tile_checkpoint": 5, "new_tile_checkpoint": 5}
    },
    "marathon": {
        "tile_config": [1, 2, 3, 4, 5],
        "starting_hand": {
            "energy_cards": 2, "rouleur_cards": 1, "sprinter_cards": 1,
            "climber_cards": 1, "random_cards": 1
        },
        "checkpoints": {"mid_tile_checkpoint": 1, "new_tile_checkpoint": 1}
    },
    "mountain": {
        "tile_config": [2, 2, 2],
        "starting_hand": {
            "energy_cards": 3, "rouleur_cards": 2, "sprinter_cards": 0,
            "climber_cards": 3, "random_cards": 2
        },
        "checkpoints": {"mid_tile_checkpoint": 4, "new_tile_checkpoint": 4}
    },
    "cobbles": {
        "tile_config": [5, 5, 5],
        "starting_hand": {
            "energy_cards": 3, "rouleur_cards": 3, "sprinter_cards": 2,
            "climber_cards": 0, "random_cards": 2
        },
        "checkpoints": {"mid_tile_checkpoint": 4, "new_tile_checkpoint": 4}
    }
}


def show_config(config_path: str = "config.json"):
    """Display current configuration"""
    config = ConfigLoader.load(config_path)

    print("\n" + "=" * 60)
    print(f"Current Configuration ({config_path})")
    print("=" * 60)

    print("\nTILE CONFIGURATION:")
    print(f"  Tiles: {config.tile_config}")
    print(f"  Track length: {len(config.tile_config) * 20} fields")
    print("  Tile details:")
    for i, tile_id in enumerate(config.tile_config, 1):
        print(f"    Tile {i}: #{tile_id} - {TILE_NAMES.get(tile_id, 'Unknown')}")

    print("\nSTARTING HAND:")
    hand = config.starting_hand
    print(f"  Energy cards: {hand.energy_cards}")
    print(f"  Rouleur cards: {hand.rouleur_cards}")
    print(f"  Sprinter cards: {hand.sprinter_cards}")
    print(f"  Climber cards: {hand.climber_cards}")
    print(f"  Random cards: {hand.random_cards}")
    print(f"  -> Total: {hand.total_cards()} cards per player")

    print("\nCHECKPOINT CARD DRAWS:")
    cp = config.checkpoints
    print(f"  Mid-tile (field 10, 30, 50...): {cp.mid_tile_checkpoint} cards")
    print(f"  New tile (field 20, 40, 60...): {cp.new_tile_checkpoint} cards")

    print("\n" + "=" * 60 + "\n")


def reset_config(config_path: str = "config.json"):
    """Reset configuration to defaults"""
    ConfigLoader.save_default(config_path)
    print(f"\n[OK] Configuration reset to defaults: {config_path}\n")
    show_config(config_path)


def validate_config(config_path: str = "config.json"):
    """Validate configuration file"""
    print(f"\nValidating {config_path}...")

    config_file = Path(config_path)
    if not config_file.exists():
        print(f"[ERROR] {config_path} not found")
        return False

    try:
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
        print("[OK] JSON syntax is valid")
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON syntax error: {e}")
        return False

    config = GameConfig.from_dict(config_dict)
    errors = config.validate()

    if errors:
        print(f"[ERROR] Validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("[OK] Configuration is valid")
        print()
        show_config(config_path)
        return True


def create_preset(preset_name: str, output_path: str = None):
    """Create a preset configuration"""
    if output_path is None:
        output_path = f"config_{preset_name}.json"

    if preset_name not in PRESETS:
        print(f"[ERROR] Unknown preset: {preset_name}")
        print(f"Available presets: {', '.join(PRESETS.keys())}")
        return False

    with open(output_path, 'w') as f:
        json.dump(PRESETS[preset_name], f, indent=2)

    print(f"[OK] Created preset '{preset_name}': {output_path}")
    print()
    show_config(output_path)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Manage Chasse Patate game configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python game_config.py show                    # Show current config
  python game_config.py validate                # Validate config.json
  python game_config.py reset                   # Reset to defaults
  python game_config.py preset quick            # Create quick game preset
  python game_config.py preset marathon config.json  # Save marathon preset as config.json
        """
    )

    parser.add_argument(
        'action', choices=['show', 'validate', 'reset', 'preset'],
        help='Action to perform'
    )
    parser.add_argument(
        'preset_name', nargs='?',
        help='Preset name (for preset action): quick, marathon, mountain, cobbles'
    )
    parser.add_argument(
        'config_path', nargs='?', default='config.json',
        help='Path to config file (default: config.json)'
    )

    args = parser.parse_args()

    if args.action == 'show':
        show_config(args.config_path)
    elif args.action == 'validate':
        validate_config(args.config_path)
    elif args.action == 'reset':
        reset_config(args.config_path)
    elif args.action == 'preset':
        if not args.preset_name:
            print("[ERROR] preset action requires a preset name")
            print("Available presets: quick, marathon, mountain, cobbles")
            return 1
        create_preset(args.preset_name, args.config_path)

    return 0


if __name__ == "__main__":
    exit(main())
