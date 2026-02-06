"""
Tests for terrain limits feature.

Terrain limits:
- Sprinter: max 3 fields per round on CLIMB terrain
- Rouleur: max 4 fields per round on CLIMB terrain
- Climber: max 3 fields per round on COBBLES terrain

The limit only applies to the portion of the move that is on limited terrain.
"""

import unittest
from game_state import GameState, TerrainType, CardType, Card, PlayMode, RACE_TILES
from game_engine import GameEngine, Move, ActionType, TERRAIN_LIMITS


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
        # Get sprinter (rider_id=1)
        sprinter = self.state.players[0].riders[1]
        self.assertEqual(sprinter.rider_type, CardType.SPRINTER)

        # Position sprinter at start of climb section (position 3 in tile 2)
        sprinter.position = 3  # First climb position

        # Try to move 6 fields - should be limited to 3
        actual_movement = self.engine._calculate_limited_movement(sprinter, 3, 6)
        self.assertEqual(actual_movement, 3)

    def test_rouleur_climb_limit(self):
        """Rouleur should be limited to 4 fields on climb terrain"""
        # Get rouleur (rider_id=0)
        rouleur = self.state.players[0].riders[0]
        self.assertEqual(rouleur.rider_type, CardType.ROULEUR)

        # Position rouleur at start of climb section
        rouleur.position = 3

        # Try to move 6 fields - should be limited to 4
        actual_movement = self.engine._calculate_limited_movement(rouleur, 3, 6)
        self.assertEqual(actual_movement, 4)

    def test_climber_cobbles_limit(self):
        """Climber should be limited to 3 fields on cobbles terrain"""
        # Get climber (rider_id=2)
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
        # First 3 positions of tile 2 are flat
        actual_movement = self.engine._calculate_limited_movement(sprinter, 0, 3)
        self.assertEqual(actual_movement, 3)

    def test_partial_terrain_limit_flat_to_climb(self):
        """Limit should only apply to the climb portion when moving from flat to climb"""
        sprinter = self.state.players[0].riders[1]

        # Position at position 1 (flat), move 6 fields
        # Fields 0-2 are flat, fields 3+ are climb
        # From position 1: fields 2, 3, 4, 5, 6, 7 would be crossed
        # Field 2 is flat (1 field), fields 3-7 are climb
        # Sprinter can move 1 flat + 3 climb = 4 fields total
        sprinter.position = 1

        actual_movement = self.engine._calculate_limited_movement(sprinter, 1, 6)
        # Position 1 -> Position 2 (flat) -> Position 3 (climb) -> Position 4 (climb) -> Position 5 (climb) -> STOP
        # That's 2 flat + 3 climb = 4 total, but we only have 1 flat field (position 2)
        # Actually: from position 1, moving to 2 (flat), 3 (climb), 4 (climb), 5 (climb) = 4 moves
        # Wait: position 1 is still flat (0-indexed, positions 0,1,2 are flat)
        # Position 1 -> 2 (flat) -> 3 (climb) -> 4 (climb) -> 5 (climb) -> stop
        # That's moving through 1 flat field (2) then 3 climb fields (3,4,5) = 4 total
        self.assertEqual(actual_movement, 4)

    def test_partial_terrain_limit_climb_to_descent(self):
        """Movement from climb to descent - descent has no limits"""
        # Use tile 4 which has climb + descent
        state = GameState(num_players=2, tile_config=[4])
        engine = GameEngine(state)
        # Tile 4: 2 flat + 12 climb + 6 descent

        sprinter = state.players[0].riders[1]

        # Position at end of climb section, about to enter descent
        # Climb: positions 2-13, Descent: positions 14-19
        # Position sprinter at position 11, try to move 8 fields
        # Fields 12, 13 are climb (2 more climb fields), 14-19 are descent
        sprinter.position = 11

        # Moving 8: 12 (climb), 13 (climb), 14 (descent), 15 (descent), 16 (descent), etc.
        # Sprinter limit is 3 on climb, but we're only crossing 2 climb fields
        # So no limit is hit - all 8 fields should be possible (track length permitting)
        actual_movement = engine._calculate_limited_movement(sprinter, 11, 8)
        self.assertEqual(actual_movement, 8)

    def test_team_draft_per_rider_limits(self):
        """In TeamDraft, each rider should apply their own terrain limits"""
        # Position all riders of player 0 at same position in climb section
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
            'movement': 6,  # Base movement of 6
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
        # All start at 5, base movement is 6
        # Rouleur: limited to 4 climb fields -> ends at 9
        # Sprinter: limited to 3 climb fields -> ends at 8
        # Climber: no limit -> ends at 11

        self.assertEqual(rouleur.position, 9)
        self.assertEqual(sprinter.position, 8)
        self.assertEqual(climber.position, 11)

    def test_team_pull_per_rider_limits(self):
        """In TeamPull, lead rider and drafters apply their own terrain limits"""
        # Give player enough cards for a pull
        player = self.state.players[0]

        # Create cards for a 6-movement pull on climb
        # Climber cards give 3 movement in attack mode on climb, 2 in pull mode
        # Energy cards give 1 each
        # Let's use 3 energy cards for a base movement of 3 (too small)
        # Actually let's position riders and use climber to pull

        climber = player.riders[2]  # Climber pulls - no limit on climb
        rouleur = player.riders[0]  # Max 4 on climb
        sprinter = player.riders[1]  # Max 3 on climb

        # Position all at position 3 (start of climb)
        climber.position = 3
        rouleur.position = 3
        sprinter.position = 3

        # Create cards for climber to pull with
        # Climber card in PULL mode on climb = 2 movement
        # 3 climber cards = 6 movement
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
            player.hand[:3],  # Use all 3 cards for 6 movement
            [rouleur, sprinter]
        )

        result = self.engine.execute_move(move)

        self.assertTrue(result['success'])

        # Check positions
        # Climber: no limit on climb, moves full 6 -> position 9
        # Rouleur: limit of 4 on climb -> position 7
        # Sprinter: limit of 3 on climb -> position 6

        self.assertEqual(climber.position, 9)
        self.assertEqual(rouleur.position, 7)
        self.assertEqual(sprinter.position, 6)


class TestTerrainLimitEdgeCases(unittest.TestCase):
    """Test edge cases for terrain limits"""

    def test_limit_at_track_end(self):
        """Terrain limit should not allow movement past track end"""
        state = GameState(num_players=2, tile_config=[2])  # 20 field track, mostly climb
        engine = GameEngine(state)

        sprinter = state.players[0].riders[1]
        sprinter.position = 18  # Near end of track

        # Try to move 5 fields - limited by both terrain (3) and track end
        actual_movement = engine._calculate_limited_movement(sprinter, 18, 5)
        # Track length is 20, so max position is 19
        # From 18, max movement is 1 to reach 19
        self.assertEqual(actual_movement, 1)

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


if __name__ == '__main__':
    unittest.main()
