"""
Config Manager - Utility for managing game configuration
"""

import argparse
import json
from pathlib import Path
from game_config import ConfigLoader, GameConfig


def show_config(config_path: str = "config.json"):
    """Display current configuration"""
    config = ConfigLoader.load(config_path)

    print("\n" + "="*60)
    print(f"Current Configuration ({config_path})")
    print("="*60)

    print("\nTILE CONFIGURATION:")
    print(f"  Tiles: {config.tile_config}")
    print(f"  Track length: {len(config.tile_config) * 20} fields")

    tile_names = {
        1: "Flat",
        2: "Mountaintop Finish",
        3: "Champs Elysees",
        4: "Up and Down",
        5: "Paris-Roubaix"
    }
    print("  Tile details:")
    for i, tile_id in enumerate(config.tile_config, 1):
        print(f"    Tile {i}: #{tile_id} - {tile_names.get(tile_id, 'Unknown')}")

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
    print(f"  At field 10, 30, 50... : {cp.checkpoint_10_cards} cards")
    print(f"  At field 20, 60, 100...: {cp.checkpoint_20_cards} cards")
    print(f"  At field 40, 80, 120...: {cp.checkpoint_40_cards} cards")

    print("\n" + "="*60 + "\n")


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

    presets = {
        "quick": {
            "tile_config": [1],
            "starting_hand": {
                "energy_cards": 5,
                "rouleur_cards": 2,
                "sprinter_cards": 2,
                "climber_cards": 2,
                "random_cards": 3
            },
            "checkpoints": {
                "checkpoint_10_cards": 5,
                "checkpoint_20_cards": 5,
                "checkpoint_40_cards": 5
            }
        },
        "marathon": {
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
        },
        "mountain": {
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
        },
        "cobbles": {
            "tile_config": [5, 5, 5],
            "starting_hand": {
                "energy_cards": 3,
                "rouleur_cards": 3,
                "sprinter_cards": 2,
                "climber_cards": 0,
                "random_cards": 2
            },
            "checkpoints": {
                "checkpoint_10_cards": 4,
                "checkpoint_20_cards": 4,
                "checkpoint_40_cards": 4
            }
        }
    }

    if preset_name not in presets:
        print(f"[ERROR] Unknown preset: {preset_name}")
        print(f"Available presets: {', '.join(presets.keys())}")
        return False

    config_dict = presets[preset_name]
    with open(output_path, 'w') as f:
        json.dump(config_dict, f, indent=2)

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
  python config_manager.py show                    # Show current config
  python config_manager.py validate                # Validate config.json
  python config_manager.py reset                   # Reset to defaults
  python config_manager.py preset quick            # Create quick game preset
  python config_manager.py preset marathon config.json  # Save marathon preset as config.json
        """
    )

    parser.add_argument(
        'action',
        choices=['show', 'validate', 'reset', 'preset'],
        help='Action to perform'
    )

    parser.add_argument(
        'preset_name',
        nargs='?',
        help='Preset name (for preset action): quick, marathon, mountain, cobbles'
    )

    parser.add_argument(
        'config_path',
        nargs='?',
        default='config.json',
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
