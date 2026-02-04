"""
Chasse Patate - AI Agents
Different AI strategies for testing game balance
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import random
from game_state import Player, Card, CardType, TerrainType, PlayMode, ActionType, Rider
from game_engine import GameEngine, Move


def calculate_move_distance(engine: GameEngine, move: Move) -> int:
    """Helper function to calculate how far a move will advance a rider"""
    if move.action_type == ActionType.PULL:
        return engine._calculate_pull_movement(move.rider, move.cards)
    elif move.action_type == ActionType.ATTACK:
        return engine._calculate_attack_movement(move.rider, move.cards)
    return 0


def calculate_total_advancement(engine: GameEngine, move: Move) -> int:
    """Calculate total advancement for all riders affected by a move
    
    For single rider moves (Pull, Attack, Draft): returns distance moved
    For team moves (TeamPull, TeamDraft): returns distance × number of riders
    For TeamCar: returns 0 (no advancement)
    """
    if move.action_type == ActionType.PULL:
        return engine._calculate_pull_movement(move.rider, move.cards)
    elif move.action_type == ActionType.ATTACK:
        return engine._calculate_attack_movement(move.rider, move.cards)
    elif move.action_type == ActionType.DRAFT:
        # Draft copies movement from last move
        if engine.state.last_move:
            return engine.state.last_move.get('movement', 0)
        return 0
    elif move.action_type == ActionType.TEAM_PULL:
        # TeamPull: lead rider + all drafting riders move same distance
        distance = engine._calculate_pull_movement(move.rider, move.cards)
        num_riders = 1 + len(move.drafting_riders)  # lead + drafters
        return distance * num_riders
    elif move.action_type == ActionType.TEAM_DRAFT:
        # TeamDraft: all riders move same distance
        if engine.state.last_move:
            distance = engine.state.last_move.get('movement', 0)
            num_riders = 1 + len(move.drafting_riders)  # primary + drafters
            return distance * num_riders
        return 0
    elif move.action_type == ActionType.TEAM_CAR:
        return 0  # No advancement
    
    return 0


def should_use_team_car(player: Player, valid_moves: List[Move], hand_threshold: int = 3) -> bool:
    """Helper function to determine if agent should use Team Car
    
    TeamCar is used only if:
    1. Hand size < threshold (default 3)
    2. No Draft or TeamDraft moves available
    """
    # Check hand size
    if len(player.hand) >= hand_threshold:
        return False
    
    # Check if Draft or TeamDraft moves are available
    has_draft = any(m.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT] for m in valid_moves)
    
    # Only use TeamCar if no draft moves available
    return not has_draft


def get_best_draft_move(valid_moves: List[Move]) -> Optional[Move]:
    """Get the best draft move, prioritizing TeamDraft over Draft
    
    Returns:
        TeamDraft if available, otherwise Draft, otherwise None
    """
    # Prefer TeamDraft (multiple riders move for free)
    team_drafts = [m for m in valid_moves if m.action_type == ActionType.TEAM_DRAFT]
    if team_drafts:
        # Choose TeamDraft with most riders
        return max(team_drafts, key=lambda m: 1 + len(m.drafting_riders))
    
    # Fall back to regular Draft
    drafts = [m for m in valid_moves if m.action_type == ActionType.DRAFT]
    if drafts:
        return drafts[0]
    
    return None


def choose_card_to_discard(player: Player) -> Optional[Card]:
    """Helper function to choose worst card to discard (Energy first)
    Note: This should be called BEFORE drawing in TeamCar, to pre-select the card type.
    After drawing, the actual card instance will be selected during execution."""
    if not player.hand:
        # If hand is empty, we'll discard an Energy after drawing
        # Return None for now, execution will handle it
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
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Choose a move given the current game state.

        Args:
            engine: The game engine
            player: The current player
            eligible_riders: Riders that can move this turn (unmoved this round).
                            If None, all riders are eligible (backward compat).
        """
        pass
    
    def __str__(self):
        return f"{self.name} (Player {self.player_id})"


class RandomAgent(Agent):
    """Agent that plays randomly - baseline for comparison"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Random")
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Choose a random valid move"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        return random.choice(valid_moves)


class GreedyAgent(Agent):
    """Agent that always plays for maximum total advancement across all riders"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Greedy")
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Choose action that maximizes total advancement (distance × number of riders)"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
        # If hand is low (< 3 cards), try Draft/TeamDraft first, then TeamCar
        if len(player.hand) < 3:
            # Check for draft moves
            draft_move = get_best_draft_move(valid_moves)
            if draft_move:
                return draft_move
            
            # No draft available, use TeamCar
            if should_use_team_car(player, valid_moves):
                team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
                if team_car_moves:
                    worst_card = choose_card_to_discard(player)
                    if worst_card:
                        team_car_moves[0].cards = [worst_card]
                    return team_car_moves[0]
        
        # Calculate total advancement for all moves and choose maximum
        # This considers both distance and number of riders moved
        non_team_car = [m for m in valid_moves if m.action_type != ActionType.TEAM_CAR]
        if non_team_car:
            return max(non_team_car, key=lambda m: calculate_total_advancement(engine, m))
        return valid_moves[0]


class LeadRiderAgent(Agent):
    """Agent that focuses on advancing the leading rider"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "LeadRider")
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Advance the leading rider, prioritizing drafts over TeamCar when low on cards"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
        # If hand is low (< 3 cards), try Draft/TeamDraft first, then TeamCar
        if len(player.hand) < 3:
            # Check for draft moves
            draft_move = get_best_draft_move(valid_moves)
            if draft_move:
                return draft_move
            
            # No draft available, use TeamCar
            if should_use_team_car(player, valid_moves):
                team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
                if team_car_moves:
                    worst_card = choose_card_to_discard(player)
                    if worst_card:
                        team_car_moves[0].cards = [worst_card]
                    return team_car_moves[0]
        
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
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Move the most behind rider, prioritizing drafts over TeamCar when low on cards"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
        # If hand is low (< 3 cards), try Draft/TeamDraft first, then TeamCar
        if len(player.hand) < 3:
            # Check for draft moves
            draft_move = get_best_draft_move(valid_moves)
            if draft_move:
                return draft_move
            
            # No draft available, use TeamCar
            if should_use_team_car(player, valid_moves):
                team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
                if team_car_moves:
                    worst_card = choose_card_to_discard(player)
                    if worst_card:
                        team_car_moves[0].cards = [worst_card]
                    return team_car_moves[0]
        
        # Find our most behind rider
        behind_rider = min(player.riders, key=lambda r: r.position)
        
        # Filter moves for behind rider (excluding TeamCar)
        behind_moves = [m for m in valid_moves if m.rider == behind_rider and m.action_type != ActionType.TEAM_CAR]
        if behind_moves:
            return max(behind_moves, key=lambda m: calculate_move_distance(engine, m))

        # If no moves for behind rider, take best move overall
        non_team_car = [m for m in valid_moves if m.action_type != ActionType.TEAM_CAR]
        if non_team_car:
            return max(non_team_car, key=lambda m: calculate_move_distance(engine, m))

        # Fallback to any available move
        return valid_moves[0]


class SprintHunterAgent(Agent):
    """Agent that prioritizes sprint points"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "SprintHunter")
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Prioritize reaching sprint points"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
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
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Choose conservative moves"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
        # Take best move (simplified for action system)
        return max(valid_moves, key=lambda m: calculate_move_distance(engine, m))


class AggressiveAgent(Agent):
    """Agent that plays aggressively for maximum advancement"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Aggressive")
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Prefer moves for maximum advancement"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
        # Take the best move for maximum distance
        return max(valid_moves, key=lambda m: calculate_move_distance(engine, m))


class CardTypeAgent(Agent):
    """Agent that prioritizes playing specific card types"""
    
    def __init__(self, player_id: int, preferred_type: CardType):
        super().__init__(player_id, f"{preferred_type.value}Focus")
        self.preferred_type = preferred_type
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Prefer playing cards of the preferred type"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
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
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Adapt strategy based on upcoming terrain, prioritizing drafts over TeamCar when low on cards"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
        # If hand is low (< 3 cards), try Draft/TeamDraft first, then TeamCar
        if len(player.hand) < 3:
            # Check for draft moves
            draft_move = get_best_draft_move(valid_moves)
            if draft_move:
                return draft_move
            
            # No draft available, use TeamCar
            if should_use_team_car(player, valid_moves):
                team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
                if team_car_moves:
                    worst_card = choose_card_to_discard(player)
                    if worst_card:
                        team_car_moves[0].cards = [worst_card]
                    return team_car_moves[0]
        
        # Filter out TeamCar for scoring
        non_team_car = [m for m in valid_moves if m.action_type != ActionType.TEAM_CAR]
        
        # Analyze terrain ahead for each move
        scored_moves = []
        for move in non_team_car:
            score = self._score_move(move, engine)
            scored_moves.append((move, score))
        
        # Return highest scored move
        if scored_moves:
            return max(scored_moves, key=lambda x: x[1])[0]
        return valid_moves[0]
    
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
        
        return score


class WheelsuckerAgent(Agent):
    """Agent that prioritizes drafting and positioning for future drafts"""
    
    def __init__(self, player_id: int):
        super().__init__(player_id, "Wheelsucker")
    
    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Prioritize drafting, then positioning for drafts, then TeamCar
        
        Only chooses draft/pull moves if total_advancement > 0
        """
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None
        
        # Priority 1: TeamDraft with biggest total advancement (only if > 0)
        team_draft_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_DRAFT]
        if team_draft_moves:
            best_team_draft = max(team_draft_moves, key=lambda m: calculate_total_advancement(engine, m))
            if calculate_total_advancement(engine, best_team_draft) > 0:
                return best_team_draft
        
        # Priority 2: Draft with biggest total advancement (only if > 0)
        draft_moves = [m for m in valid_moves if m.action_type == ActionType.DRAFT]
        if draft_moves:
            best_draft = max(draft_moves, key=lambda m: calculate_total_advancement(engine, m))
            if calculate_total_advancement(engine, best_draft) > 0:
                return best_draft
        
        # Priority 3: TeamPull with biggest total advancement (only if > 0)
        team_pull_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_PULL]
        if team_pull_moves:
            best_team_pull = max(team_pull_moves, key=lambda m: calculate_total_advancement(engine, m))
            if calculate_total_advancement(engine, best_team_pull) > 0:
                return best_team_pull
        
        # Priority 4: Attack if it can win points (land on or cross sprint)
        attack_moves = [m for m in valid_moves if m.action_type == ActionType.ATTACK]
        if attack_moves:
            for attack in attack_moves:
                distance = engine._calculate_attack_movement(attack.rider, attack.cards)
                old_pos = attack.rider.position
                new_pos = min(old_pos + distance, engine.state.track_length - 1)
                
                # Check if any position crossed is a sprint or finish
                for pos in range(old_pos + 1, new_pos + 1):
                    tile = engine.state.get_tile_at_position(pos)
                    if tile and tile.terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
                        # This attack can win points
                        return attack
        
        # Priority 5: Move to same field as opponent's rider (for future drafting)
        positioning_moves = self._get_positioning_moves(valid_moves, engine, player, same_team=False)
        if positioning_moves:
            # Choose the one with most riders at destination (best drafting opportunity)
            return max(positioning_moves, key=lambda m: self._count_riders_at_destination(m, engine, player))
        
        # Priority 6: Move to same field as own team rider (for TeamPull/TeamDraft)
        team_positioning_moves = self._get_positioning_moves(valid_moves, engine, player, same_team=True)
        if team_positioning_moves:
            return max(team_positioning_moves, key=lambda m: self._count_riders_at_destination(m, engine, player))
        
        # Priority 7: TeamCar
        team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
        if team_car_moves:
            worst_card = choose_card_to_discard(player)
            if worst_card:
                team_car_moves[0].cards = [worst_card]
            return team_car_moves[0]
        
        # Fallback: any move
        return valid_moves[0]
    
    def _get_positioning_moves(self, valid_moves: List[Move], engine: GameEngine, 
                               player: Player, same_team: bool) -> List[Move]:
        """Get moves that position rider with other riders"""
        positioning_moves = []
        
        for move in valid_moves:
            if move.action_type in [ActionType.TEAM_CAR]:
                continue
            
            # Calculate destination
            distance = calculate_move_distance(engine, move)
            if distance == 0:
                continue
            
            destination = min(move.rider.position + distance, engine.state.track_length - 1)
            
            # Check if there are riders at destination
            riders_at_dest = engine.state.get_riders_at_position(destination)
            
            if same_team:
                # Looking for own team riders
                has_own_riders = any(r.player_id == player.player_id and r != move.rider 
                                    for r in riders_at_dest)
                if has_own_riders:
                    positioning_moves.append(move)
            else:
                # Looking for opponent riders
                has_opponent_riders = any(r.player_id != player.player_id 
                                         for r in riders_at_dest)
                if has_opponent_riders:
                    positioning_moves.append(move)
        
        return positioning_moves
    
    def _count_riders_at_destination(self, move: Move, engine: GameEngine, player: Player) -> int:
        """Count how many riders (opponents or teammates) are at the destination"""
        distance = calculate_move_distance(engine, move)
        destination = min(move.rider.position + distance, engine.state.track_length - 1)
        riders_at_dest = engine.state.get_riders_at_position(destination)
        # Count riders excluding the moving rider
        return len([r for r in riders_at_dest if r != move.rider])


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
        'wheelsucker': WheelsuckerAgent,
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
        'wheelsucker',
        'rouleur_focus', 'sprinter_focus', 'climber_focus'
    ]