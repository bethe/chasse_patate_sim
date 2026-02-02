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
    """Types of terrain tiles"""
    FLAT = "Flat"
    HILL = "Hill"
    MOUNTAIN = "Mountain"
    SPRINT = "Sprint"
    FINISH = "Finish"


@dataclass
class Card:
    """Represents a rider card"""
    card_type: CardType
    movement_flat: int
    movement_hill: int
    movement_mountain: int
    
    def get_movement(self, terrain: TerrainType) -> int:
        """Get movement value for terrain"""
        if terrain in [TerrainType.FLAT, TerrainType.SPRINT]:
            return self.movement_flat
        elif terrain == TerrainType.HILL:
            return self.movement_hill
        elif terrain == TerrainType.MOUNTAIN:
            return self.movement_mountain
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
    CARD_DISTRIBUTION = {
        CardType.ROULEUR: [(7, 5, 3)] * 9,  # 9 cards: 7 flat, 5 hill, 3 mountain
        CardType.SPRINTEUR: [(9, 3, 3)] * 9,  # 9 cards: 9 flat, 3 hill, 3 mountain
        CardType.GRIMPEUR: [(5, 7, 9)] * 9,  # 9 cards: 5 flat, 7 hill, 9 mountain
    }
    
    def __init__(self, num_players: int, track_length: int = 50):
        assert 2 <= num_players <= 5, "Game supports 2-5 players"
        
        self.num_players = num_players
        self.track_length = track_length
        self.current_turn = 0
        self.current_player_idx = 0
        self.game_over = False
        
        # Initialize players
        self.players = [Player(i, f"Player {i}") for i in range(num_players)]
        
        # Create and shuffle deck
        self.deck = self._create_deck()
        self.discard_pile: List[Card] = []
        
        # Create track
        self.track = self._create_track()
        
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
            for flat, hill, mountain in configs:
                deck.append(Card(card_type, flat, hill, mountain))
        random.shuffle(deck)
        return deck
    
    def _create_track(self) -> List[TrackTile]:
        """Create the race track"""
        track = []
        
        # Example track configuration (can be customized)
        # First 20% flat, then mixed terrain with sprints
        positions_per_section = self.track_length // 5
        
        # Flat start
        for i in range(positions_per_section):
            track.append(TrackTile(i, TerrainType.FLAT))
        
        # First sprint
        track.append(TrackTile(positions_per_section, TerrainType.SPRINT))
        
        # Hills
        for i in range(positions_per_section + 1, 2 * positions_per_section):
            track.append(TrackTile(i, TerrainType.HILL))
        
        # Mountain section
        for i in range(2 * positions_per_section, 3 * positions_per_section):
            track.append(TrackTile(i, TerrainType.MOUNTAIN))
        
        # Second sprint
        track.append(TrackTile(3 * positions_per_section, TerrainType.SPRINT))
        
        # Final section with mixed terrain
        for i in range(3 * positions_per_section + 1, self.track_length - 1):
            terrain = random.choice([TerrainType.FLAT, TerrainType.HILL])
            track.append(TrackTile(i, terrain))
        
        # Finish line
        track.append(TrackTile(self.track_length - 1, TerrainType.FINISH, [15, 10, 7, 5, 3]))
        
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
