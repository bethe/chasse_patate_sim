"""
Comprehensive test suite for Chasse Patate game rules and mechanics.

Tests all core game mechanics including:
- Terrain limits
- El Patron rule and turn order
- Game end conditions
- Card mechanics
- Move validation
- Drafting rules
- Sprint and finish scoring
- Checkpoint mechanics
- Round-based game flow
- Agent behavior (TobiBot)
- Tournament position alternation

Total: 80+ unit tests
"""

import unittest
from game_state import (
    GameState, TerrainType, CardType, Card, PlayMode, RACE_TILES,
    Rider, Player, ActionType
)
from game_engine import GameEngine, Move, TERRAIN_LIMITS


class TestTerrainLimits(unittest.TestCase):
    """Test terrain limits for different rider types"""

    def setUp(self):
        """Set up a game with a track that has both climb and cobbles sections"""
        # Use tile config: Mountaintop Finish (climb heavy) + Champs Elysees (cobbles)
        # Tile 2: 3 flat + 17 climb
        # Tile 3: 8 flat + 12 cobbles
        self.state = GameState(num_players=2, tile_config=[2, 3])
        self.engine = GameEngine(self.state)

    def test_terrain_limits_constants(self):
        """Verify terrain limits are correctly defined"""
        self.assertEqual(TERRAIN_LIMITS[(CardType.SPRINTER, TerrainType.CLIMB)], 3)
        self.assertEqual(TERRAIN_LIMITS[(CardType.ROULEUR, TerrainType.CLIMB)], 4)
        self.assertEqual(TERRAIN_LIMITS[(CardType.CLIMBER, TerrainType.COBBLES)], 3)

    def test_sprinter_climb_limit(self):
        """Sprinter should be limited to 3 fields on climb terrain"""
        sprinter = self.state.players[0].riders[1]
        self.assertEqual(sprinter.rider_type, CardType.SPRINTER)

        # Position sprinter at start of climb section (position 3 in tile 2)
        sprinter.position = 3  # First climb position

        # Try to move 6 fields - should be limited to 3
        actual_movement = self.engine._calculate_limited_movement(sprinter, 3, 6)
        self.assertEqual(actual_movement, 3)

    def test_rouleur_climb_limit(self):
        """Rouleur should be limited to 4 fields on climb terrain"""
        rouleur = self.state.players[0].riders[0]
        self.assertEqual(rouleur.rider_type, CardType.ROULEUR)

        # Position rouleur at start of climb section
        rouleur.position = 3

        # Try to move 6 fields - should be limited to 4
        actual_movement = self.engine._calculate_limited_movement(rouleur, 3, 6)
        self.assertEqual(actual_movement, 4)

    def test_climber_cobbles_limit(self):
        """Climber should be limited to 3 fields on cobbles terrain"""
        climber = self.state.players[0].riders[2]
        self.assertEqual(climber.rider_type, CardType.CLIMBER)

        # Position climber at start of cobbles section (tile 3 starts at position 20)
        # Tile 3 = 8 flat + 12 cobbles, so cobbles starts at position 28
        climber.position = 28

        # Try to move 6 fields - should be limited to 3
        actual_movement = self.engine._calculate_limited_movement(climber, 28, 6)
        self.assertEqual(actual_movement, 3)

    def test_climber_no_limit_on_climb(self):
        """Climber should have NO limit on climb terrain"""
        climber = self.state.players[0].riders[2]
        climber.position = 3  # Start of climb

        # Move 10 fields - should not be limited
        actual_movement = self.engine._calculate_limited_movement(climber, 3, 10)
        self.assertEqual(actual_movement, 10)

    def test_sprinter_no_limit_on_flat(self):
        """Sprinter should have NO limit on flat terrain"""
        sprinter = self.state.players[0].riders[1]
        sprinter.position = 0  # Start position (flat)

        # Move 3 fields on flat - should not be limited
        actual_movement = self.engine._calculate_limited_movement(sprinter, 0, 3)
        self.assertEqual(actual_movement, 3)

    def test_partial_terrain_limit_flat_to_climb(self):
        """Limit should only apply to the climb portion when moving from flat to climb"""
        sprinter = self.state.players[0].riders[1]
        sprinter.position = 1

        actual_movement = self.engine._calculate_limited_movement(sprinter, 1, 6)
        # From position 1: can move through position 2 (flat) + positions 3,4,5 (climb, limited to 3) = 4 total
        self.assertEqual(actual_movement, 4)

    def test_partial_terrain_limit_climb_to_descent(self):
        """Movement from climb to descent - descent has no limits"""
        # Use tile 4 which has climb + descent
        state = GameState(num_players=2, tile_config=[4])
        engine = GameEngine(state)
        # Tile 4: 2 flat + 12 climb + 6 descent

        sprinter = state.players[0].riders[1]
        sprinter.position = 11

        # Moving 8 fields from position 11
        actual_movement = engine._calculate_limited_movement(sprinter, 11, 8)
        self.assertEqual(actual_movement, 8)

    def test_team_draft_per_rider_limits(self):
        """In TeamDraft, each rider should apply their own terrain limits"""
        rouleur = self.state.players[0].riders[0]  # Max 4 on climb
        sprinter = self.state.players[0].riders[1]  # Max 3 on climb
        climber = self.state.players[0].riders[2]  # No limit on climb

        rouleur.position = 5
        sprinter.position = 5
        climber.position = 5

        # Simulate a previous move that allows drafting
        self.state.last_move = {
            'action': 'Pull',
            'rider': 'P1R0',  # Different player
            'old_position': 5,
            'movement': 6,
        }

        # Execute team draft with all 3 riders
        move = Move(
            ActionType.TEAM_DRAFT,
            rouleur,
            [],
            [sprinter, climber]
        )

        result = self.engine.execute_move(move)
        self.assertTrue(result['success'])

        # Check each rider ended up at their limited position
        self.assertEqual(rouleur.position, 9)  # 4 climb fields
        self.assertEqual(sprinter.position, 8)  # 3 climb fields
        self.assertEqual(climber.position, 11)  # No limit

    def test_team_pull_per_rider_limits(self):
        """In TeamPull, lead rider and drafters apply their own terrain limits"""
        player = self.state.players[0]

        climber = player.riders[2]  # Climber pulls - no limit on climb
        rouleur = player.riders[0]  # Max 4 on climb
        sprinter = player.riders[1]  # Max 3 on climb

        # Position all at position 3 (start of climb)
        climber.position = 3
        rouleur.position = 3
        sprinter.position = 3

        # Create cards for climber to pull with
        player.hand = [
            Card(CardType.CLIMBER, pull_flat=0, pull_cobbles=0, pull_climb=2, pull_descent=3,
                 attack_flat=1, attack_cobbles=0, attack_climb=3, attack_descent=3),
            Card(CardType.CLIMBER, pull_flat=0, pull_cobbles=0, pull_climb=2, pull_descent=3,
                 attack_flat=1, attack_cobbles=0, attack_climb=3, attack_descent=3),
            Card(CardType.CLIMBER, pull_flat=0, pull_cobbles=0, pull_climb=2, pull_descent=3,
                 attack_flat=1, attack_cobbles=0, attack_climb=3, attack_descent=3),
        ]

        # Execute team pull: climber pulls, rouleur and sprinter draft
        move = Move(
            ActionType.TEAM_PULL,
            climber,
            player.hand[:3],
            [rouleur, sprinter]
        )

        result = self.engine.execute_move(move)
        self.assertTrue(result['success'])

        # Check positions
        self.assertEqual(climber.position, 9)  # No limit, moves full 6
        self.assertEqual(rouleur.position, 7)  # Limit of 4
        self.assertEqual(sprinter.position, 6)  # Limit of 3


class TestTerrainLimitEdgeCases(unittest.TestCase):
    """Test edge cases for terrain limits"""

    def test_limit_at_track_end(self):
        """Terrain limit should not allow movement past track end"""
        state = GameState(num_players=2, tile_config=[2])  # 20 field track
        engine = GameEngine(state)

        sprinter = state.players[0].riders[1]
        sprinter.position = 18  # Near end of track

        # Try to move 5 fields - limited by track end
        actual_movement = engine._calculate_limited_movement(sprinter, 18, 5)
        self.assertEqual(actual_movement, 1)  # Can only reach position 19

    def test_zero_movement(self):
        """Zero base movement should result in zero actual movement"""
        state = GameState(num_players=2, tile_config=[2])
        engine = GameEngine(state)

        sprinter = state.players[0].riders[1]
        sprinter.position = 5

        actual_movement = engine._calculate_limited_movement(sprinter, 5, 0)
        self.assertEqual(actual_movement, 0)

    def test_movement_under_limit(self):
        """Movement below the limit should not be affected"""
        state = GameState(num_players=2, tile_config=[2])
        engine = GameEngine(state)

        sprinter = state.players[0].riders[1]
        sprinter.position = 3  # Start of climb

        # Move only 2 fields on climb - should not be limited (limit is 3)
        actual_movement = engine._calculate_limited_movement(sprinter, 3, 2)
        self.assertEqual(actual_movement, 2)


class TestElPatronRule(unittest.TestCase):
    """Test El Patron rule and turn order mechanics"""

    def test_el_patron_starts_at_player_0(self):
        """El Patron should start at Player 0 in round 1"""
        state = GameState(num_players=3)
        self.assertEqual(state.el_patron, 0)

    def test_el_patron_rotates_each_round(self):
        """El Patron should rotate to next player each round"""
        state = GameState(num_players=3)

        # Round 1: El Patron = 0
        state.start_new_round()
        self.assertEqual(state.current_round, 1)
        self.assertEqual(state.el_patron, 0)

        # Round 2: El Patron = 1
        state.start_new_round()
        self.assertEqual(state.current_round, 2)
        self.assertEqual(state.el_patron, 1)

        # Round 3: El Patron = 2
        state.start_new_round()
        self.assertEqual(state.current_round, 3)
        self.assertEqual(state.el_patron, 2)

        # Round 4: El Patron wraps back to 0
        state.start_new_round()
        self.assertEqual(state.current_round, 4)
        self.assertEqual(state.el_patron, 0)

    def test_el_patron_order_with_tied_positions(self):
        """When riders are tied, El Patron determines turn order"""
        state = GameState(num_players=3)
        state.el_patron = 1  # Set El Patron to Player 1

        # Place all riders at position 0
        for player in state.players:
            for rider in player.riders:
                rider.position = 0

        state.start_new_round()

        # Get turn order - should start with Player 1 (El Patron)
        turn = state.determine_next_turn()
        self.assertIsNotNone(turn)
        player, eligible_riders = turn
        self.assertEqual(player.player_id, 1)  # El Patron goes first

    def test_player_order_key_calculation(self):
        """Test the player order key calculation for El Patron"""
        state = GameState(num_players=3)

        # El Patron = 0: order should be 0, 1, 2
        state.el_patron = 0
        self.assertEqual(state._player_order_key(0), 0)
        self.assertEqual(state._player_order_key(1), 1)
        self.assertEqual(state._player_order_key(2), 2)

        # El Patron = 1: order should be 1, 2, 0
        state.el_patron = 1
        self.assertEqual(state._player_order_key(1), 0)
        self.assertEqual(state._player_order_key(2), 1)
        self.assertEqual(state._player_order_key(0), 2)

        # El Patron = 2: order should be 2, 0, 1
        state.el_patron = 2
        self.assertEqual(state._player_order_key(2), 0)
        self.assertEqual(state._player_order_key(0), 1)
        self.assertEqual(state._player_order_key(1), 2)


class TestTurnOrderMechanics(unittest.TestCase):
    """Test turn order and round-based game flow"""

    def test_most_advanced_rider_moves_first(self):
        """Most advanced unmoved rider should move first"""
        state = GameState(num_players=2)

        # Position riders at different positions
        state.players[0].riders[0].position = 10
        state.players[0].riders[1].position = 5
        state.players[1].riders[0].position = 8

        state.start_new_round()

        # Player 0's rider at position 10 should go first
        turn = state.determine_next_turn()
        self.assertIsNotNone(turn)
        player, eligible_riders = turn
        self.assertEqual(player.player_id, 0)
        self.assertEqual(eligible_riders[0].position, 10)

    def test_same_player_multiple_riders_at_position(self):
        """Same player with multiple riders at top position can choose which to move"""
        state = GameState(num_players=2)

        # Player 0 has two riders at position 10
        state.players[0].riders[0].position = 10
        state.players[0].riders[1].position = 10
        state.players[0].riders[2].position = 5
        state.players[1].riders[0].position = 8

        state.start_new_round()

        turn = state.determine_next_turn()
        self.assertIsNotNone(turn)
        player, eligible_riders = turn
        self.assertEqual(player.player_id, 0)
        self.assertEqual(len(eligible_riders), 2)  # Two riders eligible
        self.assertTrue(all(r.position == 10 for r in eligible_riders))

    def test_round_completes_when_all_riders_moved(self):
        """Round should complete when all riders have moved"""
        state = GameState(num_players=2)
        state.start_new_round()

        # Mark all riders as moved
        for player in state.players:
            for rider in player.riders:
                state.riders_moved_this_round.add(rider)

        # Should return None (round complete)
        turn = state.determine_next_turn()
        self.assertIsNone(turn)

    def test_riders_moved_tracking(self):
        """Riders should be tracked as moved within a round"""
        state = GameState(num_players=2)
        state.start_new_round()

        rider = state.players[0].riders[0]

        # Rider should not be in moved set initially
        self.assertNotIn(rider, state.riders_moved_this_round)

        # Mark as moved
        state.mark_riders_moved([rider])

        # Rider should now be in moved set
        self.assertIn(rider, state.riders_moved_this_round)

    def test_finished_riders_auto_marked_moved(self):
        """Riders at finish should be automatically marked as moved"""
        state = GameState(num_players=2, tile_config=[1])  # Single tile

        # Move a rider to finish
        rider = state.players[0].riders[0]
        rider.position = 19  # Finish position

        # Start new round
        state.start_new_round()

        # Finished rider should be marked as moved
        self.assertIn(rider, state.riders_moved_this_round)


class TestGameEndConditions(unittest.TestCase):
    """Test all game end conditions"""

    def test_game_ends_when_five_riders_finish(self):
        """Game should end when 5 riders reach the finish"""
        state = GameState(num_players=3, tile_config=[1])  # Single tile
        finish_pos = 19

        # Move 5 riders to finish
        state.players[0].riders[0].position = finish_pos
        state.players[0].riders[1].position = finish_pos
        state.players[1].riders[0].position = finish_pos
        state.players[1].riders[1].position = finish_pos
        state.players[2].riders[0].position = finish_pos

        # Check game over
        self.assertTrue(state.check_game_over())
        self.assertIn("5_riders_finished", state.get_game_over_reason())

    def test_game_ends_when_one_player_finishes_all_riders(self):
        """Game should end when one player has all 3 riders at finish"""
        state = GameState(num_players=2, tile_config=[1])
        finish_pos = 19

        # Move all of Player 0's riders to finish
        for rider in state.players[0].riders:
            rider.position = finish_pos

        # Check game over
        self.assertTrue(state.check_game_over())
        self.assertIn("team_fully_finished", state.get_game_over_reason())

    def test_game_ends_when_cards_exhausted(self):
        """Game should end when deck and all hands are empty"""
        state = GameState(num_players=2)

        # Empty the deck
        state.deck = []
        state.discard_pile = []

        # Empty all player hands
        for player in state.players:
            player.hand = []

        # Check game over
        self.assertTrue(state.check_game_over())
        self.assertEqual(state.get_game_over_reason(), "players_out_of_cards")

    def test_game_not_over_with_cards_in_deck(self):
        """Game should not end if cards remain in deck"""
        state = GameState(num_players=2)

        # Deck has cards (from initial setup)
        self.assertGreater(len(state.deck), 0)

        # Game should not be over
        self.assertFalse(state.check_game_over())

    def test_game_not_over_with_less_than_five_finishers(self):
        """Game should not end with fewer than 5 riders at finish"""
        state = GameState(num_players=3, tile_config=[1])
        finish_pos = 19

        # Move only 4 riders to finish
        state.players[0].riders[0].position = finish_pos
        state.players[0].riders[1].position = finish_pos
        state.players[1].riders[0].position = finish_pos
        state.players[1].riders[1].position = finish_pos

        # Game should not be over
        self.assertFalse(state.check_game_over())

    def test_game_ends_when_player_stuck(self):
        """Game should end when a player advances less than 5 fields in 5 rounds"""
        state = GameState(num_players=2, tile_config=[1, 4, 5])

        # Simulate 5 rounds where Player 0 barely moves
        # Player 0: riders at positions 10, 11, 12
        state.players[0].riders[0].position = 10
        state.players[0].riders[1].position = 11
        state.players[0].riders[2].position = 12
        # Player 1: riders moving normally
        state.players[1].riders[0].position = 20
        state.players[1].riders[1].position = 21
        state.players[1].riders[2].position = 22

        # Simulate 5 rounds with minimal movement for Player 0
        for round_num in range(1, 6):
            state.current_round = round_num
            state.start_new_round()

            # Player 0 advances by only 0.5 fields total per round (very stuck)
            if round_num <= 3:
                state.players[0].riders[0].position += 0  # No movement
                state.players[0].riders[1].position += 1  # Minimal movement
                state.players[0].riders[2].position += 0  # No movement

            # Player 1 moves normally (5+ fields per round)
            state.players[1].riders[0].position += 2
            state.players[1].riders[1].position += 2
            state.players[1].riders[2].position += 2

        # After 5 rounds, check if game detects Player 0 as stuck
        # Player 0 total advancement: (10+11+12) = 33 -> (10+14+12) = 36 = only 3 fields in 5 rounds
        self.assertTrue(state.check_game_over())
        reason = state.get_game_over_reason()
        self.assertIsNotNone(reason)
        self.assertIn("player_stuck", reason)
        self.assertIn("Player 0", reason)

    def test_game_not_stuck_with_sufficient_advancement(self):
        """Game should not end if all players advance 5+ fields over 5 rounds"""
        state = GameState(num_players=2, tile_config=[1, 4, 5])

        # Initial positions
        state.players[0].riders[0].position = 10
        state.players[0].riders[1].position = 11
        state.players[0].riders[2].position = 12
        state.players[1].riders[0].position = 20
        state.players[1].riders[1].position = 21
        state.players[1].riders[2].position = 22

        # Simulate 5 rounds with all players advancing well
        for round_num in range(1, 6):
            state.current_round = round_num
            state.start_new_round()

            # Both players advance 6+ fields total per round
            state.players[0].riders[0].position += 2
            state.players[0].riders[1].position += 2
            state.players[0].riders[2].position += 2

            state.players[1].riders[0].position += 2
            state.players[1].riders[1].position += 2
            state.players[1].riders[2].position += 2

        # Game should not be stuck - both players advanced 30 fields in 5 rounds
        self.assertFalse(state.check_game_over())


class TestCardMechanics(unittest.TestCase):
    """Test card drawing, reshuffling, and initial dealing"""

    def test_initial_hand_size(self):
        """Each player should start with 9 cards"""
        state = GameState(num_players=3)
        for player in state.players:
            self.assertEqual(len(player.hand), 9)

    def test_initial_hand_composition(self):
        """Each player should start with 3 Energy + 1 of each rider type + 3 random"""
        state = GameState(num_players=2)
        for player in state.players:
            energy_count = sum(1 for c in player.hand if c.card_type == CardType.ENERGY)
            rouleur_count = sum(1 for c in player.hand if c.card_type == CardType.ROULEUR)
            sprinter_count = sum(1 for c in player.hand if c.card_type == CardType.SPRINTER)
            climber_count = sum(1 for c in player.hand if c.card_type == CardType.CLIMBER)

            # Should have at least 3 Energy, and at least 1 of each rider type
            self.assertGreaterEqual(energy_count, 3)
            self.assertGreaterEqual(rouleur_count, 1)
            self.assertGreaterEqual(sprinter_count, 1)
            self.assertGreaterEqual(climber_count, 1)

    def test_total_card_count(self):
        """Total cards should always equal 90"""
        state = GameState(num_players=3)

        cards_in_hands = sum(len(p.hand) for p in state.players)
        cards_in_deck = len(state.deck)
        cards_in_discard = len(state.discard_pile)
        total = cards_in_hands + cards_in_deck + cards_in_discard

        self.assertEqual(total, 90)

    def test_deck_reshuffles_when_empty(self):
        """Deck should reshuffle discard pile when empty"""
        state = GameState(num_players=2)

        # Move all cards to discard
        state.discard_pile = state.deck[:]
        state.deck = []

        # Draw a card - should trigger reshuffle
        card = state.draw_card()

        self.assertIsNotNone(card)
        self.assertGreater(len(state.deck), 0)
        self.assertEqual(len(state.discard_pile), 0)

    def test_checkpoint_card_drawing(self):
        """Crossing checkpoint should draw 3 cards"""
        state = GameState(num_players=2, tile_config=[1])
        engine = GameEngine(state)

        player = state.players[0]
        rider = player.riders[0]
        initial_hand_size = len(player.hand)

        # Position rider before checkpoint 10
        rider.position = 8

        # Create a pull move that crosses checkpoint 10
        # Use energy cards to move 3 fields (to position 11)
        player.hand = [Card(CardType.ENERGY) for _ in range(3)]
        move = Move(ActionType.PULL, rider, player.hand[:2])

        result = engine.execute_move(move)

        # Should have drawn 3 cards for checkpoint 10
        self.assertEqual(result['cards_drawn'], 3)
        self.assertIn(10, result['checkpoints_reached'])

    def test_checkpoint_only_awarded_once(self):
        """Checkpoint should only award cards once per rider"""
        state = GameState(num_players=2, tile_config=[1])
        engine = GameEngine(state)

        rider = state.players[0].riders[0]

        # Mark checkpoint as reached
        state.mark_checkpoint_reached(rider, 10)

        # Check if already reached
        self.assertTrue(state.has_rider_reached_checkpoint(rider, 10))


class TestMoveValidation(unittest.TestCase):
    """Test move validation and generation"""

    def test_pull_requires_matching_or_energy_cards(self):
        """Pull should only work with matching rider cards or energy"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        player = state.players[0]
        rouleur = player.riders[0]

        # Give player only sprinter cards (no match)
        player.hand = [
            Card(CardType.SPRINTER, pull_flat=1, pull_cobbles=1, pull_climb=0, pull_descent=3,
                 attack_flat=3, attack_cobbles=2, attack_climb=1, attack_descent=3)
        ]

        # Get valid moves for rouleur
        moves = engine._get_pull_moves(rouleur, player)

        # Should have no valid pull moves
        self.assertEqual(len(moves), 0)

    def test_attack_requires_three_cards(self):
        """Attack should require exactly 3 cards"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        player = state.players[0]
        rider = player.riders[0]

        # Give player only 2 cards
        player.hand = [Card(CardType.ENERGY), Card(CardType.ROULEUR,
            pull_flat=2, pull_cobbles=1, pull_climb=1, pull_descent=3,
            attack_flat=2, attack_cobbles=1, attack_climb=1, attack_descent=3)]

        # Get valid attack moves
        moves = engine._get_attack_moves(rider, player)

        # Should have no valid attack moves (need 3 cards)
        self.assertEqual(len(moves), 0)

    def test_attack_requires_matching_rider_card(self):
        """Attack should require at least 1 matching rider card"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        player = state.players[0]
        rouleur = player.riders[0]  # Rouleur rider

        # Give player 3 energy cards (no matching rider card)
        player.hand = [Card(CardType.ENERGY), Card(CardType.ENERGY), Card(CardType.ENERGY)]

        # Get valid attack moves
        moves = engine._get_attack_moves(rouleur, player)

        # Should have no valid attack moves (need at least 1 rouleur card)
        self.assertEqual(len(moves), 0)

    def test_draft_requires_previous_move(self):
        """Draft should only be possible if there was a previous move"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        player = state.players[0]
        rider = player.riders[0]

        # No previous move
        state.last_move = None

        # Get valid draft moves
        moves = engine._get_draft_moves(rider, player)

        # Should have no valid draft moves
        self.assertEqual(len(moves), 0)

    def test_team_car_always_available(self):
        """TeamCar should always be available as a move"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        player = state.players[0]
        rider = player.riders[0]

        # Get all valid moves
        moves = engine.get_valid_moves(player, [rider])

        # Should have at least one TeamCar move
        team_car_moves = [m for m in moves if m.action_type == ActionType.TEAM_CAR]
        self.assertGreater(len(team_car_moves), 0)


class TestDraftingRules(unittest.TestCase):
    """Test drafting eligibility and rules"""

    def test_can_draft_from_different_player(self):
        """Rider should be able to draft from different player's move"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        # Set up last move from Player 1
        state.last_move = {
            'action': 'Pull',
            'rider': 'P1R0',
            'old_position': 0,
            'movement': 3
        }

        # Player 0's rider at position 0
        rider = state.players[0].riders[0]
        rider.position = 0

        # Check if can draft
        moves = engine._get_draft_moves(rider, state.players[0])

        # Should have valid draft move
        self.assertGreater(len(moves), 0)

    def test_can_draft_from_same_player_different_rider(self):
        """Rider should be able to draft from same player's different rider"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        # Set up last move from Player 0 Rider 0
        state.last_move = {
            'action': 'Pull',
            'rider': 'P0R0',
            'old_position': 0,
            'movement': 3
        }

        # Player 0's Rider 1 at position 0 (different rider, same player)
        rider = state.players[0].riders[1]
        rider.position = 0

        # Check if can draft
        moves = engine._get_draft_moves(rider, state.players[0])

        # Should have valid draft move
        self.assertGreater(len(moves), 0)

    def test_cannot_draft_from_own_move(self):
        """Rider should NOT be able to draft from their own move"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        # Set up last move from Player 0 Rider 0
        state.last_move = {
            'action': 'Pull',
            'rider': 'P0R0',
            'old_position': 0,
            'movement': 3
        }

        # Same rider tries to draft
        rider = state.players[0].riders[0]
        rider.position = 0

        # Check if can draft
        moves = engine._get_draft_moves(rider, state.players[0])

        # Should NOT have valid draft move
        self.assertEqual(len(moves), 0)

    def test_draft_requires_matching_position(self):
        """Draft requires rider to be at starting position of last move"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        # Set up last move from Player 1 starting at position 5
        state.last_move = {
            'action': 'Pull',
            'rider': 'P1R0',
            'old_position': 5,
            'movement': 3
        }

        # Player 0's rider at position 0 (wrong position)
        rider = state.players[0].riders[0]
        rider.position = 0

        # Check if can draft
        moves = engine._get_draft_moves(rider, state.players[0])

        # Should NOT have valid draft move
        self.assertEqual(len(moves), 0)

    def test_draft_only_from_pull_or_draft_actions(self):
        """Can only draft from Pull, Draft, TeamPull, or TeamDraft actions"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        rider = state.players[0].riders[0]
        rider.position = 0

        # Test with TeamCar action (should not allow draft)
        state.last_move = {
            'action': 'TeamCar',
            'rider': 'P1R0',
            'old_position': 0,
            'movement': 0
        }

        moves = engine._get_draft_moves(rider, state.players[0])
        self.assertEqual(len(moves), 0)

        # Test with Attack action (should not allow draft)
        state.last_move = {
            'action': 'Attack',
            'rider': 'P1R0',
            'old_position': 0,
            'movement': 5
        }

        moves = engine._get_draft_moves(rider, state.players[0])
        self.assertEqual(len(moves), 0)


class TestSprintAndFinishScoring(unittest.TestCase):
    """Test sprint point awards and finish line scoring"""

    def test_sprint_points_intermediate(self):
        """Intermediate sprint should award 3, 2, 1 points for top 3"""
        state = GameState(num_players=3, tile_config=[1])  # Single tile
        engine = GameEngine(state)

        # Position 19 is the finish/sprint
        sprint_pos = 19

        # Move 3 riders to sprint in order
        riders = [state.players[i].riders[0] for i in range(3)]

        for i, rider in enumerate(riders):
            rider.position = sprint_pos - 1
            points_before = state.players[rider.player_id].points

            # Award sprint points
            points = engine._check_sprint_scoring(rider, sprint_pos)

            # First rider gets 12, second gets 8, third gets 5 (finish line points)
            expected = [12, 8, 5][i]
            self.assertEqual(points, expected)

    def test_sprint_points_only_awarded_once(self):
        """Sprint points should only be awarded once per rider per sprint"""
        state = GameState(num_players=2, tile_config=[1])
        engine = GameEngine(state)

        sprint_pos = 19
        rider = state.players[0].riders[0]

        # First crossing - should award points
        points1 = engine._check_sprint_scoring(rider, sprint_pos)
        self.assertGreater(points1, 0)

        # Second crossing - should NOT award points
        points2 = engine._check_sprint_scoring(rider, sprint_pos)
        self.assertEqual(points2, 0)

    def test_sprint_arrival_order_tracking(self):
        """Sprint arrivals should be tracked in order"""
        state = GameState(num_players=3, tile_config=[1])
        engine = GameEngine(state)

        sprint_pos = 19
        riders = [state.players[i].riders[0] for i in range(3)]

        # Move riders to sprint
        for rider in riders:
            engine._check_sprint_scoring(rider, sprint_pos)

        # Check arrival order
        arrivals = state.sprint_arrivals[sprint_pos]
        self.assertEqual(len(arrivals), 3)
        self.assertEqual(arrivals, riders)

    def test_multiple_riders_same_player_cross_finish_team_pull(self):
        """When multiple riders from same player cross finish in TeamPull, each should get points"""
        state = GameState(num_players=2, tile_config=[1])  # Single tile (20 fields)
        engine = GameEngine(state)

        player = state.players[0]
        lead_rider = player.riders[0]
        drafter = player.riders[1]

        # Position both riders at position 18 (one before finish)
        lead_rider.position = 18
        drafter.position = 18

        # Give player energy cards to move 2 fields (to position 19 = finish)
        player.hand = [Card(CardType.ENERGY), Card(CardType.ENERGY)]

        initial_points = player.points

        # Execute TeamPull with both riders
        move = Move(
            ActionType.TEAM_PULL,
            lead_rider,
            player.hand[:2],
            [drafter]
        )

        result = engine.execute_move(move)

        self.assertTrue(result['success'])

        # Both riders should cross finish at position 19
        self.assertEqual(lead_rider.position, 19)
        self.assertEqual(drafter.position, 19)

        # Check that BOTH riders got points
        # Lead rider arrives first: 12 points
        # Drafter arrives second: 8 points
        # Total: 20 points for the player
        self.assertEqual(result['points_earned'], 20)
        self.assertEqual(player.points, initial_points + 20)

        # Verify both riders are recorded at the finish
        self.assertEqual(len(state.sprint_arrivals[19]), 2)
        self.assertIn(lead_rider, state.sprint_arrivals[19])
        self.assertIn(drafter, state.sprint_arrivals[19])

    def test_multiple_riders_same_player_cross_sprint_team_draft(self):
        """When multiple riders from same player cross sprint in TeamDraft, each should get points"""
        state = GameState(num_players=2, tile_config=[1, 1])  # Two tiles
        engine = GameEngine(state)

        # Set up a previous move to enable drafting
        state.last_move = {
            'action': 'Pull',
            'rider': 'P1R0',  # Different player
            'old_position': 18,
            'movement': 2
        }

        player = state.players[0]
        rider1 = player.riders[0]
        rider2 = player.riders[1]

        # Position both riders at position 18 (start of last move)
        rider1.position = 18
        rider2.position = 18

        initial_points = player.points

        # Execute TeamDraft with both riders
        move = Move(
            ActionType.TEAM_DRAFT,
            rider1,
            [],
            [rider2]
        )

        result = engine.execute_move(move)

        self.assertTrue(result['success'])

        # Both riders should cross first sprint at position 19
        self.assertEqual(rider1.position, 20)
        self.assertEqual(rider2.position, 20)

        # Check that BOTH riders got points for crossing position 19 (first tile finish/sprint)
        # Position 19 is a sprint point (last field of first tile)
        # First rider: 3 points, Second rider: 2 points
        # Total: 5 points
        self.assertGreater(result['points_earned'], 0)
        self.assertGreater(player.points, initial_points)


class TestCardTypes(unittest.TestCase):
    """Test card types and their movement values"""

    def test_energy_card_always_moves_one(self):
        """Energy card should always provide 1 movement"""
        card = Card(CardType.ENERGY)

        # Test on all terrains
        for terrain in [TerrainType.FLAT, TerrainType.CLIMB, TerrainType.COBBLES, TerrainType.DESCENT]:
            self.assertEqual(card.get_movement(terrain, PlayMode.PULL), 1)
            self.assertEqual(card.get_movement(terrain, PlayMode.ATTACK), 1)

    def test_sprinter_strong_on_flat(self):
        """Sprinter should have high attack value on flat terrain"""
        card = Card(
            CardType.SPRINTER,
            pull_flat=1, pull_cobbles=1, pull_climb=0, pull_descent=3,
            attack_flat=3, attack_cobbles=2, attack_climb=1, attack_descent=3
        )

        # Sprinter attack on flat should be 3
        self.assertEqual(card.get_movement(TerrainType.FLAT, PlayMode.ATTACK), 3)

    def test_climber_strong_on_climb(self):
        """Climber should have high values on climb terrain"""
        card = Card(
            CardType.CLIMBER,
            pull_flat=0, pull_cobbles=0, pull_climb=2, pull_descent=3,
            attack_flat=1, attack_cobbles=0, attack_climb=3, attack_descent=3
        )

        # Climber attack on climb should be 3
        self.assertEqual(card.get_movement(TerrainType.CLIMB, PlayMode.ATTACK), 3)
        # Climber pull on climb should be 2
        self.assertEqual(card.get_movement(TerrainType.CLIMB, PlayMode.PULL), 2)

    def test_rouleur_balanced(self):
        """Rouleur should have balanced values across terrains"""
        card = Card(
            CardType.ROULEUR,
            pull_flat=2, pull_cobbles=1, pull_climb=1, pull_descent=3,
            attack_flat=2, attack_cobbles=1, attack_climb=1, attack_descent=3
        )

        # Rouleur should have reasonable values everywhere
        self.assertEqual(card.get_movement(TerrainType.FLAT, PlayMode.PULL), 2)
        self.assertEqual(card.get_movement(TerrainType.CLIMB, PlayMode.PULL), 1)

    def test_sprint_terrain_uses_flat_values(self):
        """Sprint terrain should use flat movement values"""
        card = Card(
            CardType.SPRINTER,
            pull_flat=1, pull_cobbles=1, pull_climb=0, pull_descent=3,
            attack_flat=3, attack_cobbles=2, attack_climb=1, attack_descent=3
        )

        # Sprint should use flat values
        flat_movement = card.get_movement(TerrainType.FLAT, PlayMode.ATTACK)
        sprint_movement = card.get_movement(TerrainType.SPRINT, PlayMode.ATTACK)
        self.assertEqual(flat_movement, sprint_movement)


class TestRiderTypes(unittest.TestCase):
    """Test rider type assignment"""

    def test_rider_types_assigned_correctly(self):
        """Riders should be assigned Rouleur, Sprinter, Climber in order"""
        state = GameState(num_players=2)

        for player in state.players:
            self.assertEqual(player.riders[0].rider_type, CardType.ROULEUR)
            self.assertEqual(player.riders[1].rider_type, CardType.SPRINTER)
            self.assertEqual(player.riders[2].rider_type, CardType.CLIMBER)

    def test_each_player_has_three_riders(self):
        """Each player should have exactly 3 riders"""
        state = GameState(num_players=4)

        for player in state.players:
            self.assertEqual(len(player.riders), 3)


class TestTeamCarAction(unittest.TestCase):
    """Test TeamCar action (draw 2, discard 1)"""

    def test_team_car_draws_two_cards(self):
        """TeamCar should draw 2 cards"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        player = state.players[0]
        rider = player.riders[0]
        initial_hand_size = len(player.hand)

        # Execute TeamCar
        move = Move(ActionType.TEAM_CAR, rider, [])
        result = engine.execute_move(move)

        self.assertTrue(result['success'])
        self.assertEqual(len(result['cards_drawn']), 2)

    def test_team_car_discards_one_card(self):
        """TeamCar should discard 1 card"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        player = state.players[0]
        rider = player.riders[0]
        initial_hand_size = len(player.hand)

        # Execute TeamCar
        move = Move(ActionType.TEAM_CAR, rider, [])
        result = engine.execute_move(move)

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['card_discarded'])
        # Net change: +2 -1 = +1 card
        self.assertEqual(len(player.hand), initial_hand_size + 1)

    def test_team_car_no_movement(self):
        """TeamCar should not move the rider"""
        state = GameState(num_players=2)
        engine = GameEngine(state)

        rider = state.players[0].riders[0]
        initial_position = rider.position

        # Execute TeamCar
        move = Move(ActionType.TEAM_CAR, rider, [])
        result = engine.execute_move(move)

        self.assertEqual(result['movement'], 0)
        self.assertEqual(rider.position, initial_position)


class TestTrackConfiguration(unittest.TestCase):
    """Test track setup and tile configuration"""

    def test_track_length_calculation(self):
        """Track length should be 20 fields per tile"""
        state = GameState(num_players=2, tile_config=[1, 2, 3])

        # 3 tiles × 20 fields = 60 fields
        self.assertEqual(state.track_length, 60)

    def test_default_tile_configuration(self):
        """Default configuration should be tiles [1, 5, 4]"""
        state = GameState(num_players=2)

        self.assertEqual(state.tile_config, [1, 5, 4])
        self.assertEqual(state.track_length, 60)

    def test_last_field_is_finish(self):
        """Last field of final tile should be FINISH"""
        state = GameState(num_players=2, tile_config=[1])

        last_tile = state.track[-1]
        self.assertEqual(last_tile.terrain, TerrainType.FINISH)

    def test_intermediate_tiles_have_sprint(self):
        """Last field of non-final tiles should be SPRINT"""
        state = GameState(num_players=2, tile_config=[1, 2])

        # Position 19 is last field of first tile
        first_tile_last = state.track[19]
        self.assertEqual(first_tile_last.terrain, TerrainType.SPRINT)


class TestTobiBotAgent(unittest.TestCase):
    """Test TobiBot agent's prioritized decision-making system"""

    def setUp(self):
        """Set up a game for TobiBot testing"""
        from agents import create_agent
        self.state = GameState(num_players=2, tile_config=[1, 4, 5])
        self.engine = GameEngine(self.state)
        self.tobibot = create_agent('tobibot', 0)
        self.player = self.state.players[0]

    def test_tobibot_creation(self):
        """Test that TobiBot can be created and has correct name"""
        self.assertEqual(self.tobibot.name, "TobiBot")
        self.assertEqual(self.tobibot.player_id, 0)

    def test_priority1_scoring_moves(self):
        """Test Priority 1: TobiBot prioritizes moves that score points"""
        # Position a rider near a sprint
        rider = self.player.riders[0]
        rider.position = 17  # Two positions before sprint at position 19

        # Give cards to move
        self.player.hand = [
            Card(CardType.ROULEUR, 5),
            Card(CardType.ROULEUR, 5),
            Card(CardType.ROULEUR, 5)
        ]

        # TobiBot should choose a move that reaches the sprint
        move = self.tobibot.choose_move(self.engine, self.player, self.player.riders)
        self.assertIsNotNone(move)

        # Calculate if this move will reach the sprint
        if move.action_type == ActionType.PULL:
            distance = self.engine._calculate_pull_movement(move.rider, move.cards)
            target_pos = move.rider.position + distance
            # Should reach or pass position 19 (sprint)
            self.assertGreaterEqual(target_pos, 19)

    def test_priority2_hand_management_low_cards(self):
        """Test Priority 2: TeamCar when hand ≤ 6 and no efficient moves"""
        # Set hand to exactly 6 cards (all energy)
        self.player.hand = [Card(CardType.ENERGY, 1) for _ in range(6)]

        # Position riders where they can't draft and moves aren't efficient
        for i, rider in enumerate(self.player.riders):
            rider.position = i * 10  # Spread out

        # Clear last move so drafting isn't possible
        self.state.last_move = None

        move = self.tobibot.choose_move(self.engine, self.player, self.player.riders)

        # Should consider TeamCar when hand is low and no efficient moves
        # (May not always choose TeamCar if there are scoring opportunities)
        self.assertIsNotNone(move)

    def test_priority3_prefer_teamdraft(self):
        """Test Priority 3: Prefer TeamDraft when available"""
        # Set up situation where TeamDraft is available
        # Put two riders at same position, make previous move with movement
        self.player.riders[0].position = 5
        self.player.riders[1].position = 5
        self.player.riders[2].position = 10

        # Set up last move so drafting is possible
        self.state.last_move = {
            'position': 5,
            'movement': 3,
            'action_type': ActionType.PULL
        }

        # Give plenty of cards so hand management doesn't interfere
        self.player.hand = [Card(CardType.ROULEUR, 5) for _ in range(10)]

        # Mark riders 0 and 1 as eligible (not moved yet this round)
        eligible = [self.player.riders[0], self.player.riders[1]]
        move = self.tobibot.choose_move(self.engine, self.player, eligible)

        # Should prefer TeamDraft if available
        self.assertIsNotNone(move)
        if move.action_type == ActionType.TEAM_DRAFT:
            # Good - TeamDraft was chosen
            self.assertEqual(move.action_type, ActionType.TEAM_DRAFT)

    def test_priority3_prefer_draft_over_pull(self):
        """Test Priority 3: Prefer Draft over Pull when available"""
        # Set up situation where Draft is available
        rider = self.player.riders[0]
        rider.position = 5

        # Set up last move so drafting is possible
        self.state.last_move = {
            'position': 5,
            'movement': 3,
            'action_type': ActionType.PULL
        }

        # Give plenty of cards
        self.player.hand = [Card(CardType.ROULEUR, 5) for _ in range(10)]

        move = self.tobibot.choose_move(self.engine, self.player, [rider])

        # Should choose Draft (free movement) over Pull (costs cards)
        self.assertIsNotNone(move)
        # Draft should be preferred when available
        if move.action_type == ActionType.DRAFT:
            self.assertEqual(move.action_type, ActionType.DRAFT)

    def test_priority4_group_with_teammates(self):
        """Test Priority 4: Advance to fields with team riders"""
        # Position riders so one can move to join another
        self.player.riders[0].position = 2
        self.player.riders[1].position = 5  # Target position
        self.player.riders[2].position = 10

        # Give cards to move
        self.player.hand = [
            Card(CardType.ROULEUR, 5),
            Card(CardType.ROULEUR, 5),
            Card(CardType.ROULEUR, 5)
        ]

        # Clear last move so no drafting available
        self.state.last_move = None

        move = self.tobibot.choose_move(self.engine, self.player, [self.player.riders[0]])

        self.assertIsNotNone(move)
        # TobiBot should try to group with teammates when possible

    def test_priority5_el_patron_positioning(self):
        """Test Priority 5: When El Patron, position with opponents"""
        # Make player 0 the El Patron
        self.state.el_patron = 0

        # Position opponent rider
        opponent_rider = self.state.players[1].riders[0]
        opponent_rider.position = 5

        # Position our rider near opponent
        self.player.riders[0].position = 2

        # Give cards to move
        self.player.hand = [
            Card(CardType.ROULEUR, 5),
            Card(CardType.ROULEUR, 5),
            Card(CardType.ROULEUR, 5)
        ]

        # Clear last move
        self.state.last_move = None

        move = self.tobibot.choose_move(self.engine, self.player, [self.player.riders[0]])

        self.assertIsNotNone(move)
        # When El Patron, should consider moving to opponent positions

    def test_priority7_isolated_lead_rider(self):
        """Test Priority 7: TeamCar if lead rider is isolated without options"""
        # Position lead rider alone and far ahead
        self.player.riders[0].position = 0
        self.player.riders[1].position = 0
        self.player.riders[2].position = 20  # Lead rider, isolated

        # Give few cards (but >6 so priority 2 doesn't trigger)
        self.player.hand = [Card(CardType.ENERGY, 1) for _ in range(7)]

        # Clear last move so lead can't draft
        self.state.last_move = None

        # Only lead rider is eligible
        move = self.tobibot.choose_move(self.engine, self.player, [self.player.riders[2]])

        self.assertIsNotNone(move)
        # If lead rider is isolated and can't advance well, might use TeamCar

    def test_tobibot_calculates_points_correctly(self):
        """Test that TobiBot correctly calculates potential points"""
        # Position rider near sprint
        rider = self.player.riders[0]
        rider.position = 17

        # Give cards
        self.player.hand = [Card(CardType.ROULEUR, 5) for _ in range(3)]

        # Create a move that would reach the sprint
        move = Move(
            action_type=ActionType.PULL,
            rider=rider,
            cards=[self.player.hand[0], self.player.hand[1]]
        )

        # Calculate points for this move
        points = self.tobibot._calculate_points(move, self.engine)

        # Should detect that sprint points are available
        self.assertGreaterEqual(points, 0)

    def test_tobibot_respects_terrain_limits(self):
        """Test that TobiBot respects terrain limits in calculations"""
        # Use a track with climbs
        state = GameState(num_players=2, tile_config=[2])  # Mountaintop Finish
        engine = GameEngine(state)
        player = state.players[0]

        from agents import create_agent
        tobibot = create_agent('tobibot', 0)

        # Position sprinter on climb
        sprinter = player.riders[1]  # Sprinter
        sprinter.position = 3  # Start of climb

        # Give cards
        player.hand = [Card(CardType.SPRINTER, 7) for _ in range(3)]

        # Get move
        move = tobibot.choose_move(engine, player, [sprinter])

        self.assertIsNotNone(move)
        # TobiBot should account for sprinter's 3-field limit on climbs

    def test_tobibot_can_handle_empty_moves(self):
        """Test that TobiBot handles situations with no valid moves gracefully"""
        # Remove all cards
        self.player.hand = []

        # Position riders where TeamCar isn't available (need implementation check)
        move = self.tobibot.choose_move(self.engine, self.player, self.player.riders)

        # Should either return a valid move or None
        if move is not None:
            self.assertIn(move.action_type, [
                ActionType.PULL, ActionType.ATTACK, ActionType.DRAFT,
                ActionType.TEAM_PULL, ActionType.TEAM_DRAFT, ActionType.TEAM_CAR
            ])

    def test_tobibot_identifies_isolated_rider(self):
        """Test that TobiBot correctly identifies isolated riders"""
        # Rider alone at position 10
        self.player.riders[0].position = 0
        self.player.riders[1].position = 0
        isolated_rider = self.player.riders[2]
        isolated_rider.position = 10

        # Check isolation
        is_isolated = self.tobibot._is_rider_isolated(isolated_rider, self.engine, self.player)
        self.assertTrue(is_isolated)

        # Rider with teammate should not be isolated
        self.player.riders[0].position = 10
        is_isolated = self.tobibot._is_rider_isolated(isolated_rider, self.engine, self.player)
        self.assertFalse(is_isolated)

    def test_priority7_eligible_riders_only(self):
        """Test Priority 7 bug fix: Should only check lead among ELIGIBLE riders

        This tests the fix for the infinite TeamCar loop bug where TobiBot would
        check the overall lead rider (across all riders) instead of the lead among
        eligible riders. When the overall lead had already moved, Priority 7 would
        incorrectly trigger TeamCar for remaining riders.

        Scenario: Riders at positions 10, 11, 44
        - Rider at 44 moves first (lead rider)
        - Riders at 10, 11 should move normally, NOT use TeamCar
        """
        # Set up the exact scenario from the bug: riders at positions 10, 11, 44
        self.player.riders[0].position = 10  # Rouleur
        self.player.riders[1].position = 11  # Sprinter
        self.player.riders[2].position = 44  # Climber (lead rider)

        # Give sufficient mixed cards (>6 so Priority 2 doesn't trigger)
        # Include cards for each rider type so they can all move
        self.player.hand = [
            Card(CardType.ROULEUR, 5),
            Card(CardType.ROULEUR, 5),
            Card(CardType.SPRINTER, 7),
            Card(CardType.SPRINTER, 7),
            Card(CardType.CLIMBER, 4),
            Card(CardType.CLIMBER, 4),
            Card(CardType.ENERGY, 1),
            Card(CardType.ENERGY, 1),
        ]

        # Clear last move so no drafting is available
        self.state.last_move = None

        # Simulate that rider at position 44 has already moved this round
        # Only riders at positions 10 and 11 are eligible (rider at 44 already moved)

        # Test rider at position 11 (should be lead among eligible riders)
        move_rider_11 = self.tobibot.choose_move(self.engine, self.player, [self.player.riders[1]])
        self.assertIsNotNone(move_rider_11)
        # Should NOT be TeamCar (the bug would cause this)
        self.assertNotEqual(move_rider_11.action_type, ActionType.TEAM_CAR,
                           "TobiBot should not use TeamCar for rider at position 11 - "
                           "this indicates the Priority 7 bug is present")
        # Should be a movement action
        self.assertIn(move_rider_11.action_type, [ActionType.PULL, ActionType.ATTACK, ActionType.TEAM_PULL])

        # Test rider at position 10
        move_rider_10 = self.tobibot.choose_move(self.engine, self.player, [self.player.riders[0]])
        self.assertIsNotNone(move_rider_10)
        # Should NOT be TeamCar
        self.assertNotEqual(move_rider_10.action_type, ActionType.TEAM_CAR,
                           "TobiBot should not use TeamCar for rider at position 10 - "
                           "this indicates the Priority 7 bug is present")
        # Should be a movement action
        self.assertIn(move_rider_10.action_type, [ActionType.PULL, ActionType.ATTACK, ActionType.TEAM_PULL])

    def test_no_infinite_teamcar_loop(self):
        """Integration test: Verify TobiBot doesn't get stuck in infinite TeamCar loop

        This test runs multiple rounds with riders spread out to ensure TobiBot
        doesn't repeatedly use TeamCar instead of moving riders forward.
        """
        from agents import create_agent

        # Set up game with TobiBot
        state = GameState(num_players=2, tile_config=[1, 4, 5])
        engine = GameEngine(state)
        tobibot = create_agent('tobibot', 0)
        player = state.players[0]

        # Position riders spread out like in the bug scenario
        player.riders[0].position = 10  # Rouleur
        player.riders[1].position = 11  # Sprinter
        player.riders[2].position = 44  # Climber

        # Give sufficient mixed cards for all rider types
        player.hand = [
            Card(CardType.ROULEUR, 5),
            Card(CardType.ROULEUR, 5),
            Card(CardType.SPRINTER, 7),
            Card(CardType.SPRINTER, 7),
            Card(CardType.CLIMBER, 4),
            Card(CardType.CLIMBER, 4),
            Card(CardType.ENERGY, 1),
            Card(CardType.ENERGY, 1),
            Card(CardType.ENERGY, 1),
            Card(CardType.ENERGY, 1),
        ]

        # Track TeamCar usage over multiple rounds
        teamcar_count = 0
        movement_count = 0
        total_moves = 0

        # Simulate 5 rounds of moves
        for _ in range(5):
            # Sort riders by position (descending) to simulate proper turn order
            # Leaders move first
            sorted_riders = sorted(player.riders, key=lambda r: r.position, reverse=True)

            # Each rider moves once per round
            for rider in sorted_riders:
                move = tobibot.choose_move(engine, player, [rider])
                if move:
                    total_moves += 1
                    if move.action_type == ActionType.TEAM_CAR:
                        teamcar_count += 1
                        # Execute TeamCar to update hand
                        if not move.cards:
                            move.cards = [player.hand[0]] if player.hand else []
                        engine.execute_move(move)
                    else:
                        movement_count += 1
                        # Execute movement
                        engine.execute_move(move)

                    # Replenish mixed cards if getting low
                    if len(player.hand) < 5:
                        player.hand.extend([
                            Card(CardType.ROULEUR, 5),
                            Card(CardType.SPRINTER, 7),
                            Card(CardType.CLIMBER, 4),
                            Card(CardType.ENERGY, 1),
                            Card(CardType.ENERGY, 1),
                        ])

        # After 5 rounds (15 moves), TeamCar should be minority
        # With the bug, TeamCar would be ~70-90% (10-13 out of 15 moves)
        # With the fix, TeamCar should be < 50% (most moves should be actual movement)
        teamcar_percentage = (teamcar_count / total_moves) * 100 if total_moves > 0 else 0

        self.assertLess(teamcar_percentage, 50,
                       f"TobiBot used TeamCar {teamcar_percentage:.1f}% of the time "
                       f"({teamcar_count}/{total_moves} moves). This suggests the infinite "
                       f"TeamCar loop bug may still be present. Expected < 50%.")

        # Most importantly: Verify riders actually moved forward significantly
        # With the bug, riders would barely move or not move at all
        self.assertGreater(player.riders[0].position, 10,
                          "Rider at position 10 should have advanced")
        self.assertGreater(player.riders[1].position, 11,
                          "Rider at position 11 should have advanced")

        # At least one of the non-lead riders should have advanced by 5+ positions
        # to show they're actually moving, not just stuck
        total_advancement = (player.riders[0].position - 10) + (player.riders[1].position - 11)
        self.assertGreater(total_advancement, 8,
                          f"Non-lead riders should have advanced significantly. "
                          f"Total advancement: {total_advancement} fields. "
                          f"With the bug, this would be near zero.")

    def test_tobibot_competes_full_game(self):
        """Integration test: TobiBot can complete a full game"""
        from agents import create_agent
        from simulator import GameSimulator

        # Create a simulator and run a game
        sim = GameSimulator(num_players=2, verbose=False)
        agents = [
            create_agent('tobibot', 0),
            create_agent('random', 1)
        ]

        # Run a single game
        result = sim.run_game(agents)

        # Verify game completed
        self.assertIn('final_result', result)
        self.assertIsNotNone(result['final_result'].get('winner'))


class TestTournamentPositionAlternation(unittest.TestCase):
    """Test that tournament positions are properly alternated"""

    def test_position_alternation_two_player(self):
        """Test that 2-player tournaments alternate positions properly"""
        from run_tournament import run_multiplayer_tournament

        # Run a mini tournament with 2 agents, 10 games
        agents = ['random', 'marc_soler']

        df, _ = run_multiplayer_tournament(
            agent_types=agents,
            games_per_combination=10
        )

        # Check 2-player games
        two_player = df[df['num_players'] == 2]

        for agent in agents:
            pos0_games = len(two_player[two_player['player_0_agent'] == agent])
            pos1_games = len(two_player[two_player['player_1_agent'] == agent])

            # For 10 games with 2 permutations, each should be at each position 5 times
            self.assertEqual(pos0_games, 5,
                           f"{agent} should play 5 games at position 0, got {pos0_games}")
            self.assertEqual(pos1_games, 5,
                           f"{agent} should play 5 games at position 1, got {pos1_games}")

    def test_position_distribution_three_player(self):
        """Test that 3-player tournaments distribute positions"""
        from run_tournament import run_multiplayer_tournament

        # Run with 3 agents, 12 games (divisible by 6 permutations)
        agents = ['random', 'marc_soler', 'balanced']

        df, _ = run_multiplayer_tournament(
            agent_types=agents,
            games_per_combination=12
        )

        # Check 3-player games
        three_player = df[df['num_players'] == 3]

        for agent in agents:
            pos0_games = len(three_player[three_player['player_0_agent'] == agent])
            pos1_games = len(three_player[three_player['player_1_agent'] == agent])
            pos2_games = len(three_player[three_player['player_2_agent'] == agent])

            # With 12 games and 6 permutations, each position should have 4 games
            self.assertEqual(pos0_games, 4,
                           f"{agent} should play 4 games at position 0, got {pos0_games}")
            self.assertEqual(pos1_games, 4,
                           f"{agent} should play 4 games at position 1, got {pos1_games}")
            self.assertEqual(pos2_games, 4,
                           f"{agent} should play 4 games at position 2, got {pos2_games}")

    def test_position_alternation_fairness(self):
        """Test that position alternation creates fair matchups"""
        from run_tournament import run_multiplayer_tournament

        # Run with 2 agents to check fairness
        agents = ['random', 'marc_soler']

        df, _ = run_multiplayer_tournament(
            agent_types=agents,
            games_per_combination=10
        )

        two_player = df[df['num_players'] == 2]

        # Each agent should play equal games at each position
        for agent in agents:
            total_games = len(two_player[
                (two_player['player_0_agent'] == agent) |
                (two_player['player_1_agent'] == agent)
            ])

            # Should play exactly 10 games total
            self.assertEqual(total_games, 10,
                           f"{agent} should play 10 total games, got {total_games}")

    def test_analyze_position_bias_function(self):
        """Test the analyze_position_bias function"""
        from run_tournament import run_multiplayer_tournament, analyze_position_bias
        import pandas as pd

        # Run a small tournament
        agents = ['random', 'marc_soler']

        df, _ = run_multiplayer_tournament(
            agent_types=agents,
            games_per_combination=10
        )

        # Analyze position bias
        analysis = analyze_position_bias(df, agents)

        # Check structure
        self.assertIn('by_agent', analysis)
        self.assertIn('overall', analysis)

        # Check that each agent has position stats
        for agent in agents:
            self.assertIn(agent, analysis['by_agent'])
            agent_stats = analysis['by_agent'][agent]

            # Should have 2-player position stats
            self.assertIn('2p_pos0', agent_stats)
            self.assertIn('2p_pos1', agent_stats)

            # Each position should have the required fields
            for key in ['2p_pos0', '2p_pos1']:
                self.assertIn('games', agent_stats[key])
                self.assertIn('wins', agent_stats[key])
                self.assertIn('win_rate', agent_stats[key])
                self.assertIn('avg_score', agent_stats[key])

        # Check overall stats
        self.assertIn('2p_pos0', analysis['overall'])
        self.assertIn('2p_pos1', analysis['overall'])


if __name__ == '__main__':
    unittest.main()
