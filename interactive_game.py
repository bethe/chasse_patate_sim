"""
Chasse Patate - Interactive Game Viewer
Displays the game with colored players and a visual track representation.
Supports human players and AI bots.
"""

import os
import sys
import time
from typing import List, Dict, Optional
from game_state import GameState, TerrainType, CardType, Card, PlayMode, ActionType
from game_engine import GameEngine, Move
from agents import Agent, create_agent, get_available_agents


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal coloring"""
    # Reset
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Player colors (bright versions for better visibility)
    PLAYER_COLORS = [
        '\033[91m',  # Bright Red - Player 0
        '\033[94m',  # Bright Blue - Player 1
        '\033[92m',  # Bright Green - Player 2
        '\033[93m',  # Bright Yellow - Player 3
        '\033[95m',  # Bright Magenta - Player 4
    ]

    # Player background colors for track display
    PLAYER_BG_COLORS = [
        '\033[41m',  # Red background - Player 0
        '\033[44m',  # Blue background - Player 1
        '\033[42m',  # Green background - Player 2
        '\033[43m',  # Yellow background - Player 3
        '\033[45m',  # Magenta background - Player 4
    ]

    # Terrain colors
    TERRAIN_FLAT = '\033[37m'      # White/Light gray
    TERRAIN_CLIMB = '\033[33m'     # Yellow/Orange
    TERRAIN_COBBLES = '\033[90m'   # Dark gray
    TERRAIN_DESCENT = '\033[36m'   # Cyan
    TERRAIN_SPRINT = '\033[35m'    # Magenta
    TERRAIN_FINISH = '\033[32m'    # Green

    # Background for terrain
    BG_FLAT = '\033[47m'           # White background
    BG_CLIMB = '\033[43m'          # Yellow background
    BG_COBBLES = '\033[100m'       # Dark gray background
    BG_DESCENT = '\033[46m'        # Cyan background
    BG_SPRINT = '\033[45m'         # Magenta background
    BG_FINISH = '\033[42m'         # Green background

    @classmethod
    def player_color(cls, player_id: int) -> str:
        """Get color for a player"""
        return cls.PLAYER_COLORS[player_id % len(cls.PLAYER_COLORS)]

    @classmethod
    def player_bg(cls, player_id: int) -> str:
        """Get background color for a player"""
        return cls.PLAYER_BG_COLORS[player_id % len(cls.PLAYER_BG_COLORS)]

    @classmethod
    def terrain_color(cls, terrain: TerrainType) -> str:
        """Get color for a terrain type"""
        terrain_colors = {
            TerrainType.FLAT: cls.TERRAIN_FLAT,
            TerrainType.CLIMB: cls.TERRAIN_CLIMB,
            TerrainType.COBBLES: cls.TERRAIN_COBBLES,
            TerrainType.DESCENT: cls.TERRAIN_DESCENT,
            TerrainType.SPRINT: cls.TERRAIN_SPRINT,
            TerrainType.FINISH: cls.TERRAIN_FINISH,
        }
        return terrain_colors.get(terrain, cls.TERRAIN_FLAT)

    @classmethod
    def terrain_bg(cls, terrain: TerrainType) -> str:
        """Get background color for a terrain type"""
        terrain_bgs = {
            TerrainType.FLAT: cls.BG_FLAT,
            TerrainType.CLIMB: cls.BG_CLIMB,
            TerrainType.COBBLES: cls.BG_COBBLES,
            TerrainType.DESCENT: cls.BG_DESCENT,
            TerrainType.SPRINT: cls.BG_SPRINT,
            TerrainType.FINISH: cls.BG_FINISH,
        }
        return terrain_bgs.get(terrain, cls.BG_FLAT)


def enable_windows_ansi():
    """Enable ANSI escape codes on Windows"""
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_card(card: Card, terrain: TerrainType = None) -> str:
    """Format a card for display."""
    if card.is_energy_card():
        return "Energy (1)"
    label = card.card_type.value
    if terrain:
        pull_val = card.get_movement(terrain, PlayMode.PULL)
        atk_val = card.get_movement(terrain, PlayMode.ATTACK)
        return f"{label} (Pull:{pull_val} Atk:{atk_val})"
    return f"{label}"


def format_hand(hand: List[Card], terrain: TerrainType = None) -> str:
    """Format the player's hand grouped by card type."""
    by_type = {}
    for card in hand:
        key = card.card_type.value
        by_type.setdefault(key, []).append(card)
    lines = []
    for ctype in ["Energy", "Climber", "Rouleur", "Sprinter"]:
        cards = by_type.get(ctype, [])
        if cards:
            if terrain:
                label = format_card(cards[0], terrain)
            else:
                label = format_card(cards[0])
            lines.append(f"  {label}  x{len(cards)}")
    return "\n".join(lines) if lines else "  (empty)"


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def prompt_choice(prompt: str, options: list, allow_cancel: bool = False) -> int:
    """Ask user to pick one option by number. Returns index."""
    while True:
        print(prompt)
        for i, option in enumerate(options):
            print(f"  [{i}] {option}")
        if allow_cancel:
            print(f"  [c] Cancel / go back")
        raw = input("> ").strip().lower()
        if allow_cancel and raw == "c":
            return -1
        try:
            idx = int(raw)
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print("Invalid choice, try again.\n")


def prompt_multi_choice(prompt: str, options: list, min_sel: int = 1,
                        max_sel: int = None, allow_cancel: bool = False) -> Optional[List[int]]:
    """Ask user to pick multiple options (comma-separated). Returns list of indices, or None if cancelled."""
    if max_sel is None:
        max_sel = len(options)
    while True:
        print(prompt)
        for i, option in enumerate(options):
            print(f"  [{i}] {option}")
        hint = f"  (select {min_sel}-{max_sel}, comma-separated)"
        if allow_cancel:
            hint += "  |  [b] go back"
        print(hint)
        raw = input("> ").strip().lower()
        if allow_cancel and raw == "b":
            return None
        try:
            indices = [int(x.strip()) for x in raw.split(",")]
            if min_sel <= len(indices) <= max_sel and all(0 <= i < len(options) for i in indices):
                return indices
        except ValueError:
            pass
        print("Invalid selection, try again.\n")


# ---------------------------------------------------------------------------
# Human Agent
# ---------------------------------------------------------------------------

class HumanAgent(Agent):
    """Interactive human player with colored output."""

    BACK = "BACK"  # sentinel for go-back

    def __init__(self, player_id: int):
        super().__init__(player_id, "Human")

    def choose_move(self, engine: GameEngine, player) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            print("  No valid moves available - skipping turn.")
            return None

        riders = player.riders
        terrain = self._current_terrain(engine, riders[0])

        color = Colors.player_color(self.player_id)
        print(f"\n{color}{Colors.BOLD}{'='*50}")
        print(f"  YOUR TURN  (Player {self.player_id})")
        print(f"{'='*50}{Colors.RESET}")
        print(f"Hand ({len(player.hand)} cards):")
        print(format_hand(player.hand, terrain))
        print()

        while True:
            # --- Step 1: pick rider ------------------------------------
            rider_set = sorted(set(m.rider for m in valid_moves),
                               key=lambda r: r.rider_id)
            if len(rider_set) == 1:
                chosen_rider = rider_set[0]
                print(f"  Rider: {chosen_rider.rider_type.value} @ pos {chosen_rider.position}")
            else:
                rider_labels = [f"{r.rider_type.value} @ pos {r.position}" for r in rider_set]
                rider_idx = prompt_choice("Choose rider:", rider_labels)
                chosen_rider = rider_set[rider_idx]

            # --- Step 2: pick action (can go back to rider) ------------
            result = self._step_pick_action(engine, player, valid_moves,
                                            chosen_rider, terrain,
                                            can_go_back=len(rider_set) > 1)
            if result is self.BACK:
                continue  # restart from rider selection
            return result

    def _step_pick_action(self, engine, player, valid_moves, rider, terrain,
                          can_go_back: bool):
        """Pick an action for the chosen rider. Returns Move, None, or BACK."""
        rider_moves = [m for m in valid_moves if m.rider == rider]
        team_moves_involving_rider = [
            m for m in valid_moves
            if m.action_type in (ActionType.TEAM_DRAFT, ActionType.TEAM_PULL)
            and m.rider != rider
            and rider in (m.drafting_riders or [])
        ]

        all_relevant = rider_moves + team_moves_involving_rider
        available_actions = sorted(set(m.action_type for m in all_relevant),
                                   key=lambda a: a.value)

        while True:
            action_labels = [a.value for a in available_actions]
            action_idx = prompt_choice("Choose action:", action_labels,
                                       allow_cancel=can_go_back)
            if action_idx == -1:
                return self.BACK

            chosen_action = available_actions[action_idx]
            filtered = [m for m in all_relevant if m.action_type == chosen_action]

            result = self._step_pick_details(engine, player, chosen_action,
                                             filtered, rider, terrain)
            if result is self.BACK:
                continue
            return result

    def _step_pick_details(self, engine, player, action, filtered, rider, terrain):
        """Handle the detail selection for a chosen action. Returns Move or BACK."""
        if action == ActionType.DRAFT:
            return filtered[0]

        if action == ActionType.TEAM_CAR:
            return self._handle_team_car(engine, player, rider, terrain)

        if action == ActionType.TEAM_DRAFT:
            return self._handle_team_draft(filtered, rider)

        if action == ActionType.TEAM_PULL:
            return self._handle_team_pull(engine, player, filtered, rider, terrain)

        # Pull or Attack: pick cards
        return self._handle_card_action(engine, player, action, rider, terrain)

    def _handle_card_action(self, engine, player, action, rider, terrain):
        """Handle Pull (1-3 cards) or Attack (exactly 3 cards)."""
        playable = [c for c in player.hand if c.can_play_on_rider(rider.rider_type)]
        card_labels = [format_card(c, terrain) + (" [not playable]" if c not in playable else "")
                       for c in player.hand]

        if action == ActionType.ATTACK:
            min_cards = max_cards = 3
        else:
            min_cards, max_cards = 1, min(3, len(playable))

        while True:
            indices = prompt_multi_choice(
                f"Select {min_cards}-{max_cards} cards to play:",
                card_labels, min_sel=min_cards, max_sel=max_cards,
                allow_cancel=True)
            if indices is None:
                return self.BACK

            chosen_cards = [player.hand[i] for i in indices]
            if any(c not in playable for c in chosen_cards):
                print("  Some selected cards are not playable on this rider. Try again.\n")
                continue

            mode = PlayMode.PULL if action == ActionType.PULL else PlayMode.ATTACK
            total = sum(c.get_movement(terrain, mode) if not c.is_energy_card() else 1
                        for c in chosen_cards)
            print(f"  -> Total movement: {total}")
            return Move(action, rider, chosen_cards)

    def _handle_team_car(self, engine, player, rider, terrain):
        """TeamCar: draw 2, discard 1."""
        peek_cards = []
        for i in range(min(2, len(engine.state.deck))):
            peek_cards.append(engine.state.deck[-(i + 1)])

        print(f"\n  Cards that will be drawn: "
              f"{', '.join(format_card(c, terrain) for c in peek_cards)}")

        full_hand = list(player.hand) + peek_cards
        card_labels = [format_card(c, terrain) for c in full_hand]
        idx = prompt_choice("Pick a card to discard from your updated hand:",
                            card_labels, allow_cancel=True)
        if idx == -1:
            return self.BACK
        discard_card = full_hand[idx]
        return Move(ActionType.TEAM_CAR, rider, [discard_card])

    def _handle_team_draft(self, filtered, rider):
        """TeamDraft: pick which riders draft together."""
        combos = []
        for m in filtered:
            all_riders = [m.rider] + m.drafting_riders
            combo_label = ", ".join(f"{r.rider_type.value}@{r.position}" for r in all_riders)
            combos.append((combo_label, m))
        labels = [c[0] for c in combos]
        idx = prompt_choice("Choose which riders draft together:", labels,
                            allow_cancel=True)
        if idx == -1:
            return self.BACK
        return combos[idx][1]

    def _handle_team_pull(self, engine, player, filtered, rider, terrain):
        """TeamPull: pick drafters, then pick cards for the pull."""
        drafter_sets = []
        seen = set()
        for m in filtered:
            key = tuple(sorted(r.rider_id for r in m.drafting_riders))
            if key not in seen:
                seen.add(key)
                drafter_sets.append(m.drafting_riders)

        while True:
            if len(drafter_sets) == 1:
                chosen_drafters = drafter_sets[0]
                print(f"  Drafters: {', '.join(f'{r.rider_type.value}@{r.position}' for r in chosen_drafters)}")
            else:
                labels = [", ".join(f"{r.rider_type.value}@{r.position}" for r in ds) for ds in drafter_sets]
                idx = prompt_choice("Choose drafting riders:", labels,
                                    allow_cancel=True)
                if idx == -1:
                    return self.BACK
                chosen_drafters = drafter_sets[idx]

            playable = [c for c in player.hand if c.can_play_on_rider(rider.rider_type)]
            card_labels = [format_card(c, terrain) + (" [not playable]" if c not in playable else "")
                           for c in player.hand]
            min_cards, max_cards = 1, min(3, len(playable))

            indices = prompt_multi_choice(
                f"Select {min_cards}-{max_cards} cards for the pull:",
                card_labels, min_sel=min_cards, max_sel=max_cards,
                allow_cancel=True)
            if indices is None:
                if len(drafter_sets) == 1:
                    return self.BACK
                continue

            chosen_cards = [player.hand[i] for i in indices]
            if any(c not in playable for c in chosen_cards):
                print("  Some selected cards are not playable on this rider. Try again.\n")
                continue

            total = sum(c.get_movement(terrain, PlayMode.PULL) if not c.is_energy_card() else 1
                        for c in chosen_cards)
            print(f"  -> Total movement for all riders: {total}")
            return Move(ActionType.TEAM_PULL, rider, chosen_cards, list(chosen_drafters))

    @staticmethod
    def _current_terrain(engine, rider):
        tile = engine.state.get_tile_at_position(rider.position)
        return tile.terrain if tile else TerrainType.FLAT


# ---------------------------------------------------------------------------
# Interactive Game class with colored display
# ---------------------------------------------------------------------------

class InteractiveGame:
    """Interactive game viewer with colored display"""

    def __init__(self, num_players: int = 2, tile_config: List[int] = None,
                 delay: float = 0.5, auto_play: bool = True):
        enable_windows_ansi()

        self.num_players = num_players
        self.tile_config = tile_config
        self.delay = delay
        self.auto_play = auto_play

        self.state = None
        self.engine = None
        self.agents = []

    def setup_game(self, agent_types: List[str] = None):
        """Set up a new game with specified agents or interactively"""
        self.state = GameState(self.num_players, self.tile_config)
        self.engine = GameEngine(self.state)

        self.agents = []
        for i, agent_type in enumerate(agent_types):
            if agent_type == 'human':
                agent = HumanAgent(i)
            else:
                agent = create_agent(agent_type, i)
            self.agents.append(agent)
            self.state.players[i].name = agent.name

    def get_rider_symbol(self, rider_type: CardType) -> str:
        """Get a symbol for rider type"""
        symbols = {
            CardType.ROULEUR: 'R',
            CardType.SPRINTER: 'S',
            CardType.CLIMBER: 'C',
        }
        return symbols.get(rider_type, '?')

    def render_track(self) -> str:
        """Render the track with rider positions, split by tiles.

        Features:
        - Split into tiles (20 fields each)
        - Position ruler at top (0, 5, 10, 15, ...)
        - Terrain row with colored backgrounds
        - Separate rider rows with labels like P0S, P1R, etc.
        """
        lines = []
        track_length = self.state.track_length
        tile_width = 20  # Each tile is 20 fields

        # Terrain symbols
        terrain_symbols = {
            TerrainType.FLAT: '.',
            TerrainType.CLIMB: '^',
            TerrainType.COBBLES: '~',
            TerrainType.DESCENT: 'v',
            TerrainType.SPRINT: 'S',
            TerrainType.FINISH: 'F',
        }

        # Build a mapping: position -> list of riders
        riders_by_pos: Dict[int, List] = {}
        for player in self.state.players:
            for rider in player.riders:
                pos = rider.position
                if pos not in riders_by_pos:
                    riders_by_pos[pos] = []
                riders_by_pos[pos].append(rider)

        # Header with legend
        lines.append(f"{Colors.BOLD}--- Track ---{Colors.RESET}")
        lines.append(f"  Legend: {Colors.BG_FLAT}.=Flat{Colors.RESET} "
                    f"{Colors.BG_CLIMB}^=Climb{Colors.RESET} "
                    f"{Colors.BG_COBBLES}~=Cobbles{Colors.RESET} "
                    f"{Colors.BG_DESCENT}v=Descent{Colors.RESET} "
                    f"{Colors.BG_SPRINT}[S]=Sprint{Colors.RESET} "
                    f"{Colors.BG_FINISH}[F]=Finish{Colors.RESET}")

        # Player color legend
        player_legend = "  Riders: "
        for i in range(self.num_players):
            color = Colors.player_color(i)
            player_legend += f"{color}P{i}R=Rouleur P{i}S=Sprinter P{i}C=Climber{Colors.RESET}  "
        lines.append(player_legend)
        lines.append("")

        # Process each tile
        num_tiles = (track_length + tile_width - 1) // tile_width

        for tile_num in range(num_tiles):
            start_pos = tile_num * tile_width
            end_pos = min(start_pos + tile_width, track_length)

            # Tile header
            lines.append(f"  {Colors.BOLD}Tile {tile_num + 1}{Colors.RESET}  (pos {start_pos}-{end_pos - 1})")

            # Position ruler row (every 5 positions)
            ruler_line = "       "  # Indent for label column
            for pos in range(start_pos, end_pos):
                if pos % 5 == 0:
                    ruler_line += f"{pos:<3}"
                else:
                    ruler_line += "   "
            lines.append(f"{Colors.DIM}{ruler_line}{Colors.RESET}")

            # Terrain row
            terrain_line = "       "  # Indent for label column
            for pos in range(start_pos, end_pos):
                tile = self.state.get_tile_at_position(pos)
                if tile:
                    terrain = tile.terrain
                    bg = Colors.terrain_bg(terrain)
                    sym = terrain_symbols.get(terrain, '?')

                    # Highlight sprint/finish with brackets
                    if terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
                        terrain_line += f"{bg}[{sym}]{Colors.RESET}"
                    else:
                        terrain_line += f"{bg} {sym} {Colors.RESET}"
                else:
                    terrain_line += "   "
            lines.append(terrain_line)

            # Rider rows - one row per "layer" of stacked riders
            max_stack = max((len(riders_by_pos.get(pos, [])) for pos in range(start_pos, end_pos)), default=0)

            for layer in range(max_stack):
                rider_line = "       "  # Indent for label column
                has_content = False

                for pos in range(start_pos, end_pos):
                    riders = riders_by_pos.get(pos, [])
                    if layer < len(riders):
                        rider = riders[layer]
                        color = Colors.player_color(rider.player_id)
                        rider_type_char = self.get_rider_symbol(rider.rider_type)
                        label = f"P{rider.player_id}{rider_type_char}"
                        rider_line += f"{color}{Colors.BOLD}{label}{Colors.RESET}"
                        has_content = True
                    else:
                        rider_line += "   "

                if has_content:
                    lines.append(rider_line)

            lines.append("")  # Blank line between tiles

        # Show finished riders (beyond track)
        finished = []
        for player in self.state.players:
            for rider in player.riders:
                if rider.position >= track_length:
                    color = Colors.player_color(player.player_id)
                    rider_type_char = self.get_rider_symbol(rider.rider_type)
                    finished.append(f"{color}P{player.player_id}{rider_type_char}{Colors.RESET}")
        if finished:
            lines.append(f"  {Colors.BOLD}Finished:{Colors.RESET} {', '.join(finished)}")
            lines.append("")

        return "\n".join(lines)

    def render_players(self) -> str:
        """Render player information panel"""
        lines = []
        lines.append(f"{Colors.BOLD}{'='*50}{Colors.RESET}")
        lines.append(f"{Colors.BOLD}PLAYERS{Colors.RESET}")
        lines.append(f"{Colors.BOLD}{'='*50}{Colors.RESET}")

        for player in self.state.players:
            color = Colors.player_color(player.player_id)
            lines.append(f"\n{color}{Colors.BOLD}Player {player.player_id}: {player.name}{Colors.RESET}")
            lines.append(f"  Points: {player.points} | Cards: {len(player.hand)}")

            for rider in player.riders:
                rider_type = self.get_rider_symbol(rider.rider_type)
                tile = self.state.get_tile_at_position(rider.position)
                terrain = tile.terrain.value if tile else "?"
                lines.append(f"  {color}{rider_type}{Colors.RESET} at pos {rider.position} ({terrain})")

        return "\n".join(lines)

    def render_legend(self) -> str:
        """Render a compact legend (main legend is now in track header)"""
        lines = []
        # Player colors reminder
        player_colors = f"{Colors.BOLD}Players:{Colors.RESET} "
        for i in range(self.num_players):
            color = Colors.player_color(i)
            player_colors += f"{color}P{i}{Colors.RESET} "
        lines.append(player_colors)

        return "\n".join(lines)

    def render_move(self, move: Move, result: dict) -> str:
        """Render information about a move"""
        lines = []

        player_id = move.rider.player_id
        color = Colors.player_color(player_id)

        action = result.get('action', 'Unknown')
        rider_type = result.get('rider_type', '?')
        old_pos = result.get('old_position', 0)
        new_pos = result.get('new_position', 0)
        movement = result.get('movement', 0)
        points = result.get('points_earned', 0)

        lines.append(f"\n{color}{Colors.BOLD}>> Player {player_id} ({action}){Colors.RESET}")
        lines.append(f"   {rider_type} moved {old_pos} -> {new_pos} (+{movement})")

        if points > 0:
            lines.append(f"   {Colors.BOLD}+{points} POINTS!{Colors.RESET}")

        if 'drafting_riders' in result and result['drafting_riders']:
            for drafter in result['drafting_riders']:
                lines.append(f"   Draft: {drafter['rider']} {drafter['old_position']} -> {drafter['new_position']}")

        if result.get('cards_played'):
            lines.append(f"   Cards: {', '.join(result['cards_played'])}")

        return "\n".join(lines)

    def render_game_state(self, last_move_info: str = "") -> str:
        """Render the complete game state"""
        lines = []

        lines.append(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        lines.append(f"{Colors.BOLD}  CHASSE PATATE - Turn {self.state.current_turn}{Colors.RESET}")
        lines.append(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

        lines.append(self.render_track())
        lines.append(self.render_players())
        lines.append(self.render_legend())

        if last_move_info:
            lines.append(last_move_info)

        return "\n".join(lines)

    def has_human_player(self) -> bool:
        """Check if any player is human"""
        return any(isinstance(agent, HumanAgent) for agent in self.agents)

    def play_game(self):
        """Play the game with visual output"""
        turn_count = 0
        max_turns = 150
        last_move_info = ""

        # Initial display
        clear_screen()
        print(self.render_game_state())

        if self.has_human_player():
            input("\nPress Enter to start...")
        elif not self.auto_play:
            input("\nPress Enter to start...")
        else:
            time.sleep(self.delay)

        while not self.state.game_over and turn_count < max_turns:
            current_player = self.state.get_current_player()
            agent = self.agents[current_player.player_id]
            is_human = isinstance(agent, HumanAgent)

            # Show board before human turn
            if is_human:
                clear_screen()
                print(self.render_game_state(last_move_info))

            # Agent chooses move
            move = agent.choose_move(self.engine, current_player)

            if move is None:
                if self.state.check_game_over():
                    break
                self.state.advance_turn()
                turn_count += 1
                continue

            # Execute move
            result = self.engine.execute_move(move)

            # Render move info
            last_move_info = self.render_move(move, result)

            # Update display for bots
            if not is_human:
                clear_screen()
                print(self.render_game_state(last_move_info))

            # Check game over
            self.state.check_game_over()

            # Wait
            if is_human:
                pass  # Human already interacted
            elif not self.auto_play:
                input("\nPress Enter for next turn...")
            else:
                time.sleep(self.delay)

            # Next turn
            self.state.advance_turn()
            turn_count += 1

        # Game over
        clear_screen()
        print(self.render_game_state())
        self.print_final_results()

    def print_final_results(self):
        """Print final game results"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}  GAME OVER!{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

        sorted_players = sorted(self.state.players, key=lambda p: p.points, reverse=True)

        for rank, player in enumerate(sorted_players, 1):
            color = Colors.player_color(player.player_id)
            medal = ""
            if rank == 1:
                medal = f" {Colors.BOLD}[WINNER]{Colors.RESET}"

            print(f"  {rank}. {color}{Colors.BOLD}{player.name}{Colors.RESET}: "
                  f"{player.points} points{medal}")

        print()


# ---------------------------------------------------------------------------
# Game setup
# ---------------------------------------------------------------------------

def setup_game_interactive():
    """Interactive game setup: pick player count and assign human/bot slots."""
    enable_windows_ansi()

    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  CHASSE PATATE - Interactive Play{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    print()

    # Number of players
    num_players = None
    while num_players is None:
        raw = input("How many players? (2-5): ").strip()
        try:
            n = int(raw)
            if 2 <= n <= 5:
                num_players = n
        except ValueError:
            pass

    bot_types = get_available_agents()
    slot_options = ["human"] + bot_types
    agent_types: List[str] = []

    for slot in range(num_players):
        color = Colors.player_color(slot)
        print(f"\n{color}{Colors.BOLD}Player {slot}:{Colors.RESET}")
        for i, option in enumerate(slot_options):
            print(f"  [{i}] {option}")

        while True:
            raw = input("> ").strip()
            try:
                idx = int(raw)
                if 0 <= idx < len(slot_options):
                    choice = slot_options[idx]
                    agent_types.append(choice)
                    print(f"  -> {color}Player {slot}{Colors.RESET} = {choice}")
                    break
            except ValueError:
                pass
            print("Invalid choice, try again.")

    return num_players, agent_types


def main():
    """Main entry point for interactive game"""
    import argparse

    enable_windows_ansi()

    parser = argparse.ArgumentParser(description='Chasse Patate - Interactive Game Viewer')
    parser.add_argument('--agents', '-a', nargs='+', default=None,
                       help='Agent types for each player (e.g., human claudebot wheelsucker)')
    parser.add_argument('--delay', '-d', type=float, default=0.8,
                       help='Delay between turns in seconds (default: 0.8)')
    parser.add_argument('--manual', '-m', action='store_true',
                       help='Manual mode - press Enter between turns')
    parser.add_argument('--list-agents', '-l', action='store_true',
                       help='List available agent types and exit')

    args = parser.parse_args()

    # List agents if requested
    if args.list_agents:
        print(f"\n{Colors.BOLD}Available agent types:{Colors.RESET}")
        print(f"  {Colors.BOLD}human{Colors.RESET} - Play as a human")
        for i, agent in enumerate(get_available_agents()):
            color = Colors.player_color(i % 5)
            print(f"  {color}{agent}{Colors.RESET}")
        print()
        return

    # If no agents specified, run interactive setup
    if args.agents is None:
        num_players, agent_types = setup_game_interactive()
    else:
        # Validate agents
        agent_types = args.agents
        available = ['human'] + get_available_agents()
        for agent in agent_types:
            if agent not in available:
                print(f"Error: Unknown agent type '{agent}'")
                print(f"Available: {', '.join(available)}")
                return
        num_players = len(agent_types)

    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  GAME START  ({num_players} players){Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

    # Show game setup
    print("Players:")
    for i, agent in enumerate(agent_types):
        color = Colors.player_color(i)
        print(f"  {color}Player {i}: {agent}{Colors.RESET}")

    has_human = 'human' in agent_types
    if has_human:
        print(f"\nMode: Interactive (human player)")
    else:
        print(f"\nDelay: {args.delay}s {'(manual mode)' if args.manual else '(auto-play)'}")

    print("(Press Ctrl+C to quit)")
    print()

    game = InteractiveGame(
        num_players=num_players,
        delay=args.delay,
        auto_play=not args.manual and not has_human
    )

    game.setup_game(agent_types)

    try:
        game.play_game()
    except KeyboardInterrupt:
        print("\n\nGame interrupted.")


if __name__ == "__main__":
    main()
