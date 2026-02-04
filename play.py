"""
Chasse Patate - Interactive Play
Play against AI bots in the terminal.
"""

from typing import List, Optional
from itertools import combinations
from game_state import GameState, Card, CardType, ActionType, PlayMode, Rider, Player, TerrainType
from game_engine import GameEngine, Move
from agents import Agent, create_agent, get_available_agents


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
    return f"Rider {rider.rider_id} ({rider.rider_type.value}) @ pos {rider.position}"


def format_hand(hand: List[Card], terrain: TerrainType = None) -> str:
    """Format the player's hand grouped by card type."""
    by_type = {}
    for card in hand:
        key = card.card_type.value
        by_type.setdefault(key, []).append(card)
    lines = []
    for ctype in ["Energy", "Rouleur", "Sprinter", "Climber"]:
        cards = by_type.get(ctype, [])
        if cards:
            if terrain:
                label = format_card(cards[0], terrain)
            else:
                label = format_card(cards[0])
            lines.append(f"  {label}  x{len(cards)}")
    return "\n".join(lines) if lines else "  (empty)"


def print_board(state: GameState):
    """Print a compact view of all rider positions."""
    print("\n--- Board ---")
    for player in state.players:
        parts = []
        for rider in player.riders:
            tile = state.get_tile_at_position(rider.position)
            terrain = tile.terrain.value if tile else "?"
            parts.append(f"R{rider.rider_id}({rider.rider_type.value[0]})@{rider.position}[{terrain}]")
        print(f"  Player {player.player_id} ({player.name}): {', '.join(parts)}  | pts={player.points} hand={len(player.hand)}")
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


def prompt_multi_choice(prompt: str, options: list, min_sel: int = 1, max_sel: int = None) -> List[int]:
    """Ask user to pick multiple options (comma-separated). Returns list of indices."""
    if max_sel is None:
        max_sel = len(options)
    while True:
        print(prompt)
        for i, option in enumerate(options):
            print(f"  [{i}] {option}")
        print(f"  (select {min_sel}-{max_sel}, comma-separated)")
        raw = input("> ").strip()
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

        print(f"\n{'='*50}")
        print(f"  YOUR TURN  (Player {self.player_id})")
        print(f"{'='*50}")
        print(f"Hand ({len(player.hand)} cards):")
        print(format_hand(player.hand, terrain))
        print()

        # --- Step 1: pick action type -----------------------------------
        available_actions = sorted(set(m.action_type for m in valid_moves),
                                   key=lambda a: a.value)
        action_labels = [a.value for a in available_actions]
        action_idx = prompt_choice("Choose action:", action_labels)
        chosen_action = available_actions[action_idx]

        # Filter moves to chosen action
        filtered = [m for m in valid_moves if m.action_type == chosen_action]

        # --- Step 2: pick rider ----------------------------------------
        rider_set = sorted(set(m.rider for m in filtered),
                           key=lambda r: r.rider_id)
        if len(rider_set) == 1:
            chosen_rider = rider_set[0]
            print(f"  Rider: {format_rider(chosen_rider)}")
        else:
            rider_labels = [format_rider(r) for r in rider_set]
            rider_idx = prompt_choice("Choose rider:", rider_labels)
            chosen_rider = rider_set[rider_idx]

        filtered = [m for m in filtered if m.rider == chosen_rider]

        # --- Step 3: action-specific selection --------------------------
        if chosen_action in (ActionType.DRAFT,):
            # Draft: no further choice needed
            return filtered[0]

        if chosen_action == ActionType.TEAM_CAR:
            return self._handle_team_car(engine, player, chosen_rider, terrain)

        if chosen_action == ActionType.TEAM_DRAFT:
            return self._handle_team_draft(filtered, chosen_rider)

        if chosen_action == ActionType.TEAM_PULL:
            return self._handle_team_pull(engine, player, filtered, chosen_rider, terrain)

        # Pull or Attack: pick cards
        return self._handle_card_action(engine, player, chosen_action,
                                        chosen_rider, terrain)

    # ---- action handlers ------------------------------------------------

    def _handle_card_action(self, engine: GameEngine, player: Player,
                            action: ActionType, rider: Rider,
                            terrain: TerrainType) -> Move:
        """Handle Pull (1-3 cards) or Attack (exactly 3 cards)."""
        playable = [c for c in player.hand if c.can_play_on_rider(rider.rider_type)]
        card_labels = [format_card(c, terrain) for c in playable]

        if action == ActionType.ATTACK:
            min_cards = max_cards = 3
        else:
            min_cards, max_cards = 1, min(3, len(playable))

        indices = prompt_multi_choice(
            f"Select {min_cards}-{max_cards} cards to play:",
            card_labels, min_sel=min_cards, max_sel=max_cards)
        chosen_cards = [playable[i] for i in indices]

        mode = PlayMode.PULL if action == ActionType.PULL else PlayMode.ATTACK
        total = sum(c.get_movement(terrain, mode) if not c.is_energy_card() else 1
                    for c in chosen_cards)
        print(f"  -> Total movement: {total}")
        return Move(action, rider, chosen_cards)

    def _handle_team_car(self, engine: GameEngine, player: Player,
                         rider: Rider, terrain: TerrainType) -> Move:
        """TeamCar: peek at deck, draw 2, let human pick discard."""
        # Peek at the top 2 cards that will be drawn
        peek_cards = []
        for i in range(min(2, len(engine.state.deck))):
            peek_cards.append(engine.state.deck[-(i + 1)])

        print(f"\n  Cards that will be drawn: "
              f"{', '.join(format_card(c, terrain) for c in peek_cards)}")

        full_hand = list(player.hand) + peek_cards
        card_labels = [format_card(c, terrain) for c in full_hand]
        idx = prompt_choice("Pick a card to discard from your updated hand:",
                            card_labels)
        discard_card = full_hand[idx]
        return Move(ActionType.TEAM_CAR, rider, [discard_card])

    def _handle_team_draft(self, filtered: List[Move], rider: Rider) -> Move:
        """TeamDraft: pick which riders draft together."""
        # Collect unique drafter combos
        combos = []
        for m in filtered:
            all_riders = [m.rider] + m.drafting_riders
            combo_label = ", ".join(format_rider(r) for r in all_riders)
            combos.append((combo_label, m))
        labels = [c[0] for c in combos]
        idx = prompt_choice("Choose which riders draft together:", labels)
        return combos[idx][1]

    def _handle_team_pull(self, engine: GameEngine, player: Player,
                          filtered: List[Move], rider: Rider,
                          terrain: TerrainType) -> Move:
        """TeamPull: pick drafters, then pick cards for the pull."""
        # Unique drafter sets (excluding the puller)
        drafter_sets = []
        seen = set()
        for m in filtered:
            key = tuple(sorted(r.rider_id for r in m.drafting_riders))
            if key not in seen:
                seen.add(key)
                drafter_sets.append(m.drafting_riders)
        if len(drafter_sets) == 1:
            chosen_drafters = drafter_sets[0]
            print(f"  Drafters: {', '.join(format_rider(r) for r in chosen_drafters)}")
        else:
            labels = [", ".join(format_rider(r) for r in ds) for ds in drafter_sets]
            idx = prompt_choice("Choose drafting riders:", labels)
            chosen_drafters = drafter_sets[idx]

        # Now pick cards (same as Pull)
        playable = [c for c in player.hand if c.can_play_on_rider(rider.rider_type)]
        card_labels = [format_card(c, terrain) for c in playable]
        min_cards, max_cards = 1, min(3, len(playable))
        indices = prompt_multi_choice(
            f"Select {min_cards}-{max_cards} cards for the pull:",
            card_labels, min_sel=min_cards, max_sel=max_cards)
        chosen_cards = [playable[i] for i in indices]

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
        idx = prompt_choice(f"\nPlayer {slot}:", labels)
        choice = slot_options[idx]
        if choice == "human":
            agents.append(HumanAgent(slot))
        else:
            agents.append(create_agent(choice, slot))
        print(f"  -> Player {slot} = {agents[-1].name}")

    return num_players, agents


# ---------------------------------------------------------------------------
# Main game loop (mirrors simulator.py but with interactive output)
# ---------------------------------------------------------------------------

def play_game():
    num_players, agents = setup_game()

    state = GameState(num_players=num_players)
    engine = GameEngine(state)

    # Assign agent names to players
    for i, agent in enumerate(agents):
        state.players[i].name = str(agent)

    print(f"\n{'='*60}")
    print(f"  GAME START  ({num_players} players)")
    print(f"{'='*60}")
    print_board(state)

    turn_count = 0
    max_rounds = 150

    while not state.game_over and state.current_round < max_rounds:
        state.start_new_round()
        print(f"\n{'~'*60}")
        print(f"  ROUND {state.current_round}")
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

            # Print result
            rider_names = ", ".join(f"P{r.player_id}R{r.rider_id}" for r in moved_riders)
            print(f"  Turn {turn_count}: {agent.name} (P{current_player.player_id}) "
                  f"- {move.action_type.value} [{rider_names}]")
            print_move_result(move_result, current_player)

            turn_count += 1
            if state.check_game_over():
                break

    # --- Game over -------------------------------------------------------
    final = engine.process_end_of_race()
    print(f"\n{'='*60}")
    print(f"  GAME OVER  after {state.current_round} rounds ({turn_count} turns)")
    print(f"{'='*60}")
    print()
    print("Final scores:")
    for label, score in final["final_scores"].items():
        print(f"  {label}: {score} points")
    print(f"\nWinner: {final['winner']} with {final['winner_score']} points!")

    reason = state.get_game_over_reason()
    if reason:
        print(f"Reason: {reason}")
    print()


if __name__ == "__main__":
    play_game()
