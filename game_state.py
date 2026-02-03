"""
Chasse Patate - Game State Management
Handles all game state, cards, and rules
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import random


class CardType(Enum):
    """Types of rider cards"""
    ROULEUR = "Rouleur"
    SPRINTEUR = "Sprinteur"
    GRIMPEUR = "Grimpeur"


class TerrainType(Enum):
    """Types of terrain"""
    FLAT = "Flat"
    COBBLES = "Cobbles"
    CLIMB = "Climb"
    DESCENT = "Descent"
    SPRINT = "Sprint"  # Special marker for sprint points
    FINISH = "Finish"  # Special marker for finish line


@dataclass
class Card:
    """Represents a rider card"""
    card_type: CardType
    movement_flat: int
    movement_cobbles: int
    movement_climb: int
    movement_descent: int
    
    def get_movement(self, terrain: TerrainType) -> int:
        """Get movement value for terrain"""
        if terrain == TerrainType.FLAT:
            return self.movement_flat
        elif terrain == TerrainType.COBBLES:
            return self.movement_cobbles
        elif terrain == TerrainType.CLIMB:
            return self.movement_climb
        elif terrain == TerrainType.DESCENT:
            return self.movement_descent
        elif terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
            # Use flat movement for special tiles
            return self.movement_flat
        return 0


@dataclass
class Rider:
    """Represents a rider on the track"""
    player_id: int
    rider_id: int  # 0-2 for each player's three riders
    position: int = 0  # Track position
    
    def __hash__(self):
        return hash((self.player_id, self.rider_id))
    
    def __eq__(self, other):
        if isinstance(other, Rider):
            return self.player_id == other.player_id and self.rider_id == other.rider_id
        return False


@dataclass
class RaceTile:
    """Represents one of the 5 race track tiles (20 fields each)"""
    tile_id: int
    nickname: str
    terrain_map: List[TerrainType]  # 20 terrain types for fields 0-19
    
    def __post_init__(self):
        assert len(self.terrain_map) == 20, f"Tile must have exactly 20 fields, got {len(self.terrain_map)}"


# The 5 race tiles as defined in the game
RACE_TILES = {
    1: RaceTile(
        tile_id=1,
        nickname="Flat",
        terrain_map=[TerrainType.FLAT] * 20
    ),
    2: RaceTile(
        tile_id=2,
        nickname="Mountaintop Finish",
        terrain_map=[TerrainType.FLAT] * 3 + [TerrainType.CLIMB] * 17
    ),
    3: RaceTile(
        tile_id=3,
        nickname="Champs Elysees",
        terrain_map=[TerrainType.FLAT] * 8 + [TerrainType.COBBLES] * 12
    ),
    4: RaceTile(
        tile_id=4,
        nickname="Up and Down",
        terrain_map=[TerrainType.FLAT] * 2 + [TerrainType.CLIMB] * 12 + [TerrainType.DESCENT] * 6
    ),
    5: RaceTile(
        tile_id=5,
        nickname="Paris-Roubaix",
        # Fields 1-2: Flat, 3-7: Cobbles, 8: Flat (field 8 is missing in spec, assuming Flat)
        # 9-13: Flat, 14-18: Cobbles, 19-20: Flat
        terrain_map=(
            [TerrainType.FLAT] * 2 +      # Fields 1-2
            [TerrainType.COBBLES] * 5 +   # Fields 3-7
            [TerrainType.FLAT] * 6 +      # Fields 8-13
            [TerrainType.COBBLES] * 5 +   # Fields 14-18
            [TerrainType.FLAT] * 2        # Fields 19-20
        )
    )
}

# Default race configuration: Tile 1, Tile 5, Tile 4
DEFAULT_RACE_CONFIG = [1, 5, 4]


@dataclass
class Player:
    """Represents a player in the game"""
    player_id: int
    name: str
    hand: List[Card] = field(default_factory=list)
    riders: List[Rider] = field(default_factory=list)
    points: int = 0
    
    def __post_init__(self):
        if not self.riders:
            self.riders = [Rider(self.player_id, i) for i in range(3)]


@dataclass
class TrackTile:
    """Represents a tile on the track"""
    position: int
    terrain: TerrainType
    sprint_points: Optional[List[int]] = None  # Points for positions [1st, 2nd, 3rd]
    
    def __post_init__(self):
        if self.terrain == TerrainType.SPRINT and self.sprint_points is None:
            self.sprint_points = [5, 3, 1]


class GameState:
    """Main game state"""
    
    # Card distributions per rulebook
    # Format: (flat, cobbles, climb, descent)
    # TODO: Update these values based on actual card specifications
    CARD_DISTRIBUTION = {
        CardType.ROULEUR: [(7, 5, 3, 5)] * 9,      # Placeholder values
        CardType.SPRINTEUR: [(9, 6, 3, 6)] * 9,    # Placeholder values
        CardType.GRIMPEUR: [(5, 4, 9, 7)] * 9,     # Placeholder values
    }
    
    def __init__(self, num_players: int, tile_config: List[int] = None):
        assert 2 <= num_players <= 5, "Game supports 2-5 players"
        
        self.num_players = num_players
        
        # Use default tile configuration if none provided
        if tile_config is None:
            tile_config = DEFAULT_RACE_CONFIG
        
        self.tile_config = tile_config
        self.track_length = len(tile_config) * 20  # Each tile is 20 fields
        
        self.current_turn = 0
        self.current_player_idx = 0
        self.game_over = False
        
        # Initialize players
        self.players = [Player(i, f"Player {i}") for i in range(num_players)]
        
        # Create and shuffle deck
        self.deck = self._create_deck()
        self.discard_pile: List[Card] = []
        
        # Create track from tiles
        self.track = self._create_track_from_tiles(tile_config)
        
        # Deal initial hands (5 cards each)
        for player in self.players:
            player.hand = [self.deck.pop() for _ in range(5)]
        
        # Slipstream tracking
        self.exhaustion_tokens: Dict[Rider, int] = {
            rider: 0 for player in self.players for rider in player.riders
        }
    
    def _create_deck(self) -> List[Card]:
        """Create and shuffle the deck"""
        deck = []
        for card_type, configs in self.CARD_DISTRIBUTION.items():
            for flat, cobbles, climb, descent in configs:
                deck.append(Card(card_type, flat, cobbles, climb, descent))
        random.shuffle(deck)
        return deck
    
    def _create_track_from_tiles(self, tile_config: List[int]) -> List[TrackTile]:
        """Create the race track from tile configuration"""
        track = []
        position = 0
        
        for tile_id in tile_config:
            if tile_id not in RACE_TILES:
                raise ValueError(f"Invalid tile_id: {tile_id}. Must be 1-5.")
            
            race_tile = RACE_TILES[tile_id]
            
            # Add all 20 fields from this tile
            for field_idx, terrain in enumerate(race_tile.terrain_map):
                track.append(TrackTile(position, terrain))
                position += 1
        
        # Mark the last position as finish
        track[-1].terrain = TerrainType.FINISH
        track[-1].sprint_points = [15, 10, 7, 5, 3]  # Finish line points
        
        return track
    
    def get_current_player(self) -> Player:
        """Get the current player"""
        return self.players[self.current_player_idx]
    
    def get_tile_at_position(self, position: int) -> Optional[TrackTile]:
        """Get the track tile at a position"""
        if 0 <= position < len(self.track):
            return self.track[position]
        return None
    
    def get_riders_at_position(self, position: int) -> List[Rider]:
        """Get all riders at a specific position"""
        riders = []
        for player in self.players:
            for rider in player.riders:
                if rider.position == position:
                    riders.append(rider)
        return riders
    
    def get_rider_positions(self) -> Dict[Rider, int]:
        """Get positions of all riders"""
        positions = {}
        for player in self.players:
            for rider in player.riders:
                positions[rider] = rider.position
        return positions
    
    def draw_card(self) -> Optional[Card]:
        """Draw a card from the deck"""
        if not self.deck:
            # Reshuffle discard pile if deck is empty
            if self.discard_pile:
                self.deck = self.discard_pile[:]
                self.discard_pile = []
                random.shuffle(self.deck)
            else:
                return None
        return self.deck.pop() if self.deck else None
    
    def advance_turn(self):
        """Move to next player's turn"""
        self.current_player_idx = (self.current_player_idx + 1) % self.num_players
        if self.current_player_idx == 0:
            self.current_turn += 1
    
    def check_game_over(self) -> bool:
        """Check if game is over (any rider crossed finish line)"""
        for player in self.players:
            for rider in player.riders:
                if rider.position >= self.track_length - 1:
                    self.game_over = True
                    return True
        return False
    
    def get_game_summary(self) -> Dict:
        """Get current game state summary"""
        return {
            'turn': self.current_turn,
            'current_player': self.current_player_idx,
            'player_scores': [p.points for p in self.players],
            'player_hand_sizes': [len(p.hand) for p in self.players],
            'rider_positions': {
                f"P{r.player_id}R{r.rider_id}": r.position 
                for player in self.players for r in player.riders
            },
            'game_over': self.game_over
        }
