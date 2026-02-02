"""
Chasse Patate - Game Engine
Handles game logic, move validation, and rule enforcement
"""

from typing import List, Tuple, Optional, Set
from dataclasses import dataclass
from game_state import GameState, Player, Rider, Card, TerrainType, CardType


@dataclass
class Move:
    """Represents a player's move"""
    rider: Rider
    card: Card
    target_position: int
    uses_slipstream: bool = False


class GameEngine:
    """Handles game logic and rules"""
    
    def __init__(self, game_state: GameState):
        self.state = game_state
    
    def get_valid_moves(self, player: Player) -> List[Move]:
        """Get all valid moves for a player"""
        valid_moves = []
        
        for rider in player.riders:
            for card in player.hand:
                # Get possible moves with this card
                moves = self._get_moves_for_rider_card(rider, card)
                valid_moves.extend(moves)
        
        return valid_moves
    
    def _get_moves_for_rider_card(self, rider: Rider, card: Card) -> List[Move]:
        """Get all valid moves for a specific rider-card combination"""
        moves = []
        current_pos = rider.position
        current_tile = self.state.get_tile_at_position(current_pos)
        
        if not current_tile:
            return moves
        
        # Base movement for current terrain
        base_movement = card.get_movement(current_tile.terrain)
        
        # Try moves without slipstream
        for distance in range(1, base_movement + 1):
            target_pos = current_pos + distance
            if self._is_valid_position(target_pos):
                moves.append(Move(rider, card, target_pos, uses_slipstream=False))
        
        # Try moves with slipstream (if applicable)
        slipstream_moves = self._get_slipstream_moves(rider, card, current_pos, base_movement)
        moves.extend(slipstream_moves)
        
        return moves
    
    def _get_slipstream_moves(self, rider: Rider, card: Card, 
                              current_pos: int, base_movement: int) -> List[Move]:
        """Calculate possible slipstream moves"""
        moves = []
        
        # Check if there are riders ahead to slipstream
        riders_ahead = []
        for pos in range(current_pos + 1, current_pos + base_movement + 6):
            if pos >= self.state.track_length:
                break
            riders_at_pos = self.state.get_riders_at_position(pos)
            if riders_at_pos:
                riders_ahead.extend([(r, pos) for r in riders_at_pos if r != rider])
        
        if not riders_ahead:
            return moves
        
        # Can slipstream up to 5 spaces beyond base movement
        max_slipstream = base_movement + 5
        
        for distance in range(base_movement + 1, max_slipstream + 1):
            target_pos = current_pos + distance
            if not self._is_valid_position(target_pos):
                break
            
            # Check if we would be slipstreaming (passing riders)
            would_slipstream = any(pos < target_pos for _, pos in riders_ahead)
            
            if would_slipstream:
                moves.append(Move(rider, card, target_pos, uses_slipstream=True))
        
        return moves
    
    def _is_valid_position(self, position: int) -> bool:
        """Check if a position is valid on the track"""
        return 0 <= position < self.state.track_length
    
    def execute_move(self, move: Move) -> dict:
        """Execute a move and return results"""
        player = self.state.players[move.rider.player_id]
        
        # Validate move
        if move.card not in player.hand:
            return {'success': False, 'error': 'Card not in hand'}
        
        # Store old position
        old_position = move.rider.position
        
        # Move the rider
        move.rider.position = move.target_position
        
        # Add exhaustion token if slipstreaming
        if move.uses_slipstream:
            self.state.exhaustion_tokens[move.rider] += 1
        
        # Remove card from hand and discard
        player.hand.remove(move.card)
        self.state.discard_pile.append(move.card)
        
        # Check for sprint points
        points_earned = self._check_sprint_scoring(move.rider, move.target_position)
        if points_earned > 0:
            player.points += points_earned
        
        # Draw new card
        new_card = self.state.draw_card()
        if new_card:
            player.hand.append(new_card)
        
        return {
            'success': True,
            'rider': f"P{move.rider.player_id}R{move.rider.rider_id}",
            'old_position': old_position,
            'new_position': move.target_position,
            'card_played': move.card.card_type.value,
            'used_slipstream': move.uses_slipstream,
            'points_earned': points_earned,
            'exhaustion_tokens': self.state.exhaustion_tokens[move.rider]
        }
    
    def _check_sprint_scoring(self, rider: Rider, position: int) -> int:
        """Check if rider scores points at a sprint"""
        tile = self.state.get_tile_at_position(position)
        
        if not tile or tile.terrain not in [TerrainType.SPRINT, TerrainType.FINISH]:
            return 0
        
        if not tile.sprint_points:
            return 0
        
        # Get all riders at this position
        riders_here = self.state.get_riders_at_position(position)
        
        # Sort riders by arrival order (first to arrive gets best points)
        # For simplicity, we'll award based on player order in same turn
        # In real game, would need to track exact arrival timing
        
        # Find position in scoring
        scoring_position = len([r for p in self.state.players 
                               for r in p.riders 
                               if r.position == position and r != rider])
        
        if scoring_position < len(tile.sprint_points):
            return tile.sprint_points[scoring_position]
        
        return 0
    
    def process_end_of_race(self) -> dict:
        """Calculate final scores at end of race"""
        # Get all riders at finish
        finish_position = self.state.track_length - 1
        finish_tile = self.state.get_tile_at_position(finish_position)
        
        # Get riders sorted by position (highest first)
        all_riders = [(r, r.position) for p in self.state.players for r in p.riders]
        all_riders.sort(key=lambda x: x[1], reverse=True)
        
        # Award finish points
        finish_points = finish_tile.sprint_points if finish_tile else [15, 10, 7, 5, 3]
        
        for i, (rider, pos) in enumerate(all_riders):
            if pos >= finish_position and i < len(finish_points):
                player = self.state.players[rider.player_id]
                player.points += finish_points[i]
        
        # Get final standings
        standings = sorted(enumerate(self.state.players), 
                          key=lambda x: x[1].points, 
                          reverse=True)
        
        return {
            'final_scores': {f"Player {i}": p.points for i, p in standings},
            'winner': standings[0][1].name,
            'winner_score': standings[0][1].points
        }
    
    def get_game_state_for_agent(self, player_id: int) -> dict:
        """Get game state information for an agent"""
        player = self.state.players[player_id]
        
        return {
            'player_id': player_id,
            'hand': [{'type': c.card_type.value, 
                     'flat': c.movement_flat,
                     'hill': c.movement_hill, 
                     'mountain': c.movement_mountain} for c in player.hand],
            'my_riders': [{'rider_id': r.rider_id, 'position': r.position} 
                         for r in player.riders],
            'my_score': player.points,
            'opponent_riders': [{'player_id': r.player_id, 
                                'rider_id': r.rider_id, 
                                'position': r.position}
                               for p in self.state.players if p.player_id != player_id
                               for r in p.riders],
            'opponent_scores': [p.points for p in self.state.players if p.player_id != player_id],
            'track_length': self.state.track_length,
            'current_turn': self.state.current_turn,
            'deck_size': len(self.state.deck),
            'discard_size': len(self.state.discard_pile)
        }
