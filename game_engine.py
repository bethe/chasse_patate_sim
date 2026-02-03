"""
Chasse Patate - Game Engine
Handles game logic, move validation, and rule enforcement
"""

from typing import List, Tuple, Optional, Set
from dataclasses import dataclass
from game_state import GameState, Player, Rider, Card, TerrainType, CardType, PlayMode, ActionType


@dataclass
class Move:
    """Represents a player's action (Pull, Attack, Draft, or TeamCar)"""
    action_type: ActionType
    rider: Rider
    cards: List[Card]  # 1-3 cards for Pull/Attack, 1 card for TeamCar (card to discard), empty for Draft
    
    def __post_init__(self):
        """Validate the move"""
        if self.action_type == ActionType.PULL:
            assert 1 <= len(self.cards) <= 3, "Pull requires 1-3 cards"
        elif self.action_type == ActionType.ATTACK:
            assert len(self.cards) == 3, "Attack requires exactly 3 cards"
        elif self.action_type == ActionType.TEAM_CAR:
            assert len(self.cards) <= 1, "Team Car can specify 0 or 1 card to discard"


class GameEngine:
    """Handles game logic and rules"""
    
    def __init__(self, game_state: GameState):
        self.state = game_state
    
    def get_valid_moves(self, player: Player) -> List[Move]:
        """Get all valid actions (Pull, Attack, Draft, TeamCar) for a player"""
        valid_moves = []
        
        # Generate moves for each rider
        for rider in player.riders:
            # PULL actions (1-3 cards)
            pull_moves = self._get_pull_moves(rider, player)
            valid_moves.extend(pull_moves)
            
            # ATTACK actions (exactly 3 cards, must include at least 1 matching rider card)
            attack_moves = self._get_attack_moves(rider, player)
            valid_moves.extend(attack_moves)
            
            # DRAFT actions (follow another rider's Pull move)
            draft_moves = self._get_draft_moves(rider, player)
            valid_moves.extend(draft_moves)
        
        # TEAM CAR action (available once per turn, not per rider)
        # Player draws 2 cards, then discards 1 card of their choice
        # Can be used even with 0 cards (discard happens after drawing)
        valid_moves.append(Move(ActionType.TEAM_CAR, player.riders[0], []))
        
        return valid_moves
    
    def _get_pull_moves(self, rider: Rider, player: Player) -> List[Move]:
        """Generate all valid Pull moves for a rider (1-3 cards)"""
        moves = []
        
        # Get eligible cards: matching rider cards + energy cards
        eligible_cards = [c for c in player.hand 
                         if c.is_energy_card() or c.card_type == rider.rider_type]
        
        if not eligible_cards:
            return moves
        
        # Generate combinations: 1 card, 2 cards, or 3 cards
        from itertools import combinations
        
        for num_cards in [1, 2, 3]:
            if len(eligible_cards) >= num_cards:
                for card_combo in combinations(range(len(eligible_cards)), num_cards):
                    cards = [eligible_cards[i] for i in card_combo]
                    moves.append(Move(ActionType.PULL, rider, cards))
        
        return moves
    
    def _get_attack_moves(self, rider: Rider, player: Player) -> List[Move]:
        """Generate all valid Attack moves for a rider (exactly 3 cards, at least 1 matching rider card)"""
        moves = []
        
        # Need at least 3 cards in hand
        if len(player.hand) < 3:
            return moves
        
        # Get eligible cards
        matching_rider_cards = [c for c in player.hand if c.card_type == rider.rider_type]
        energy_cards = [c for c in player.hand if c.is_energy_card()]
        
        # Must have at least 1 matching rider card
        if not matching_rider_cards:
            return moves
        
        # Generate all 3-card combinations from hand
        from itertools import combinations
        
        for card_combo in combinations(player.hand, 3):
            cards = list(card_combo)
            # Check if at least one card matches the rider type
            has_matching_card = any(c.card_type == rider.rider_type for c in cards)
            # Check if all cards are eligible (matching rider card or energy)
            all_eligible = all(c.is_energy_card() or c.card_type == rider.rider_type for c in cards)
            
            if has_matching_card and all_eligible:
                moves.append(Move(ActionType.ATTACK, rider, cards))
        
        return moves
    
    def _get_draft_moves(self, rider: Rider, player: Player) -> List[Move]:
        """Generate draft moves for a rider
        
        A rider can draft if:
        1. The last move was a PULL action
        2. The last move was by a different player
        3. The rider's current position matches the old_position of the last Pull move
        """
        moves = []
        
        # Check if there was a previous move
        if not self.state.last_move:
            return moves
        
        # Check if last move was a Pull action
        if self.state.last_move.get('action') != 'Pull':
            return moves
        
        # Check if last move was by a different player
        last_rider_str = self.state.last_move.get('rider', '')  # e.g., "P0R1"
        if last_rider_str.startswith(f'P{player.player_id}'):
            return moves  # Can't draft from your own rider
        
        # Check if rider's current position matches the starting position of the last Pull
        last_old_position = self.state.last_move.get('old_position', -1)
        if rider.position != last_old_position:
            return moves
        
        # Rider is eligible to draft!
        # Store the movement distance in a special way (we'll retrieve it in execute_move)
        moves.append(Move(ActionType.DRAFT, rider, []))
        
        return moves
    
    def _is_valid_position(self, position: int) -> bool:
        """Check if a position is valid on the track"""
        return 0 <= position < self.state.track_length
    
    def execute_move(self, move: Move) -> dict:
        """Execute a move and return results"""
        player = self.state.players[move.rider.player_id]
        
        # Validate cards are in hand
        for card in move.cards:
            if card not in player.hand:
                return {'success': False, 'error': f'Card {card.card_type.value} not in hand'}
        
        # Store old position and terrain
        old_position = move.rider.position
        old_tile = self.state.get_tile_at_position(old_position)
        old_terrain = old_tile.terrain.value if old_tile else "Unknown"
        
        # Calculate movement based on action type
        if move.action_type == ActionType.PULL:
            total_movement = self._calculate_pull_movement(move.rider, move.cards)
            action_name = "Pull"
        elif move.action_type == ActionType.ATTACK:
            total_movement = self._calculate_attack_movement(move.rider, move.cards)
            action_name = "Attack"
        elif move.action_type == ActionType.DRAFT:
            # Draft: copy the movement from the last Pull move
            if not self.state.last_move or self.state.last_move.get('action') != 'Pull':
                return {'success': False, 'error': 'Cannot draft - no valid Pull move to follow'}
            total_movement = self.state.last_move.get('movement', 0)
            action_name = "Draft"
        elif move.action_type == ActionType.TEAM_CAR:
            # Team Car: Draw 2 cards, discard 1 card
            result = self._execute_team_car(move, player, old_position, old_terrain)
            # Update last_move tracking
            self.state.last_move = result
            return result
        else:
            return {'success': False, 'error': f'Unknown action type: {move.action_type}'}
        
        # Move the rider
        new_position = min(old_position + total_movement, self.state.track_length - 1)
        move.rider.position = new_position
        
        # Get new terrain
        new_tile = self.state.get_tile_at_position(new_position)
        new_terrain = new_tile.terrain.value if new_tile else "Unknown"
        
        # Remove cards from hand and discard
        for card in move.cards:
            player.hand.remove(card)
            self.state.discard_pile.append(card)
        
        # Check for sprint points on ALL positions crossed (not just the final position)
        points_earned = 0
        for pos in range(old_position + 1, new_position + 1):
            points = self._check_sprint_scoring(move.rider, pos)
            points_earned += points
        
        if points_earned > 0:
            player.points += points_earned
        
        # Check if rider reached new checkpoint(s) (every 10 fields)
        cards_drawn = 0
        checkpoints_reached = []
        
        # Check all checkpoints from old position to new position
        for checkpoint in range(10, new_position + 1, 10):
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
        
        result = {
            'success': True,
            'action': action_name,
            'rider': f"P{move.rider.player_id}R{move.rider.rider_id}",
            'rider_type': move.rider.rider_type.value,
            'old_position': old_position,
            'old_terrain': old_terrain,
            'new_position': new_position,
            'new_terrain': new_terrain,
            'cards_played': [c.card_type.value for c in move.cards],
            'num_cards': len(move.cards),
            'movement': total_movement,
            'points_earned': points_earned,
            'checkpoints_reached': checkpoints_reached if checkpoints_reached else None,
            'cards_drawn': cards_drawn
        }
        
        # Store this move for potential drafting
        self.state.last_move = result
        
        return result
    
    def _calculate_pull_movement(self, rider: Rider, cards: List[Card]) -> int:
        """Calculate total movement for a Pull action"""
        current_tile = self.state.get_tile_at_position(rider.position)
        if not current_tile:
            return 0
        
        total = 0
        for card in cards:
            if card.is_energy_card():
                total += 1
            else:
                # Use Pull values
                total += card.get_movement(current_tile.terrain, PlayMode.PULL)
        
        return total
    
    def _calculate_attack_movement(self, rider: Rider, cards: List[Card]) -> int:
        """Calculate total movement for an Attack action"""
        current_tile = self.state.get_tile_at_position(rider.position)
        if not current_tile:
            return 0
        
        total = 0
        for card in cards:
            if card.is_energy_card():
                total += 1
            else:
                # Use Attack values
                total += card.get_movement(current_tile.terrain, PlayMode.ATTACK)
        
        return total
    
    def _execute_team_car(self, move: Move, player: Player, old_position: int, old_terrain: str) -> dict:
        """Execute Team Car action: Draw 2 cards first, then discard 1 card"""
        hand_size_before = len(player.hand)
        
        # Draw 2 cards FIRST
        cards_drawn = []
        for _ in range(2):
            new_card = self.state.draw_card()
            if new_card:
                player.hand.append(new_card)
                cards_drawn.append(new_card.card_type.value)
        
        # Now choose which card to discard from the UPDATED hand
        # Priority: Discard Energy cards first, then others
        card_to_discard = None
        
        # If agent specified a card type to discard via move.cards
        if move.cards and len(move.cards) > 0:
            # Agent pre-selected a card type - find a matching card in current hand
            target_card_type = move.cards[0].card_type
            matching_cards = [c for c in player.hand if c.card_type == target_card_type]
            if matching_cards:
                card_to_discard = matching_cards[0]
        
        # If no card specified or not found, use default strategy
        if not card_to_discard and player.hand:
            # Prefer Energy cards
            energy_cards = [c for c in player.hand if c.is_energy_card()]
            if energy_cards:
                card_to_discard = energy_cards[0]
            else:
                card_to_discard = player.hand[0]
        
        card_discarded = None
        if card_to_discard:
            player.hand.remove(card_to_discard)
            self.state.discard_pile.append(card_to_discard)
            card_discarded = card_to_discard.card_type.value
        
        hand_size_after = len(player.hand)
        
        # Rider doesn't move
        new_position = old_position
        new_terrain = old_terrain
        
        return {
            'success': True,
            'action': 'TeamCar',
            'rider': f"P{move.rider.player_id}R{move.rider.rider_id}",
            'rider_type': move.rider.rider_type.value,
            'old_position': old_position,
            'old_terrain': old_terrain,
            'new_position': new_position,
            'new_terrain': new_terrain,
            'cards_played': [],
            'cards_drawn': cards_drawn,
            'card_discarded': card_discarded,
            'hand_size_before': hand_size_before,
            'hand_size_after': hand_size_after,
            'num_cards': 0,
            'movement': 0,
            'points_earned': 0,
            'checkpoints_reached': None
        }
    
    def _check_sprint_scoring(self, rider: Rider, position: int) -> int:
        """Check if rider scores points at a sprint
        
        Riders score points based on arrival order:
        - Intermediate sprints (last field of each tile): Top 3 get [3, 2, 1]
        - Final sprint (finish line): Top 5 get [12, 8, 5, 3, 1]
        """
        tile = self.state.get_tile_at_position(position)
        
        if not tile or tile.terrain not in [TerrainType.SPRINT, TerrainType.FINISH]:
            return 0
        
        if not tile.sprint_points:
            return 0
        
        # Track arrival order at this sprint
        if position not in self.state.sprint_arrivals:
            self.state.sprint_arrivals[position] = []
        
        # Check if this rider has already been recorded at this sprint
        if rider in self.state.sprint_arrivals[position]:
            return 0  # Already scored here
        
        # Record this rider's arrival
        self.state.sprint_arrivals[position].append(rider)
        
        # Determine scoring position (0-indexed)
        scoring_position = len(self.state.sprint_arrivals[position]) - 1
        
        # Award points if within scoring positions
        if scoring_position < len(tile.sprint_points):
            return tile.sprint_points[scoring_position]
        
        return 0
    
    def process_end_of_race(self) -> dict:
        """Calculate final standings - points already awarded during play"""
        # All points have already been awarded during gameplay when riders
        # crossed sprint lines. Just calculate final standings.
        
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