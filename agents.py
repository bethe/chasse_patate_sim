"""
Chasse Patate - AI Agents
Different AI strategies for testing game balance
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import random
from game_state import Player, Card, CardType, TerrainType, PlayMode, ActionType
from game_engine import GameEngine, Move


def calculate_move_distance(engine: GameEngine, move: Move) -> int:
    """Helper function to calculate how far a move will advance a rider"""
    if move.action_type == ActionType.PULL:
        return engine._calculate_pull_movement(move.rider, move.cards)
    elif move.action_type == ActionType.ATTACK:
        return engine._calculate_attack_movement(move.rider, move.cards)
    return 0


def should_use_team_car(player: Player, hand_threshold: int = 3) -> bool:
    """Helper function to determine if agent should use Team Car"""
    return len(player.hand) < hand_threshold


def choose_card_to_discard(player: Player) -> Optional[Card]:
    """Helper function to choose worst card to discard (Energy first)"""
    if not player.hand:
        return None
    # Prefer discarding Energy cards
    energy_cards = [c for c in player.hand if c.is_energy_card()]
    if energy_cards:
        return energy_cards[0]
    # Otherwise discard first card
    return player.hand[0]


class Agent(ABC):
    """Base class for AI agents"""
    
    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name
    
    @abstractmethod
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Choose a move given the current game state"""
        pass
    
    def _try_use_team_car(self, valid_moves: List[Move], player: Player) -> Optional[Move]:
        """Helper to check and return a Team Car move if appropriate"""
        if should_use_team_car(player):
            team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
            if team_car_moves:
                worst_card = choose_card_to_discard(player)
                if worst_card:
                    team_car_moves[0].cards = [worst_card]
                return team_car_moves[0]
        return None
    
    def __str__(self):
        return f"{self.name} (Player {self.player_id})"


class RandomAgent(Agent):
    """Agent that plays randomly - baseline for comparison"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Random")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Choose a random valid move"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
        return random.choice(valid_moves)


class GreedyAgent(Agent):
    """Agent that always plays for maximum immediate advancement"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Greedy")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Choose action that advances furthest, or Team Car if low on cards"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
        
        # If hand is low (< 3 cards), prefer Team Car
        team_car_move = self._try_use_team_car(valid_moves, player)
        if team_car_move:
            return team_car_move
        
        # Otherwise return move with maximum distance
        non_team_car = [m for m in valid_moves if m.action_type != ActionType.TEAM_CAR]
        if non_team_car:
            return max(non_team_car, key=lambda m: calculate_move_distance(engine, m))
        return valid_moves[0]


class LeadRiderAgent(Agent):
    """Agent that focuses on advancing the leading rider"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "LeadRider")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Advance the leading rider, use Team Car if low on cards"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
        
        # If hand is low, use Team Car
        team_car_move = self._try_use_team_car(valid_moves, player)
        if team_car_move:
            return team_car_move
        
        # Find our leading rider
        lead_rider = max(player.riders, key=lambda r: r.position)
        
        # Filter moves for lead rider
        lead_moves = [m for m in valid_moves if m.rider == lead_rider and m.action_type != ActionType.TEAM_CAR]
        if not lead_moves:
            # If no moves for lead rider, pick best overall
            non_team_car = [m for m in valid_moves if m.action_type != ActionType.TEAM_CAR]
            if non_team_car:
                return max(non_team_car, key=lambda m: calculate_move_distance(engine, m))
        
        # Pick move that advances lead rider most
        return max(lead_moves, key=lambda m: calculate_move_distance(engine, m))


class BalancedAgent(Agent):
    """Agent that tries to keep all three riders advancing together"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Balanced")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Move the most behind rider"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
            
        # Check for Team Car usage
        team_car_move = self._try_use_team_car(valid_moves, player)
        if team_car_move:
            return team_car_move
        
        # Find our most behind rider
        behind_rider = min(player.riders, key=lambda r: r.position)
        
        # Filter moves for behind rider
        behind_moves = [m for m in valid_moves if m.rider == behind_rider]
        if not behind_moves:
            # If no moves available, take best move overall
            return max(valid_moves, key=lambda m: calculate_move_distance(engine, m))
        
        # Pick move that advances behind rider most
        return max(behind_moves, key=lambda m: calculate_move_distance(engine, m))


class SprintHunterAgent(Agent):
    """Agent that prioritizes sprint points"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "SprintHunter")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Prioritize reaching sprint points"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
            
        # Check for Team Car usage
        team_car_move = self._try_use_team_car(valid_moves, player)
        if team_car_move:
            return team_car_move
        
        # Find moves that land on sprint tiles
        sprint_moves = []
        for move in valid_moves:
            distance = calculate_move_distance(engine, move)
            target_pos = move.rider.position + distance
            tile = engine.state.get_tile_at_position(target_pos)
            if tile and tile.terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
                sprint_moves.append(move)
        
        # If we can reach a sprint, prioritize those moves
        if sprint_moves:
            # Choose the sprint move that gets us furthest
            return max(sprint_moves, key=lambda m: calculate_move_distance(engine, m))
        
        # Otherwise, advance furthest
        return max(valid_moves, key=lambda m: calculate_move_distance(engine, m))


class ConservativeAgent(Agent):
    """Agent that plays conservatively"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Conservative")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Choose conservative moves"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
            
        # Check for Team Car usage
        team_car_move = self._try_use_team_car(valid_moves, player)
        if team_car_move:
            return team_car_move
        
        # Take best move (simplified for action system)
        return max(valid_moves, key=lambda m: calculate_move_distance(engine, m))


class AggressiveAgent(Agent):
    """Agent that plays aggressively for maximum advancement"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Aggressive")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Prefer moves for maximum advancement"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
            
        # Check for Team Car usage
        team_car_move = self._try_use_team_car(valid_moves, player)
        if team_car_move:
            return team_car_move
        
        # Take the best move for maximum distance
        return max(valid_moves, key=lambda m: calculate_move_distance(engine, m))


class CardTypeAgent(Agent):
    """Agent that prioritizes playing specific card types"""
    
    def __init__(self, player_id: int, preferred_type: CardType):
        super().__init__(player_id, f"{preferred_type.value}Focus")
        self.preferred_type = preferred_type
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Prefer playing cards of the preferred type"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
            
        # Check for Team Car usage
        team_car_move = self._try_use_team_car(valid_moves, player)
        if team_car_move:
            return team_car_move
        
        # Filter for moves that use preferred card type
        preferred_moves = [m for m in valid_moves 
                          if any(c.card_type == self.preferred_type for c in m.cards)]
        
        if preferred_moves:
            # Play preferred card type, maximizing distance
            return max(preferred_moves, key=lambda m: calculate_move_distance(engine, m))
        else:
            # Play any card for maximum distance
            return max(valid_moves, key=lambda m: calculate_move_distance(engine, m))


class AdaptiveAgent(Agent):
    """Agent that adapts strategy based on terrain ahead"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Adaptive")
    
    def choose_move(self, engine: GameEngine, player: Player) -> Optional[Move]:
        """Adapt strategy based on upcoming terrain"""
        valid_moves = engine.get_valid_moves(player)
        if not valid_moves:
            return None
            
        # Check for Team Car usage
        team_car_move = self._try_use_team_car(valid_moves, player)
        if team_car_move:
            return team_car_move
        
        # Analyze terrain ahead for each rider
        scored_moves = []
        for move in valid_moves:
            score = self._score_move(move, engine)
            scored_moves.append((move, score))
        
        # Return highest scored move
        return max(scored_moves, key=lambda x: x[1])[0]
    
    def _score_move(self, move: Move, engine: GameEngine) -> float:
        """Score a move based on multiple factors"""
        score = 0.0
        
        # Base score: distance gained
        distance_gained = calculate_move_distance(engine, move)
        score += distance_gained * 10
        
        # Calculate target position
        target_pos = move.rider.position + distance_gained
        
        # Check terrain at destination
        tile = engine.state.get_tile_at_position(target_pos)
        if tile:
            # Bonus for landing on sprint or finish
            if tile.terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
                score += 50
            
            # Check upcoming terrain (next 5 tiles)
            climb_count = 0
            for offset in range(1, 6):
                next_tile = engine.state.get_tile_at_position(target_pos + offset)
                if next_tile and next_tile.terrain == TerrainType.CLIMB:
                    climb_count += 1
            
            # If climbs ahead and we used climber cards, bonus
            if climb_count >= 2 and any(c.card_type == CardType.CLIMBER for c in move.cards):
                score += 20
            
            # If flat ahead and we used sprinter cards, bonus
            if climb_count == 0 and any(c.card_type == CardType.SPRINTER for c in move.cards):
                score += 20
        
        return score


# Factory function to create agents
def create_agent(agent_type: str, player_id: int) -> Agent:
    """Create an agent of the specified type"""
    agent_map = {
        'random': RandomAgent,
        'greedy': GreedyAgent,
        'lead_rider': LeadRiderAgent,
        'balanced': BalancedAgent,
        'sprint_hunter': SprintHunterAgent,
        'conservative': ConservativeAgent,
        'aggressive': AggressiveAgent,
        'adaptive': AdaptiveAgent,
        'rouleur_focus': lambda pid: CardTypeAgent(pid, CardType.ROULEUR),
        'sprinter_focus': lambda pid: CardTypeAgent(pid, CardType.SPRINTER),
        'climber_focus': lambda pid: CardTypeAgent(pid, CardType.CLIMBER),
    }
    
    if agent_type not in agent_map:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    return agent_map[agent_type](player_id)


def get_available_agents() -> List[str]:
    """Get list of all available agent types"""
    return [
        'random', 'greedy', 'lead_rider', 'balanced', 
        'sprint_hunter', 'conservative', 'aggressive', 'adaptive',
        'rouleur_focus', 'sprinter_focus', 'climber_focus'
    ]