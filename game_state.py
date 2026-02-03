"""
Chasse Patate - Game State Management
Handles all game state, cards, and rules
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import random


class CardType(Enum):
    """Types of cards"""
    ENERGY = "Energy"
    ROULEUR = "Rouleur"
    SPRINTER = "Sprinter"
    CLIMBER = "Climber"


class PlayMode(Enum):
    """Card play modes"""
    PULL = "Pull"
    ATTACK = "Attack"


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
    """Represents a card that can be played"""
    card_type: CardType
    
    # Movement values for pull mode (None for Energy card)
    pull_flat: Optional[int] = None
    pull_cobbles: Optional[int] = None
    pull_climb: Optional[int] = None
    pull_descent: Optional[int] = None
    
    # Movement values for attack mode (None for Energy card)
    attack_flat: Optional[int] = None
    attack_cobbles: Optional[int] = None
    attack_climb: Optional[int] = None
    attack_descent: Optional[int] = None
    
    def is_energy_card(self) -> bool:
        """Check if this is an Energy card"""
        return self.card_type == CardType.ENERGY
    
    def can_play_on_rider(self, rider_type: CardType) -> bool:
        """Check if this card can be played on a specific rider type"""
        if self.is_energy_card():
            return True  # Energy can be played on any rider
        return self.card_type == rider_type  # Rider cards match rider type
    
    def get_movement(self, terrain: TerrainType, play_mode: PlayMode) -> int:
        """Get movement value for terrain and play mode"""
        # Energy card always returns 1
        if self.is_energy_card():
            return 1
        
        # Select the appropriate mode
        if play_mode == PlayMode.PULL:
            terrain_map = {
                TerrainType.FLAT: self.pull_flat,
                TerrainType.COBBLES: self.pull_cobbles,
                TerrainType.CLIMB: self.pull_climb,
                TerrainType.DESCENT: self.pull_descent,
            }
        else:  # PlayMode.ATTACK
            terrain_map = {
                TerrainType.FLAT: self.attack_flat,
                TerrainType.COBBLES: self.attack_cobbles,
                TerrainType.CLIMB: self.attack_climb,
                TerrainType.DESCENT: self.attack_descent,
            }
        
        # Handle special terrain types (Sprint/Finish use flat values)
        if terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
            terrain = TerrainType.FLAT
        
        movement = terrain_map.get(terrain, 0)
        return movement if movement is not None else 0


@dataclass
class Rider:
    """Represents a rider on the track"""
    player_id: int
    rider_id: int  # 0-2 for each player's three riders
    rider_type: CardType = CardType.ROULEUR  # Type of rider (set in __post_init__)
    position: int = 0  # Track position
    
    def __post_init__(self):
        # Assign rider types: 0=Rouleur, 1=Sprinter, 2=Climber
        rider_types = [CardType.ROULEUR, CardType.SPRINTER, CardType.CLIMBER]
        if hasattr(self, 'rider_type') and self.rider_type == CardType.ROULEUR:
            # Only set if not already set (default value)
            self.rider_type = rider_types[self.rider_id]
    
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
    # 18 of each rider card + 36 Energy cards = 90 total cards
    CARD_DISTRIBUTION = {
        # Energy cards: 36 total
        CardType.ENERGY: [
            Card(CardType.ENERGY)
            for _ in range(36)
        ],
        
        # Rouleur cards: 18 total
        CardType.ROULEUR: [
            Card(
                CardType.ROULEUR,
                pull_flat=2, pull_cobbles=1, pull_climb=1, pull_descent=3,
                attack_flat=2, attack_cobbles=1, attack_climb=1, attack_descent=3
            )
            for _ in range(18)
        ],
        
        # Sprinter cards: 18 total
        CardType.SPRINTER: [
            Card(
                CardType.SPRINTER,
                pull_flat=1, pull_cobbles=1, pull_climb=0, pull_descent=3,
                attack_flat=3, attack_cobbles=2, attack_climb=1, attack_descent=3
            )
            for _ in range(18)
        ],
        
        # Climber cards: 18 total
        CardType.CLIMBER: [
            Card(
                CardType.CLIMBER,
                pull_flat=0, pull_cobbles=0, pull_climb=2, pull_descent=3,
                attack_flat=1, attack_cobbles=0, attack_climb=3, attack_descent=3
            )
            for _ in range(18)
        ],
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
        
        # Deal initial hands according to rules
        self._deal_initial_hands()
        
        # Slipstream tracking
        self.exhaustion_tokens: Dict[Rider, int] = {
            rider: 0 for player in self.players for rider in player.riders
        }
    
    def _deal_initial_hands(self):
        """Deal initial hands according to game rules:
        - 3 Energy cards
        - 1 Rouleur, 1 Sprinter, 1 Climber card
        - 3 random cards from remaining deck
        Total: 9 cards per player"""
        
        # First, separate the deck by card type for easier dealing
        energy_cards = [c for c in self.deck if c.card_type == CardType.ENERGY]
        rouleur_cards = [c for c in self.deck if c.card_type == CardType.ROULEUR]
        sprinter_cards = [c for c in self.deck if c.card_type == CardType.SPRINTER]
        climber_cards = [c for c in self.deck if c.card_type == CardType.CLIMBER]
        
        # Clear deck, we'll rebuild it after dealing
        self.deck = []
        
        for player in self.players:
            hand = []
            
            # Deal 3 Energy cards
            for _ in range(3):
                if energy_cards:
                    hand.append(energy_cards.pop(0))
            
            # Deal exactly 1 of each rider card type
            if rouleur_cards:
                hand.append(rouleur_cards.pop(0))
            if sprinter_cards:
                hand.append(sprinter_cards.pop(0))
            if climber_cards:
                hand.append(climber_cards.pop(0))
            
            player.hand = hand
        
        # Rebuild deck with remaining cards
        self.deck = energy_cards + rouleur_cards + sprinter_cards + climber_cards
        random.shuffle(self.deck)
        
        # Now deal 3 random cards to each player from the shuffled remaining deck
        for player in self.players:
            for _ in range(3):
                if self.deck:
                    player.hand.append(self.deck.pop(0))
    
    def _create_deck(self) -> List[Card]:
        """Create and shuffle the deck"""
        deck = []
        for card_type, cards in self.CARD_DISTRIBUTION.items():
            deck.extend(cards)
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
            'player_hands_detailed': [self._get_hand_breakdown(p) for p in self.players],
            'rider_positions': {
                f"P{r.player_id}R{r.rider_id}": r.position 
                for player in self.players for r in player.riders
            },
            'game_over': self.game_over,
            'deck_size': len(self.deck),
            'discard_size': len(self.discard_pile)
        }
    
    def _get_hand_breakdown(self, player: Player) -> Dict:
        """Get detailed breakdown of a player's hand"""
        breakdown = {
            'energy': 0,
            'rouleur': 0,
            'sprinter': 0,
            'climber': 0,
            'total': len(player.hand)
        }
        
        for card in player.hand:
            if card.card_type == CardType.ENERGY:
                breakdown['energy'] += 1
            elif card.card_type == CardType.ROULEUR:
                breakdown['rouleur'] += 1
            elif card.card_type == CardType.SPRINTER:
                breakdown['sprinter'] += 1
            elif card.card_type == CardType.CLIMBER:
                breakdown['climber'] += 1
        
        return breakdown
