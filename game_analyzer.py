"""
Chasse Patate - Game Analyzer
Loads and replays games from logs with full visualization
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from game_state import GameState, Card, CardType, TerrainType, ActionType
from game_engine import GameEngine


# ---------------------------------------------------------------------------
# Player Colors (ANSI escape codes) - Same as play.py
# ---------------------------------------------------------------------------

class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Player colors (bright/bold versions for visibility)
    PLAYER_COLORS = [
        "\033[91m",  # Player 0: Bright Red
        "\033[94m",  # Player 1: Bright Blue
        "\033[92m",  # Player 2: Bright Green
        "\033[93m",  # Player 3: Bright Yellow
        "\033[95m",  # Player 4: Bright Magenta
    ]

    @classmethod
    def player(cls, player_id: int, text: str) -> str:
        """Wrap text in player's color"""
        color = cls.PLAYER_COLORS[player_id % len(cls.PLAYER_COLORS)]
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def bold(cls, text: str) -> str:
        """Make text bold"""
        return f"{cls.BOLD}{text}{cls.RESET}"

    @classmethod
    def player_bold(cls, player_id: int, text: str) -> str:
        """Wrap text in player's color and make it bold"""
        color = cls.PLAYER_COLORS[player_id % len(cls.PLAYER_COLORS)]
        return f"{cls.BOLD}{color}{text}{cls.RESET}"


# ---------------------------------------------------------------------------
# Display helpers - Same as play.py
# ---------------------------------------------------------------------------

TERRAIN_SYMBOLS = {
    TerrainType.FLAT: (".", "Flat"),
    TerrainType.COBBLES: ("~", "Cobbles"),
    TerrainType.CLIMB: ("^", "Climb"),
    TerrainType.DESCENT: ("v", "Descent"),
    TerrainType.SPRINT: ("S", "Sprint"),
    TerrainType.FINISH: ("F", "Finish"),
}


def print_track(state: GameState):
    """Print a visual representation of the race track with rider positions."""
    row_width = 20  # one row per tile (tiles are 20 fields)
    track_len = len(state.track)

    # Build a mapping: position -> list of (label, player_id) for coloring
    riders_by_pos: dict[int, list[tuple[str, int]]] = {}
    for player in state.players:
        for rider in player.riders:
            pos = rider.position
            label = f"{player.player_id}{rider.rider_type.value[0]}"
            riders_by_pos.setdefault(pos, []).append((label, player.player_id))

    print("\n--- Track ---")

    # Legend
    legend_parts = [f"{sym}={name}" for sym, name in TERRAIN_SYMBOLS.values()]
    print(f"  Legend: {', '.join(legend_parts)}")

    # Player color legend
    player_examples = []
    for i in range(state.num_players):
        example = Colors.player(i, f"P{i}")
        player_examples.append(example)
    print(f"  Players: {', '.join(player_examples)}  (e.g. 0R = Player 0 Rouleur)")
    print()

    for row_start in range(0, track_len, row_width):
        row_end = min(row_start + row_width, track_len)

        # Determine which tile this row belongs to
        tile_num = row_start // 20 + 1

        # --- Terrain line ---
        terrain_cells = []
        for pos in range(row_start, row_end):
            tile = state.track[pos]
            sym, _ = TERRAIN_SYMBOLS.get(tile.terrain, ("?", "?"))
            if tile.sprint_points:
                terrain_cells.append(f"[{sym}]")
            else:
                terrain_cells.append(f" {sym} ")
        terrain_line = "".join(terrain_cells)

        # --- Position number ruler (every 5 fields) ---
        ruler_line = ""
        for pos in range(row_start, row_end):
            if pos % 5 == 0:
                num_str = str(pos)
                ruler_line += num_str.ljust(3)
            else:
                ruler_line += "   "

        # --- Rider line ---
        rider_cells = []
        for pos in range(row_start, row_end):
            riders_here = riders_by_pos.get(pos, [])
            if riders_here:
                # Show up to 1 label per cell; overflow goes to extra line
                label, player_id = riders_here[0]
                colored_label = Colors.player(player_id, f"{label:>3}")
                rider_cells.append(colored_label)
            else:
                rider_cells.append("   ")

        rider_line = "".join(rider_cells)

        # Extra rider line if any position has >1 rider
        extra_lines = []
        max_stack = max((len(riders_by_pos.get(pos, [])) for pos in range(row_start, row_end)), default=0)
        for layer in range(1, max_stack):
            cells = []
            for pos in range(row_start, row_end):
                riders_here = riders_by_pos.get(pos, [])
                if layer < len(riders_here):
                    label, player_id = riders_here[layer]
                    colored_label = Colors.player(player_id, f"{label:>3}")
                    cells.append(colored_label)
                else:
                    cells.append("   ")
            extra_lines.append("".join(cells))

        # Print the row
        print(f"  Tile {tile_num}  (pos {row_start}-{row_end - 1})")
        print(f"  {ruler_line}")
        print(f"  {terrain_line}")
        print(f"  {rider_line}")
        for el in extra_lines:
            print(f"  {el}")
        print()

    # Finished riders (beyond track)
    finished = []
    for player in state.players:
        for rider in player.riders:
            if rider.position >= track_len:
                label = f"P{player.player_id}R{rider.rider_id}({rider.rider_type.value[0]})"
                finished.append(Colors.player(player.player_id, label))
    if finished:
        print(f"  Finished: {', '.join(finished)}")
        print()


def print_scoreboard(state: GameState):
    """Print scoreboard with all player information."""
    print("--- Scoreboard ---")
    for player in state.players:
        parts = []
        for rider in player.riders:
            tile = state.get_tile_at_position(rider.position)
            terrain = tile.terrain.value if tile else "?"
            parts.append(f"{rider.rider_type.value}@{rider.position}[{terrain}]")
        patron_tag = Colors.bold(" [El Patron]") if player.player_id == state.el_patron else ""
        player_label = Colors.player_bold(player.player_id, f"P{player.player_id} {player.name}")
        print(f"  {player_label}{patron_tag}: {', '.join(parts)}  | pts={player.points} hand={len(player.hand)}")
    print(f"  Deck: {len(state.deck)}  Discard: {len(state.discard_pile)}")
    print()


def format_hand_detailed(hand_data: Dict) -> str:
    """Format hand from log data (hand counts by type)."""
    lines = []
    for ctype in ["energy", "climber", "rouleur", "sprinter"]:
        count = hand_data.get(ctype, 0)
        if count > 0:
            label = ctype.capitalize()
            lines.append(f"  {label} x{count}")
    return "\n".join(lines) if lines else "  (empty)"


# ---------------------------------------------------------------------------
# Game Log Loader
# ---------------------------------------------------------------------------

class GameAnalyzer:
    """Loads and analyzes game logs with full visualization."""

    def __init__(self, log_dir: str = "game_logs"):
        self.log_dir = Path(log_dir)

    def list_games(self, pattern: str = "*.json") -> List[Path]:
        """List all game log files."""
        return sorted(self.log_dir.glob(pattern))

    def load_game(self, game_file: str) -> Dict:
        """Load a game log from file."""
        path = Path(game_file)
        if not path.exists():
            # Try in log_dir
            path = self.log_dir / game_file

        if not path.exists():
            raise FileNotFoundError(f"Game log not found: {game_file}")

        with open(path, 'r') as f:
            return json.load(f)

    def replay_game(self, game_file: str, pause_between_turns: bool = True,
                    pause_between_rounds: bool = True):
        """Replay a game with full visualization, turn by turn."""
        game_log = self.load_game(game_file)

        # Print game header
        print("=" * 70)
        print(Colors.bold("  GAME REPLAY"))
        print("=" * 70)
        print(f"  Game ID: {game_log.get('game_id', 'N/A')}")
        print(f"  Timestamp: {game_log.get('timestamp', 'N/A')}")
        print(f"  Players: {game_log.get('num_players', 'N/A')}")
        print(f"  Mode: {game_log.get('mode', 'simulated')}")
        print()

        # Print agents
        print("  Agents:")
        for agent in game_log.get('agents', []):
            player_id = agent['player_id']
            agent_name = agent['type']
            colored_name = Colors.player_bold(player_id, f"  Player {player_id}: {agent_name}")
            print(colored_name)
        print()

        # Print final result summary
        final = game_log.get('final_result', {})
        print("  Final Result:")
        print(f"    Winner: {final.get('winner', 'N/A')} ({final.get('winner_score', 0)} points)")
        print(f"    Reason: {final.get('game_over_reason', 'N/A')}")
        print(f"    Rounds: {final.get('total_rounds', 0)}")
        print(f"    Turns: {final.get('total_turns', 0)}")
        print("=" * 70)
        print()

        if pause_between_rounds:
            input("Press Enter to start replay...")

        # Replay move history
        move_history = game_log.get('move_history', [])
        current_round = 0

        for i, turn_data in enumerate(move_history):
            round_num = turn_data['round']
            turn_num = turn_data['turn']
            player_id = turn_data['player']
            move = turn_data['move']
            state_data = turn_data['state']

            # Print round header when round changes
            if round_num != current_round:
                current_round = round_num
                el_patron = state_data.get('el_patron', 0)
                agent_name = game_log['agents'][el_patron]['type']
                patron_label = Colors.player_bold(el_patron, f"{agent_name} (Player {el_patron})")

                print(f"\n{'~'*70}")
                print(f"  ROUND {round_num}  |  El Patron: {patron_label}")
                print(f"{'~'*70}")

                if pause_between_rounds and i > 0:
                    input("Press Enter to continue to next round...")

            # Print turn header
            agent_name = game_log['agents'][player_id]['type']
            player_label = Colors.player_bold(player_id, f"{agent_name} (P{player_id})")

            print(f"\n{'='*70}")
            print(f"  Turn {turn_num}: {player_label}")
            print(f"{'='*70}")

            # Print all players' hands
            print("\n--- All Players' Hands ---")
            hands_detailed = state_data.get('player_hands_detailed', [])
            for pid, hand_data in enumerate(hands_detailed):
                p_label = Colors.player_bold(pid, f"Player {pid} ({game_log['agents'][pid]['type']})")
                print(f"{p_label}:")
                print(format_hand_detailed(hand_data))
            print()

            # Reconstruct game state for track visualization
            state = self._reconstruct_state(game_log, state_data)

            # Print track
            print_track(state)
            print_scoreboard(state)

            # Print the move
            action = move.get('action', '?')
            rider = move.get('rider', '?')
            old_pos = move.get('old_position', '?')
            new_pos = move.get('new_position', '?')
            movement = move.get('movement', 0)
            cards_played = move.get('cards_played', [])

            print(f"\n--- Move Details ---")
            print(f"  Action: {Colors.bold(action)}")
            print(f"  Rider: {Colors.player(player_id, rider)} ({move.get('rider_type', '?')})")

            if cards_played:
                cards_str = ", ".join(cards_played)
                print(f"  Cards played: {cards_str} ({len(cards_played)} cards)")
            else:
                print(f"  Cards played: (none)")

            print(f"  Movement: {old_pos} -> {new_pos} (+{movement})")

            # Print additional move details
            pts = move.get('points_earned', 0)
            if pts:
                print(f"  Points earned: +{pts} (sprint/finish)")

            drafters = move.get('drafting_riders')
            if drafters:
                print(f"  Drafters:")
                for d in drafters:
                    print(f"    - {d['rider']}: {d['old_position']} -> {d['new_position']}")

            cards_drawn = move.get('cards_drawn', 0)
            if isinstance(cards_drawn, list):
                # TeamCar returns list of card type strings
                print(f"  Cards drawn: {', '.join(cards_drawn)}")
                discarded = move.get('card_discarded')
                if discarded:
                    print(f"  Card discarded: {discarded}")
            elif cards_drawn and cards_drawn > 0:
                print(f"  Cards drawn from checkpoints: {cards_drawn}")

            if pause_between_turns:
                input("\nPress Enter for next turn...")

        # Print final summary
        print(f"\n{'='*70}")
        print(Colors.bold("  GAME OVER"))
        print(f"{'='*70}")
        print()
        print("Final scores:")
        for player_id, agent in enumerate(game_log['agents']):
            label = f"Player {player_id}"
            score = final['final_scores'].get(label, 0)
            player_label = Colors.player_bold(player_id, f"{label} ({agent['type']})")
            print(f"  {player_label}: {score} points")
        print()
        print(f"Winner: {Colors.bold(final['winner'])} with {final['winner_score']} points!")
        print(f"Reason: {final.get('game_over_reason', 'N/A')}")
        print(f"Total rounds: {final.get('total_rounds', 0)}")
        print(f"Total turns: {final.get('total_turns', 0)}")
        print()

    def _reconstruct_state(self, game_log: Dict, state_data: Dict) -> GameState:
        """Reconstruct a GameState object from log data for visualization."""
        num_players = game_log['num_players']
        state = GameState(num_players=num_players)

        # Set round and el_patron
        state.current_round = state_data.get('round', 1)
        state.el_patron = state_data.get('el_patron', 0)

        # Set player names and scores
        for i, agent in enumerate(game_log['agents']):
            state.players[i].name = agent['type']
            scores = state_data.get('player_scores', [])
            if i < len(scores):
                state.players[i].points = scores[i]

        # Set rider positions
        rider_positions = state_data.get('rider_positions', {})
        for rider_key, rider_data in rider_positions.items():
            # Parse rider key (e.g., "P0R1")
            parts = rider_key.replace('P', '').replace('R', ' ').split()
            if len(parts) == 2:
                player_id = int(parts[0])
                rider_id = int(parts[1])
                position = rider_data.get('position', 0)

                if player_id < len(state.players):
                    for rider in state.players[player_id].riders:
                        if rider.rider_id == rider_id:
                            rider.position = position
                            break

        return state


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    """Command-line interface for game analyzer."""
    import sys

    analyzer = GameAnalyzer()

    if len(sys.argv) < 2:
        # List available games
        games = analyzer.list_games()
        print("Available game logs:")
        for game in games[:20]:  # Show first 20
            print(f"  {game.name}")
        if len(games) > 20:
            print(f"  ... and {len(games) - 20} more")
        print()
        print("Usage:")
        print(f"  python {sys.argv[0]} <game_file>")
        print(f"  python {sys.argv[0]} <game_file> --no-pause-turns")
        print(f"  python {sys.argv[0]} <game_file> --no-pause")
        print()
        print("Examples:")
        print(f"  python {sys.argv[0]} game_0.json")
        print(f"  python {sys.argv[0]} play_0.json")
        print(f"  python {sys.argv[0]} game_logs/game_0.json --no-pause-turns")
        return

    game_file = sys.argv[1]
    pause_turns = "--no-pause-turns" not in sys.argv and "--no-pause" not in sys.argv
    pause_rounds = "--no-pause" not in sys.argv

    try:
        analyzer.replay_game(game_file, pause_between_turns=pause_turns,
                           pause_between_rounds=pause_rounds)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error replaying game: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
