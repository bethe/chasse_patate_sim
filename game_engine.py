"""
Chasse Patate - Game Engine
Handles game logic, move validation, and rule enforcement
"""

from typing import List, Tuple, Optional, Set
from dataclasses import dataclass
from game_state import GameState, Player, Rider, Card, TerrainType, CardType, PlayMode


@dataclass
class Move:
    """Represents a player's move"""
    rider: Rider
    card: Card
    target_position: int
    play_mode: PlayMode  # Pull or Attack


class GameEngine:
    """Handles game logic and rules"""
    
    def __init__(self, game_state: GameState):
        self.state = game_state
    
    def get_valid_moves(self, player: Player) -> List[Move]:
        """Get all valid moves for a player"""
        valid_moves = []
        
        for rider in player.riders:
            for card in player.hand:
                # Check if card can be played on this rider
                if not card.can_play_on_rider(rider.rider_type):
                    continue
                
                # Get possible moves with this card
                # Try both Pull and Attack modes (except for Energy which is always the same)
                if card.is_energy_card():
                    moves = self._get_moves_for_rider_card(rider, card, PlayMode.PULL)
                    valid_moves.extend(moves)
                else:
                    # Try Pull mode
                    moves_pull = self._get_moves_for_rider_card(rider, card, PlayMode.PULL)
                    valid_moves.extend(moves_pull)
                    
                    # Try Attack mode
                    moves_attack = self._get_moves_for_rider_card(rider, card, PlayMode.ATTACK)
                    valid_moves.extend(moves_attack)
        
        return valid_moves
    
    def _get_moves_for_rider_card(self, rider: Rider, card: Card, play_mode: PlayMode) -> List[Move]:
        """Get all valid moves for a specific rider-card combination"""
        moves = []
        current_pos = rider.position
        current_tile = self.state.get_tile_at_position(current_pos)
        
        if not current_tile:
            return moves
        
        # Base movement for current terrain
        base_movement = card.get_movement(current_tile.terrain, play_mode)
        
        # Generate all possible moves from 1 to base_movement
        for distance in range(1, base_movement + 1):
            target_pos = current_pos + distance
            if self._is_valid_position(target_pos):
                moves.append(Move(rider, card, target_pos, play_mode))
        
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
        
        # Validate card can be played on this rider
        if not move.card.can_play_on_rider(move.rider.rider_type):
            return {'success': False, 'error': 'Card cannot be played on this rider type'}
        
        # Store old position
        old_position = move.rider.position
        
        # Move the rider
        move.rider.position = move.target_position
        
        # Remove card from hand and discard
        player.hand.remove(move.card)
        self.state.discard_pile.append(move.card)
        
        # Check for sprint points
        points_earned = self._check_sprint_scoring(move.rider, move.target_position)
        if points_earned > 0:
            player.points += points_earned
        
        # Check if rider reached new checkpoint(s) (every 10 fields)
        cards_drawn = 0
        checkpoints_reached = []
        
        # Check all checkpoints from old position to new position
        for checkpoint in range(10, move.target_position + 1, 10):
            if checkpoint > old_position and not self.state.has_rider_reached_checkpoint(move.rider, checkpoint):
                # This is a new checkpoint for this rider
                self.state.mark_checkpoint_reached(move.rider, checkpoint)
                checkpoints_reached.append(checkpoint)
                
                # Draw 3 cards for this checkpoint
                for _ in range(3):
                    new_card = self.state.draw_card()
                    if new_card:
                        player.hand.append(new_card)
                        cards_drawn += 1
        
        return {
            'success': True,
            'rider': f"P{move.rider.player_id}R{move.rider.rider_id}",
            'rider_type': move.rider.rider_type.value,
            'old_position': old_position,
            'new_position': move.target_position,
            'card_played': move.card.card_type.value,
            'play_mode': move.play_mode.value,
            'points_earned': points_earned,
            'checkpoints_reached': checkpoints_reached if checkpoints_reached else None,
            'cards_drawn': cards_drawn
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
        
        def card_to_dict(c: Card) -> dict:
            if c.is_energy_card():
                return {'type': 'Energy', 'movement': 1}
            return {
                'type': c.card_type.value,
                'pull': {
                    'flat': c.pull_flat, 'cobbles': c.pull_cobbles,
                    'climb': c.pull_climb, 'descent': c.pull_descent
                },
                'attack': {
                    'flat': c.attack_flat, 'cobbles': c.attack_cobbles,
                    'climb': c.attack_climb, 'descent': c.attack_descent
                }
            }
        
        return {
            'player_id': player_id,
            'hand': [card_to_dict(c) for c in player.hand],
            'my_riders': [{'rider_id': r.rider_id, 
                          'rider_type': r.rider_type.value,
                          'position': r.position} 
                         for r in player.riders],
            'my_score': player.points,
            'opponent_riders': [{'player_id': r.player_id, 
                                'rider_id': r.rider_id,
                                'rider_type': r.rider_type.value,
                                'position': r.position}
                               for p in self.state.players if p.player_id != player_id
                               for r in p.riders],
            'opponent_scores': [p.points for p in self.state.players if p.player_id != player_id],
            'track_length': self.state.track_length,
            'current_turn': self.state.current_turn,
            'deck_size': len(self.state.deck),
            'discard_size': len(self.state.discard_pile)
        }
