"""
Chasse Patate - Interactive Play
Play against AI bots in the terminal.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from itertools import combinations
from game_state import GameState, Card, CardType, ActionType, PlayMode, Rider, Player, TerrainType
from game_engine import GameEngine, Move
from agents import Agent, create_agent, get_available_agents


# ---------------------------------------------------------------------------
# Game Logger for interactive play
# ---------------------------------------------------------------------------

class PlayLogger:
    """Logs interactive game information in the same format as simulator"""

    def __init__(self, log_dir: str = "game_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.game_info = {}
        self.move_history = []

    def _get_next_play_id(self) -> int:
        """Find the next available play_XX.json ID"""
        existing = list(self.log_dir.glob("play_*.json"))
        if not existing:
            return 0
        ids = []
        for f in existing:
            try:
                # Extract number from play_XX.json
                num = int(f.stem.split("_")[1])
                ids.append(num)
            except (IndexError, ValueError):
                pass
        return max(ids) + 1 if ids else 0

    def start_game(self, agents: List[Agent], num_players: int):
        """Initialize logging for a new interactive game"""
        self.move_history = []
        self.game_id = self._get_next_play_id()

        self.game_info = {
            'game_id': self.game_id,
            'timestamp': datetime.now().isoformat(),
            'num_players': num_players,
            'agents': [{'player_id': a.player_id, 'type': a.name} for a in agents],
            'mode': 'interactive'
        }

    def log_turn(self, round_num: int, turn_num: int, player_id: int,
                 move_result: dict, game_state: dict):
        """Log a single turn within a round"""
        turn_data = {
            'round': round_num,
            'turn': turn_num,
            'player': player_id,
            'move': move_result,
            'state': game_state
        }
        self.move_history.append(turn_data)

    def end_game(self, final_result: dict):
        """Finalize and save game log"""
        self.game_info['final_result'] = final_result
        self.game_info['move_history'] = self.move_history

        # Save detailed JSON log as play_XX.json
        game_file = self.log_dir / f"play_{self.game_id}.json"
        with open(game_file, 'w') as f:
            json.dump(self.game_info, f, indent=2)

        print(f"\nGame log saved to: {game_file}")
        return self.game_info


# ---------------------------------------------------------------------------
# Player Colors (ANSI escape codes)
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
    return (f"{label} "
            f"[Pull F:{card.pull_flat} Co:{card.pull_cobbles} "
            f"Cl:{card.pull_climb} D:{card.pull_descent} | "
            f"Atk F:{card.attack_flat} Co:{card.attack_cobbles} "
            f"Cl:{card.attack_climb} D:{card.attack_descent}]")


def format_rider(rider: Rider) -> str:
    """Format a rider for display."""
    return f"{rider.rider_type.value} @ pos {rider.position}"


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


CARD_SORT_ORDER = {
    CardType.ENERGY: 0,
    CardType.CLIMBER: 1,
    CardType.ROULEUR: 2,
    CardType.SPRINTER: 3,
}


def sort_cards(cards: List[Card]) -> List[Card]:
    """Sort cards: Energy first, then Climber, Rouleur, Sprinter."""
    return sorted(cards, key=lambda c: CARD_SORT_ORDER.get(c.card_type, 99))


def format_card_list(cards: List[Card], terrain: TerrainType = None,
                     highlight_playable: List[Card] = None) -> List[str]:
    """Format a list of cards as individually numbered labels, sorted alphabetically.

    If highlight_playable is given, cards NOT in that list are marked as (not playable).
    """
    labels = []
    for card in cards:
        label = format_card(card, terrain)
        if highlight_playable is not None and card not in highlight_playable:
            label += "  [not playable]"
        labels.append(label)
    return labels


TERRAIN_SYMBOLS = {
    TerrainType.FLAT: (".", "Flat"),
    TerrainType.COBBLES: ("~", "Cobbles"),
    TerrainType.CLIMB: ("^", "Climb"),
    TerrainType.DESCENT: ("v", "Descent"),
    TerrainType.SPRINT: ("S", "Sprint"),
    TerrainType.FINISH: ("F", "Finish"),
}

# Player colour labels for the track (P0=0, P1=1, etc.)
RIDER_LABELS = "0123456789"


def print_track(state: GameState):
    """Print a visual representation of the race track with rider positions.

    The track is printed in rows of *row_width* fields.  Each field shows:
      - A terrain symbol (see legend) when empty
      - A rider label (player-id digit) when occupied
    Sprint / finish fields are highlighted with brackets.
    A small legend and tile separator markers keep things readable.
    """

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
        ruler_cells = []
        for pos in range(row_start, row_end):
            if pos % 5 == 0:
                ruler_cells.append(f"{pos:<4}")
            else:
                ruler_cells.append("")
        # Build ruler string manually to align with 3-char cells
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


def print_card_reference_table():
    """Print a reference table showing all card movement values for all terrains."""
    print("\n" + "="*70)
    print(Colors.bold("  CARD REFERENCE TABLE - Movement Values"))
    print("="*70)

    # Create sample cards of each type
    energy_card = Card(CardType.ENERGY)
    rouleur_card = Card(
        CardType.ROULEUR,
        pull_flat=2, pull_cobbles=1, pull_climb=1, pull_descent=3,
        attack_flat=2, attack_cobbles=1, attack_climb=1, attack_descent=3
    )
    sprinter_card = Card(
        CardType.SPRINTER,
        pull_flat=1, pull_cobbles=1, pull_climb=0, pull_descent=3,
        attack_flat=3, attack_cobbles=2, attack_climb=1, attack_descent=3
    )
    climber_card = Card(
        CardType.CLIMBER,
        pull_flat=0, pull_cobbles=0, pull_climb=2, pull_descent=3,
        attack_flat=1, attack_cobbles=0, attack_climb=3, attack_descent=3
    )

    cards = [
        ("Energy", energy_card),
        ("Rouleur", rouleur_card),
        ("Sprinter", sprinter_card),
        ("Climber", climber_card)
    ]

    terrains = [
        ("Flat", TerrainType.FLAT),
        ("Cobbles", TerrainType.COBBLES),
        ("Climb", TerrainType.CLIMB),
        ("Descent", TerrainType.DESCENT)
    ]

    # Print header
    print(f"\n  {'Card Type':<12} | {'Terrain':<8} | Pull | Attack")
    print("  " + "-"*66)

    for card_name, card in cards:
        first_terrain = True
        for terrain_name, terrain_type in terrains:
            pull_val = card.get_movement(terrain_type, PlayMode.PULL)
            attack_val = card.get_movement(terrain_type, PlayMode.ATTACK)

            if first_terrain:
                print(f"  {card_name:<12} | {terrain_name:<8} |  {pull_val}   |   {attack_val}")
                first_terrain = False
            else:
                print(f"  {'':<12} | {terrain_name:<8} |  {pull_val}   |   {attack_val}")
        print("  " + "-"*66)

    print("\n" + Colors.bold("  TERRAIN LIMITS (Max fields per round):"))
    print("  " + "-"*66)
    print(f"  Sprinter on Climb:   3 fields max")
    print(f"  Rouleur on Climb:    4 fields max")
    print(f"  Climber on Cobbles:  3 fields max")
    print("="*70)
    print()


def print_board(state: GameState):
    """Print a compact view of all rider positions plus track visualization."""
    print_track(state)

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


def print_move_result(result: dict, player: Player):
    """Print what happened after a move."""
    action = result.get("action", "?")
    rider = result.get("rider", "?")
    old_pos = result.get("old_position", "?")
    new_pos = result.get("new_position", "?")
    movement = result.get("movement", 0)
    pts = result.get("points_earned", 0)

    parts = [f"{action} by {rider}: {old_pos} -> {new_pos} (+{movement})"]
    if pts:
        parts.append(f"  +{pts} sprint points!")
    drafters = result.get("drafting_riders")
    if drafters:
        for d in drafters:
            parts.append(f"  Drafter {d['rider']}: {d['old_position']} -> {d['new_position']}")
    cards_drawn_count = result.get("cards_drawn", 0)
    if isinstance(cards_drawn_count, list):
        # TeamCar returns list of card type strings
        parts.append(f"  Cards drawn: {', '.join(cards_drawn_count)}")
        discarded = result.get("card_discarded")
        if discarded:
            parts.append(f"  Card discarded: {discarded}")
    elif cards_drawn_count and cards_drawn_count > 0:
        parts.append(f"  Cards drawn from checkpoints: {cards_drawn_count}")

    for line in parts:
        print(f"    {line}")


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def prompt_choice(prompt: str, options: list, allow_cancel: bool = False) -> int:
    """Ask user to pick one option by number. Returns index.

    Special commands:
    - 'r': Show card reference table
    - 'c': Cancel (if allow_cancel=True)
    """
    while True:
        print(prompt)
        for i, option in enumerate(options):
            print(f"  [{i}] {option}")
        if allow_cancel:
            print(f"  [c] Cancel / go back")
        print(f"  [r] Show card reference table")
        raw = input("> ").strip().lower()
        if allow_cancel and raw == "c":
            return -1
        if raw == "r":
            print_card_reference_table()
            continue  # Show prompt again
        try:
            idx = int(raw)
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print("Invalid choice, try again.\n")


def prompt_multi_choice(prompt: str, options: list, min_sel: int = 1,
                        max_sel: int = None, allow_cancel: bool = False) -> Optional[List[int]]:
    """Ask user to pick multiple options (comma-separated). Returns list of indices, or None if cancelled.

    Special commands:
    - 'r': Show card reference table
    - 'b': Go back (if allow_cancel=True)
    """
    if max_sel is None:
        max_sel = len(options)
    while True:
        print(prompt)
        for i, option in enumerate(options):
            print(f"  [{i}] {option}")
        hint = f"  (select {min_sel}-{max_sel}, comma-separated)"
        if allow_cancel:
            hint += "  |  [b] go back"
        hint += "  |  [r] reference"
        print(hint)
        raw = input("> ").strip().lower()
        if allow_cancel and raw == "b":
            return None
        if raw == "r":
            print_card_reference_table()
            continue  # Show prompt again
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
    """Interactive human player."""

    BACK = "BACK"  # sentinel for go-back

    def __init__(self, player_id: int):
        super().__init__(player_id, "Human")

    def choose_move(self, engine: GameEngine, player: Player,
                    eligible_riders: List[Rider] = None) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            print("  No valid moves available - skipping turn.")
            return None

        riders = eligible_riders if eligible_riders is not None else player.riders
        terrain = self._current_terrain(engine, riders[0])

        player_label = Colors.player_bold(self.player_id, f"Player {self.player_id}")
        print(f"\n{'='*50}")
        print(f"  YOUR TURN  ({player_label})")
        print(f"{'='*50}")
        print(f"Hand ({len(player.hand)} cards):")
        print(format_hand(player.hand, terrain))
        print()

        # Step 1 -> Step 2 -> Step 3  (with go-back)
        while True:
            # --- Step 1: pick rider ------------------------------------
            rider_set = sorted(set(m.rider for m in valid_moves),
                               key=lambda r: r.rider_id)
            if len(rider_set) == 1:
                chosen_rider = rider_set[0]
                print(f"  Rider: {format_rider(chosen_rider)}")
            else:
                rider_labels = [format_rider(r) for r in rider_set]
                rider_idx = prompt_choice("Choose rider:", rider_labels)
                chosen_rider = rider_set[rider_idx]

            # --- Step 2: pick action (can go back to rider) ------------
            result = self._step_pick_action(engine, player, valid_moves,
                                            chosen_rider, terrain,
                                            can_go_back=len(rider_set) > 1)
            if result is self.BACK:
                continue  # restart from rider selection
            return result

    # ------------------------------------------------------------------
    # Step 2: pick action type
    # ------------------------------------------------------------------

    def _step_pick_action(self, engine, player, valid_moves, rider, terrain,
                          can_go_back: bool):
        """Pick an action for the chosen rider. Returns Move, None, or BACK."""
        # Moves where this rider is the primary mover
        rider_moves = [m for m in valid_moves if m.rider == rider]

        # For team actions (TeamDraft, TeamPull), the chosen rider might be a
        # drafter rather than the primary rider.  Include those moves too.
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

            # --- Step 3: action-specific (can go back to action) -------
            result = self._step_pick_details(engine, player, chosen_action,
                                             filtered, rider, terrain)
            if result is self.BACK:
                continue  # restart from action selection
            return result

    # ------------------------------------------------------------------
    # Step 3: action-specific details
    # ------------------------------------------------------------------

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

    # ---- action handlers ------------------------------------------------

    def _handle_card_action(self, engine: GameEngine, player: Player,
                            action: ActionType, rider: Rider,
                            terrain: TerrainType):
        """Handle Pull (1-3 cards) or Attack (exactly 3 cards).
        Shows all hand cards sorted alphabetically; unplayable cards are marked."""
        hand_sorted = sort_cards(player.hand)
        playable = [c for c in hand_sorted if c.can_play_on_rider(rider.rider_type)]
        card_labels = format_card_list(hand_sorted, terrain, highlight_playable=playable)

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

            chosen_cards = [hand_sorted[i] for i in indices]
            # Validate all selected cards are playable
            if any(c not in playable for c in chosen_cards):
                print("  Some selected cards are not playable on this rider. Try again.\n")
                continue

            mode = PlayMode.PULL if action == ActionType.PULL else PlayMode.ATTACK
            total = sum(c.get_movement(terrain, mode) if not c.is_energy_card() else 1
                        for c in chosen_cards)
            print(f"  -> Total movement: {total}")
            return Move(action, rider, chosen_cards)

    def _handle_team_car(self, engine: GameEngine, player: Player,
                         rider: Rider, terrain: TerrainType):
        """TeamCar: peek at deck, draw 2, let human pick discard."""
        peek_cards = []
        for i in range(min(2, len(engine.state.deck))):
            peek_cards.append(engine.state.deck[-(i + 1)])

        print(f"\n  Cards that will be drawn: "
              f"{', '.join(format_card(c, terrain) for c in peek_cards)}")

        full_hand = sort_cards(list(player.hand) + peek_cards)
        card_labels = format_card_list(full_hand, terrain)
        idx = prompt_choice("Pick a card to discard from your updated hand:",
                            card_labels, allow_cancel=True)
        if idx == -1:
            return self.BACK
        discard_card = full_hand[idx]
        return Move(ActionType.TEAM_CAR, rider, [discard_card])

    def _handle_team_draft(self, filtered: List[Move], rider: Rider):
        """TeamDraft: pick which riders draft together."""
        combos = []
        for m in filtered:
            all_riders = [m.rider] + m.drafting_riders
            combo_label = ", ".join(format_rider(r) for r in all_riders)
            combos.append((combo_label, m))
        labels = [c[0] for c in combos]
        idx = prompt_choice("Choose which riders draft together:", labels,
                            allow_cancel=True)
        if idx == -1:
            return self.BACK
        return combos[idx][1]

    def _handle_team_pull(self, engine: GameEngine, player: Player,
                          filtered: List[Move], rider: Rider,
                          terrain: TerrainType):
        """TeamPull: pick drafters, then pick cards for the pull."""
        # Unique drafter sets
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
                print(f"  Drafters: {', '.join(format_rider(r) for r in chosen_drafters)}")
            else:
                labels = [", ".join(format_rider(r) for r in ds) for ds in drafter_sets]
                idx = prompt_choice("Choose drafting riders:", labels,
                                    allow_cancel=True)
                if idx == -1:
                    return self.BACK
                chosen_drafters = drafter_sets[idx]

            # Pick cards (sorted hand, all shown)
            hand_sorted = sort_cards(player.hand)
            playable = [c for c in hand_sorted if c.can_play_on_rider(rider.rider_type)]
            card_labels = format_card_list(hand_sorted, terrain, highlight_playable=playable)
            min_cards, max_cards = 1, min(3, len(playable))

            indices = prompt_multi_choice(
                f"Select {min_cards}-{max_cards} cards for the pull:",
                card_labels, min_sel=min_cards, max_sel=max_cards,
                allow_cancel=True)
            if indices is None:
                if len(drafter_sets) == 1:
                    return self.BACK  # can't re-pick drafters, go back to action
                continue  # re-pick drafters

            chosen_cards = [hand_sorted[i] for i in indices]
            if any(c not in playable for c in chosen_cards):
                print("  Some selected cards are not playable on this rider. Try again.\n")
                continue

            total = sum(c.get_movement(terrain, PlayMode.PULL) if not c.is_energy_card() else 1
                        for c in chosen_cards)
            print(f"  -> Total movement for all riders: {total}")
            return Move(ActionType.TEAM_PULL, rider, chosen_cards, list(chosen_drafters))

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _current_terrain(engine: GameEngine, rider: Rider) -> TerrainType:
        tile = engine.state.get_tile_at_position(rider.position)
        return tile.terrain if tile else TerrainType.FLAT


# ---------------------------------------------------------------------------
# Game setup
# ---------------------------------------------------------------------------

def setup_game():
    """Interactive game setup: pick player count and assign human/bot slots."""
    print("=" * 60)
    print("  CHASSE PATATE - Interactive Play")
    print("=" * 60)
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
    agents: List[Agent] = []

    for slot in range(num_players):
        labels = [f"{o}" for o in slot_options]
        player_label = Colors.player_bold(slot, f"Player {slot}")
        idx = prompt_choice(f"\n{player_label}:", labels)
        choice = slot_options[idx]
        if choice == "human":
            agents.append(HumanAgent(slot))
        else:
            agents.append(create_agent(choice, slot))
        colored_name = Colors.player(slot, agents[-1].name)
        print(f"  -> {player_label} = {colored_name}")

    return num_players, agents


# ---------------------------------------------------------------------------
# Main game loop (mirrors simulator.py but with interactive output)
# ---------------------------------------------------------------------------

def play_game():
    num_players, agents = setup_game()

    state = GameState(num_players=num_players)
    engine = GameEngine(state)

    # Initialize logger
    logger = PlayLogger()
    logger.start_game(agents, num_players)

    # Assign agent names to players
    for i, agent in enumerate(agents):
        state.players[i].name = agent.name

    # Check if there are any human players (for pause-after-bot-turn feature)
    has_human_players = any(isinstance(a, HumanAgent) for a in agents)

    print(f"\n{'='*60}")
    print(f"  GAME START  ({num_players} players)")
    print(f"{'='*60}")
    print_board(state)

    turn_count = 0
    max_rounds = 150

    while not state.game_over and state.current_round < max_rounds:
        state.start_new_round()
        patron = state.players[state.el_patron]
        patron_label = Colors.player_bold(state.el_patron, f"{patron.name} (Player {state.el_patron})")
        print(f"\n{'~'*60}")
        print(f"  ROUND {state.current_round}  |  El Patron: {patron_label}")
        print(f"{'~'*60}")

        while True:
            turn_info = state.determine_next_turn()
            if turn_info is None:
                break  # round over

            current_player, eligible_riders = turn_info
            agent = agents[current_player.player_id]
            acted_position = eligible_riders[0].position

            is_human = isinstance(agent, HumanAgent)

            if is_human:
                print_board(state)

            move = agent.choose_move(engine, current_player, eligible_riders)

            if move is None:
                state.mark_riders_moved(eligible_riders, acted_position)
                turn_count += 1
                if state.check_game_over():
                    break
                continue

            move_result = engine.execute_move(move)

            moved_riders = [move.rider]
            if move.drafting_riders:
                moved_riders.extend(move.drafting_riders)
            state.mark_riders_moved(moved_riders, acted_position)

            # Log the turn
            game_summary = state.get_game_summary()
            logger.log_turn(state.current_round, turn_count,
                           current_player.player_id,
                           move_result, game_summary)

            # Print result
            rider_names = ", ".join(
                Colors.player(r.player_id, f"P{r.player_id}R{r.rider_id}")
                for r in moved_riders
            )
            player_label = Colors.player_bold(current_player.player_id,
                                              f"{agent.name} (P{current_player.player_id})")
            print(f"  Turn {turn_count}: {player_label} "
                  f"- {move.action_type.value} [{rider_names}]")
            print_move_result(move_result, current_player)

            # If this was a bot turn and there are human players, pause for review
            if not is_human and has_human_players:
                input("  [Press Enter to continue...]")

            turn_count += 1
            if state.check_game_over():
                break

    # --- Game over -------------------------------------------------------
    final = engine.process_end_of_race()

    # Add game over details to final result
    reason = state.get_game_over_reason()
    final['game_over_reason'] = reason
    final['total_rounds'] = state.current_round
    final['total_turns'] = turn_count

    # Count riders at finish
    finish_pos = state.track_length - 1
    riders_at_finish = sum(1 for p in state.players for r in p.riders if r.position >= finish_pos)
    final['riders_at_finish'] = riders_at_finish

    # Save game log
    logger.end_game(final)

    print(f"\n{'='*60}")
    print(f"  GAME OVER  after {state.current_round} rounds ({turn_count} turns)")
    print(f"{'='*60}")
    print()
    print("Final scores:")
    for i, player in enumerate(state.players):
        label = f"Player {i}"
        score = final["final_scores"].get(label, 0)
        player_label = Colors.player_bold(i, f"{label} ({player.name})")
        print(f"  {player_label}: {score} points")

    # Find winner player_id from winner string
    winner_str = final['winner']
    winner_id = None
    for i, player in enumerate(state.players):
        if f"Player {i}" in winner_str or player.name in winner_str:
            winner_id = i
            break
    if winner_id is not None:
        winner_label = Colors.player_bold(winner_id, final['winner'])
    else:
        winner_label = Colors.bold(final['winner'])
    print(f"\nWinner: {winner_label} with {final['winner_score']} points!")

    if reason:
        print(f"Reason: {reason}")
    print()


if __name__ == "__main__":
    play_game()
