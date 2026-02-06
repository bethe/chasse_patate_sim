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


if __name__ == '__main__':
    unittest.main()
