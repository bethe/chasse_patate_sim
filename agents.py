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
    elif move.action_type == ActionType.TEAM_PULL:
        return engine._calculate_pull_movement(move.rider, move.cards)
    elif move.action_type == ActionType.DRAFT:
        if engine.state.last_move:
            return engine.state.last_move.get('movement', 0)
        return 0
    elif move.action_type == ActionType.TEAM_DRAFT:
        if engine.state.last_move:
            return engine.state.last_move.get('movement', 0)
        return 0
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


def filter_wasteful_moves(moves: List[Move], engine: GameEngine) -> List[Move]:
    """Filter out moves that cost cards but have 0 advancement

    Returns moves that either:
    - Have advancement > 0, OR
    - Are free (Draft, TeamDraft, TeamCar)

    If all paid moves have 0 advancement, returns only free moves.
    If no moves pass the filter, returns original list as last resort.

    Args:
        moves: List of moves to filter
        engine: Game engine for calculating advancement

    Returns:
        Filtered list of moves (preferring productive > free > wasteful)
    """
    productive_moves = []  # Moves with advancement > 0
    free_moves = []  # Draft, TeamDraft, TeamCar
    wasteful_moves = []  # Moves costing cards with 0 advancement

    for move in moves:
        # Categorize each move
        if move.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT, ActionType.TEAM_CAR]:
            free_moves.append(move)
        elif len(move.cards) > 0:
            advancement = calculate_total_advancement(engine, move)
            if advancement > 0:
                productive_moves.append(move)
            else:
                wasteful_moves.append(move)
        else:
            # Shouldn't happen, but treat as free
            free_moves.append(move)

    # Return productive moves if available
    if productive_moves:
        return productive_moves

    # Otherwise return free moves if available (better than wasteful)
    if free_moves:
        return free_moves

    # Last resort: return original moves (all are wasteful or empty)
    return moves


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
        # Filter out wasteful moves (cost cards but 0 advancement)
        valid_moves = filter_wasteful_moves(valid_moves, engine)
        return random.choice(valid_moves)


class MarcSolerAgent(Agent):
    """Agent that always plays for maximum total advancement across all riders"""

    def __init__(self, player_id: int):
        super().__init__(player_id, "Marc Soler")

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
        # Filter out moves that cost cards but have 0 advancement (includes TeamCar as fallback)
        filtered_moves = filter_wasteful_moves(valid_moves, engine)

        # Prefer non-TeamCar moves if available
        non_team_car = [m for m in filtered_moves if m.action_type != ActionType.TEAM_CAR]
        if non_team_car:
            return max(non_team_car, key=lambda m: calculate_total_advancement(engine, m))

        # Fallback to TeamCar or any move
        if filtered_moves:
            best_move = filtered_moves[0]
            if best_move.action_type == ActionType.TEAM_CAR and not best_move.cards:
                worst_card = choose_card_to_discard(player)
                if worst_card:
                    best_move.cards = [worst_card]
            return best_move
        return valid_moves[0]


class ClaudeBotAgent(Agent):
    """A sophisticated agent that combines multiple strategic elements:

    1. Terrain-aware movement: Uses terrain limits to choose optimal riders for terrain
    2. Sprint optimization: Targets high-value sprints strategically
    3. Drafting efficiency: Maximizes free movement through drafts
    4. Card economy: Manages hand size and card types intelligently
    5. Rider specialization: Uses each rider type on their optimal terrain
    6. Positional play: Positions for future drafting opportunities
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "ClaudeBot")
        # Import terrain limits for decision making
        from game_engine import TERRAIN_LIMITS
        self.terrain_limits = TERRAIN_LIMITS

    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Choose the best move using a multi-factor scoring system"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None

        # Filter out moves that cost cards but have 0 advancement
        valid_moves = filter_wasteful_moves(valid_moves, engine)

        # Score all moves and pick the best
        scored_moves = []
        for move in valid_moves:
            score = self._score_move(move, engine, player)
            scored_moves.append((move, score))

        # Return highest scored move
        best_move = max(scored_moves, key=lambda x: x[1])
        return best_move[0]

    def _score_move(self, move: Move, engine: GameEngine, player: Player) -> float:
        """Score a move based on multiple strategic factors"""
        score = 0.0

        # Handle TeamCar specially
        if move.action_type == ActionType.TEAM_CAR:
            return self._score_team_car(player, engine)

        # Calculate actual movement after terrain limits
        base_movement = self._get_base_movement(move, engine)
        actual_movement = self._get_actual_movement(move, engine)

        # FACTOR 1: Base advancement value (weighted by riders moved)
        if move.action_type in [ActionType.TEAM_PULL, ActionType.TEAM_DRAFT]:
            num_riders = 1 + len(move.drafting_riders)
            # Calculate total team advancement with individual terrain limits
            total_advancement = self._calculate_team_advancement(move, engine, base_movement)
            score += total_advancement * 15
        else:
            score += actual_movement * 15

        # FACTOR 2: Card efficiency (drafts are free!)
        if move.action_type == ActionType.DRAFT:
            score += 100  # Big bonus for free movement
        elif move.action_type == ActionType.TEAM_DRAFT:
            num_riders = 1 + len(move.drafting_riders)
            score += 100 + (num_riders - 1) * 50  # Even bigger for multiple free moves
        elif move.action_type == ActionType.TEAM_PULL:
            # Free movement for drafters, cost cards for puller
            free_riders = len(move.drafting_riders)
            score += free_riders * 40

        # FACTOR 3: Sprint/Finish targeting
        score += self._score_sprint_potential(move, engine, actual_movement)

        # FACTOR 4: Terrain-rider matching
        score += self._score_terrain_matching(move, engine)

        # FACTOR 5: Card conservation (penalize using too many cards when not needed)
        if move.action_type in [ActionType.PULL, ActionType.ATTACK, ActionType.TEAM_PULL]:
            cards_used = len(move.cards)
            hand_size = len(player.hand)

            # Penalize heavily if this would leave us with very few cards
            if hand_size - cards_used <= 1:
                score -= 50
            elif hand_size - cards_used <= 2:
                score -= 20

            # Penalize attacks slightly (they use 3 cards)
            if move.action_type == ActionType.ATTACK:
                score -= 15

        # FACTOR 6: Positioning for future drafts
        score += self._score_positioning(move, engine, player, actual_movement)

        # FACTOR 7: Avoid wasting movement on terrain-limited riders
        if actual_movement < base_movement:
            # We're hitting terrain limits - this might not be the best rider
            wasted = base_movement - actual_movement
            score -= wasted * 8

        # FACTOR 8: Progress penalty for 0 movement
        if actual_movement == 0:
            score -= 200  # Strongly discourage no-progress moves

        return score

    def _get_base_movement(self, move: Move, engine: GameEngine) -> int:
        """Get base movement before terrain limits"""
        if move.action_type == ActionType.PULL:
            return engine._calculate_pull_movement(move.rider, move.cards)
        elif move.action_type == ActionType.ATTACK:
            return engine._calculate_attack_movement(move.rider, move.cards)
        elif move.action_type == ActionType.DRAFT:
            if engine.state.last_move:
                return engine.state.last_move.get('movement', 0)
            return 0
        elif move.action_type == ActionType.TEAM_PULL:
            return engine._calculate_pull_movement(move.rider, move.cards)
        elif move.action_type == ActionType.TEAM_DRAFT:
            if engine.state.last_move:
                return engine.state.last_move.get('movement', 0)
            return 0
        return 0

    def _get_actual_movement(self, move: Move, engine: GameEngine) -> int:
        """Get actual movement after applying terrain limits for the primary rider"""
        base = self._get_base_movement(move, engine)
        return engine._calculate_limited_movement(move.rider, move.rider.position, base)

    def _calculate_team_advancement(self, move: Move, engine: GameEngine, base_movement: int) -> int:
        """Calculate total advancement for team moves, accounting for per-rider terrain limits"""
        total = 0

        # Primary rider
        primary_movement = engine._calculate_limited_movement(
            move.rider, move.rider.position, base_movement
        )
        total += primary_movement

        # Drafting riders (each has their own terrain limits)
        for drafter in move.drafting_riders:
            drafter_movement = engine._calculate_limited_movement(
                drafter, drafter.position, base_movement
            )
            total += drafter_movement

        return total

    def _score_sprint_potential(self, move: Move, engine: GameEngine, actual_movement: int) -> float:
        """Score based on sprint/finish line potential"""
        score = 0.0
        old_pos = move.rider.position
        new_pos = min(old_pos + actual_movement, engine.state.track_length - 1)

        # Check all positions crossed for sprints
        for pos in range(old_pos + 1, new_pos + 1):
            tile = engine.state.get_tile_at_position(pos)
            if tile:
                if tile.terrain == TerrainType.FINISH:
                    # Huge bonus for finishing - check arrival order
                    arrivals = engine.state.sprint_arrivals.get(pos, [])
                    position_in_race = len(arrivals)
                    # Points: [12, 8, 5, 3, 1] for top 5
                    if position_in_race == 0:
                        score += 200  # First to finish!
                    elif position_in_race == 1:
                        score += 150
                    elif position_in_race == 2:
                        score += 100
                    elif position_in_race < 5:
                        score += 50
                elif tile.terrain == TerrainType.SPRINT:
                    # Bonus for intermediate sprints
                    arrivals = engine.state.sprint_arrivals.get(pos, [])
                    position_in_sprint = len(arrivals)
                    # Points: [3, 2, 1] for top 3
                    if position_in_sprint == 0:
                        score += 60
                    elif position_in_sprint == 1:
                        score += 40
                    elif position_in_sprint == 2:
                        score += 20

        # Also check for drafting riders in team moves
        if move.action_type in [ActionType.TEAM_PULL, ActionType.TEAM_DRAFT]:
            base_movement = self._get_base_movement(move, engine)
            for drafter in move.drafting_riders:
                drafter_movement = engine._calculate_limited_movement(
                    drafter, drafter.position, base_movement
                )
                drafter_old = drafter.position
                drafter_new = min(drafter_old + drafter_movement, engine.state.track_length - 1)

                for pos in range(drafter_old + 1, drafter_new + 1):
                    tile = engine.state.get_tile_at_position(pos)
                    if tile and tile.terrain == TerrainType.FINISH:
                        arrivals = engine.state.sprint_arrivals.get(pos, [])
                        if len(arrivals) < 5:
                            score += 80  # Bonus for getting more riders to finish
                    elif tile and tile.terrain == TerrainType.SPRINT:
                        arrivals = engine.state.sprint_arrivals.get(pos, [])
                        if len(arrivals) < 3:
                            score += 25

        return score

    def _score_terrain_matching(self, move: Move, engine: GameEngine) -> float:
        """Score based on how well the rider matches the terrain"""
        score = 0.0
        rider_type = move.rider.rider_type
        current_terrain = engine._get_terrain_at_position(move.rider.position)

        # Destination terrain analysis
        base_movement = self._get_base_movement(move, engine)
        actual_movement = self._get_actual_movement(move, engine)
        dest_pos = min(move.rider.position + actual_movement, engine.state.track_length - 1)
        dest_terrain = engine._get_terrain_at_position(dest_pos)

        # Bonus for using the right rider on the right terrain
        if rider_type == CardType.CLIMBER and current_terrain == TerrainType.CLIMB:
            score += 30  # Climbers excel on climbs
        elif rider_type == CardType.SPRINTER and current_terrain == TerrainType.FLAT:
            score += 20  # Sprinters excel on flats
        elif rider_type == CardType.SPRINTER and current_terrain == TerrainType.DESCENT:
            score += 25  # Sprinters are fast on descents too
        elif rider_type == CardType.ROULEUR:
            score += 10  # Rouleurs are balanced, small bonus everywhere

        # Penalty for using terrain-limited riders on their weak terrain
        limit_key = (rider_type, current_terrain)
        if limit_key in self.terrain_limits:
            score -= 15  # This rider is limited on this terrain

        return score

    def _score_positioning(self, move: Move, engine: GameEngine, player: Player, actual_movement: int) -> float:
        """Score based on positioning for future drafts"""
        score = 0.0
        dest_pos = min(move.rider.position + actual_movement, engine.state.track_length - 1)

        # Check if we end up next to other riders
        riders_at_dest = engine.state.get_riders_at_position(dest_pos)

        # Bonus for being with opponent riders (drafting opportunity)
        opponent_riders = [r for r in riders_at_dest if r.player_id != player.player_id]
        if opponent_riders:
            score += len(opponent_riders) * 20

        # Bonus for being with own riders (team move opportunity)
        own_riders = [r for r in riders_at_dest if r.player_id == player.player_id and r != move.rider]
        if own_riders:
            score += len(own_riders) * 15

        return score

    def _score_team_car(self, player: Player, engine: GameEngine) -> float:
        """Score TeamCar action"""
        hand_size = len(player.hand)

        # TeamCar is valuable when hand is low
        if hand_size <= 1:
            return 80  # Critical need for cards
        elif hand_size <= 2:
            return 40  # Low cards, could use more
        elif hand_size <= 3:
            return 10  # Okay but not urgent
        else:
            return -50  # Don't waste a turn drawing when we have cards

    def _get_rider_terrain_limit(self, rider_type: CardType, terrain: TerrainType) -> Optional[int]:
        """Get terrain limit for a rider type on a terrain, if any"""
        return self.terrain_limits.get((rider_type, terrain))


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


class GeminiAgent(Agent):
    """
    Gemini Bot: A strategic agent that balances advancement, scoring, and efficiency.
    It evaluates moves based on a weighted scoring system considering:
    - Total advancement (distance * riders)
    - Sprint/Finish points
    - Card efficiency (favoring drafts)
    - Checkpoints (card draw)
    - Hand management (TeamCar)
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "Gemini")

    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None

        # Filter out moves that cost cards but have 0 advancement
        valid_moves = filter_wasteful_moves(valid_moves, engine)

        scored_moves = []
        for move in valid_moves:
            score = self._score_move(move, engine, player)
            scored_moves.append((score, move))

        # Sort by score descending
        scored_moves.sort(key=lambda x: x[0], reverse=True)

        best_move = scored_moves[0][1]

        # If TeamCar is selected, ensure we pick a card to discard
        if best_move.action_type == ActionType.TEAM_CAR and not best_move.cards:
            worst_card = choose_card_to_discard(player)
            if worst_card:
                best_move.cards = [worst_card]

        return best_move

    def _score_move(self, move: Move, engine: GameEngine, player: Player) -> float:
        score = 0.0

        # 1. Handle TeamCar separately
        if move.action_type == ActionType.TEAM_CAR:
            # Base score for TeamCar is low, unless we really need cards
            score = -20.0
            # Bonus for low hand size
            if len(player.hand) <= 2:
                score += 60.0
            elif len(player.hand) <= 3:
                score += 30.0
            return score

        # 2. Calculate Advancement
        advancement = calculate_total_advancement(engine, move)
        score += advancement * 10.0

        # 3. Calculate Points (Sprints/Finish)
        points = self._estimate_points(move, engine)
        score += points * 50.0

        # 4. Card Efficiency (Penalize using cards)
        cards_used = len(move.cards)
        score -= cards_used * 8.0

        # 5. Checkpoints (Card draw potential)
        checkpoints = self._count_checkpoints(move, engine)
        score += checkpoints * 15.0

        return score

    def _get_move_distance(self, move: Move, engine: GameEngine) -> int:
        """Calculate distance for any move type"""
        if move.action_type in [ActionType.PULL, ActionType.TEAM_PULL]:
            return engine._calculate_pull_movement(move.rider, move.cards)
        elif move.action_type == ActionType.ATTACK:
            return engine._calculate_attack_movement(move.rider, move.cards)
        elif move.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT]:
            if engine.state.last_move:
                return engine.state.last_move.get('movement', 0)
        return 0

    def _estimate_points(self, move: Move, engine: GameEngine) -> int:
        """Estimate points earned by this move"""
        points = 0
        riders = [move.rider]
        if move.drafting_riders:
            riders.extend(move.drafting_riders)

        distance = self._get_move_distance(move, engine)
        if distance == 0:
            return 0

        for rider in riders:
            old_pos = rider.position
            new_pos = min(old_pos + distance, engine.state.track_length - 1)

            # Check all tiles crossed
            for pos in range(old_pos + 1, new_pos + 1):
                tile = engine.state.get_tile_at_position(pos)
                if tile and tile.terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
                    # Check if points are still available
                    arrivals = engine.state.sprint_arrivals.get(pos, [])
                    if rider in arrivals:
                        continue
                    current_rank = len(arrivals)
                    if tile.sprint_points and current_rank < len(tile.sprint_points):
                        points += tile.sprint_points[current_rank]
        return points

    def _count_checkpoints(self, move: Move, engine: GameEngine) -> int:
        """Count new checkpoints reached"""
        count = 0
        riders = [move.rider]
        if move.drafting_riders:
            riders.extend(move.drafting_riders)

        distance = self._get_move_distance(move, engine)
        if distance == 0:
            return 0

        for rider in riders:
            old_pos = rider.position
            new_pos = min(old_pos + distance, engine.state.track_length - 1)

            # Checkpoints are at 10, 20, 30...
            for cp in range(10, new_pos + 1, 10):
                if cp > old_pos and not engine.state.has_rider_reached_checkpoint(rider, cp):
                    count += 1
        return count


class TobiBotAgent(Agent):
    """
    TobiBot: A strategic agent with prioritized decision-making:
    1. Score points when possible (maximize sprint/finish points)
    2. When hand ≤ 6, play TeamCar unless move efficiency >1 field/card
    3. Prefer efficient moves: TeamDraft > Draft > TeamPull
    4. Group with team riders (only when moving forward to join riders ahead)
    5. When El Patron, position with opponents
    6. Maximize team advancement respecting terrain limits (with bonus for card efficiency)
    7. TeamCar if any isolated rider lacks good options
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "TobiBot")

    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None

        # Priority 1: Score points when possible
        scoring_moves = self._get_scoring_moves(valid_moves, engine)
        if scoring_moves:
            # Return move that scores most points
            return max(scoring_moves, key=lambda m: self._calculate_points(m, engine))

        # Priority 2: Hand management - TeamCar if hand ≤ 6 and no efficient moves
        if len(player.hand) <= 6:
            # Check if any move has >1 field per card
            has_efficient_move = False
            for move in valid_moves:
                if move.action_type == ActionType.TEAM_CAR:
                    continue
                advancement = calculate_total_advancement(engine, move)
                # Skip moves with 0 advancement
                if advancement == 0:
                    continue
                cards_used = len(move.cards)
                if cards_used == 0:
                    # Free move with advancement > 0 is efficient
                    has_efficient_move = True
                    break
                if advancement / cards_used > 1:
                    has_efficient_move = True
                    break

            if not has_efficient_move:
                team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
                if team_car_moves:
                    worst_card = choose_card_to_discard(player)
                    if worst_card:
                        team_car_moves[0].cards = [worst_card]
                    return team_car_moves[0]

        # Priority 3: Prefer efficient moves (filter out 0-advancement moves)
        # TeamDraft
        team_draft_moves = [m for m in valid_moves
                           if m.action_type == ActionType.TEAM_DRAFT
                           and calculate_total_advancement(engine, m) > 0]
        if team_draft_moves:
            return max(team_draft_moves, key=lambda m: calculate_total_advancement(engine, m))

        # Draft
        draft_moves = [m for m in valid_moves
                      if m.action_type == ActionType.DRAFT
                      and calculate_total_advancement(engine, m) > 0]
        if draft_moves:
            return max(draft_moves, key=lambda m: calculate_total_advancement(engine, m))

        # TeamPull
        team_pull_moves = [m for m in valid_moves
                          if m.action_type == ActionType.TEAM_PULL
                          and calculate_total_advancement(engine, m) > 0]
        if team_pull_moves:
            # Apply priority 4-6 to select best TeamPull
            return self._select_best_move(team_pull_moves, engine, player)

        # Apply priorities 4-6 to remaining moves (excluding TeamCar and 0-advancement moves)
        non_team_car = [m for m in valid_moves
                       if m.action_type != ActionType.TEAM_CAR
                       and calculate_total_advancement(engine, m) > 0]
        if non_team_car:
            return self._select_best_move(non_team_car, engine, player)

        # Priority 7: If any isolated rider lacks good options, consider TeamCar
        eligible_riders_list = eligible_riders if eligible_riders is not None else player.riders
        if eligible_riders_list:
            # Check if any eligible rider is isolated
            for rider in eligible_riders_list:
                if self._is_rider_isolated(rider, engine, player):
                    # Check if this rider can draft or advance >4 fields
                    rider_moves = [m for m in valid_moves if m.rider == rider]
                    can_draft = any(m.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT] for m in rider_moves)
                    can_advance_far = any(calculate_move_distance(engine, m) > 4 for m in rider_moves
                                         if m.action_type in [ActionType.PULL, ActionType.ATTACK])

                    if not can_draft and not can_advance_far:
                        team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
                        if team_car_moves:
                            worst_card = choose_card_to_discard(player)
                            if worst_card:
                                team_car_moves[0].cards = [worst_card]
                            return team_car_moves[0]

        # Fallback
        return valid_moves[0]

    def _get_scoring_moves(self, valid_moves: List[Move], engine: GameEngine) -> List[Move]:
        """Get moves that can score points at sprint or finish"""
        scoring_moves = []
        for move in valid_moves:
            if move.action_type == ActionType.TEAM_CAR:
                continue
            if self._calculate_points(move, engine) > 0:
                scoring_moves.append(move)
        return scoring_moves

    def _calculate_points(self, move: Move, engine: GameEngine) -> int:
        """Calculate total points this move would score"""
        points = 0
        riders = [move.rider]
        if move.drafting_riders:
            riders.extend(move.drafting_riders)

        for rider in riders:
            distance = self._get_rider_movement(move, rider, engine)
            if distance == 0:
                continue

            old_pos = rider.position
            new_pos = min(old_pos + distance, engine.state.track_length - 1)

            for pos in range(old_pos + 1, new_pos + 1):
                tile = engine.state.get_tile_at_position(pos)
                if tile and tile.terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
                    arrivals = engine.state.sprint_arrivals.get(pos, [])
                    if rider in arrivals:
                        continue
                    current_rank = len(arrivals)
                    if tile.sprint_points and current_rank < len(tile.sprint_points):
                        points += tile.sprint_points[current_rank]
        return points

    def _get_rider_movement(self, move: Move, rider: Rider, engine: GameEngine) -> int:
        """Get movement for a specific rider in a move"""
        if rider == move.rider:
            # Primary rider
            if move.action_type == ActionType.PULL:
                base = engine._calculate_pull_movement(move.rider, move.cards)
            elif move.action_type == ActionType.ATTACK:
                base = engine._calculate_attack_movement(move.rider, move.cards)
            elif move.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT]:
                base = engine.state.last_move.get('movement', 0) if engine.state.last_move else 0
            elif move.action_type == ActionType.TEAM_PULL:
                base = engine._calculate_pull_movement(move.rider, move.cards)
            else:
                return 0
            return engine._calculate_limited_movement(rider, rider.position, base)
        else:
            # Drafting rider
            if move.action_type == ActionType.TEAM_PULL:
                base = engine._calculate_pull_movement(move.rider, move.cards)
            elif move.action_type == ActionType.TEAM_DRAFT:
                base = engine.state.last_move.get('movement', 0) if engine.state.last_move else 0
            else:
                return 0
            return engine._calculate_limited_movement(rider, rider.position, base)

    def _is_rider_isolated(self, rider: Rider, engine: GameEngine, player: Player) -> bool:
        """Check if rider is on a field with no teammates"""
        riders_at_pos = engine.state.get_riders_at_position(rider.position)
        teammates = [r for r in riders_at_pos if r.player_id == player.player_id and r != rider]
        return len(teammates) == 0

    def _select_best_move(self, moves: List[Move], engine: GameEngine, player: Player) -> Move:
        """Select best move considering priorities 4-6"""
        scored_moves = []

        for move in moves:
            score = 0.0

            # Calculate destination
            distance = calculate_move_distance(engine, move)
            if distance == 0:
                continue
            destination = min(move.rider.position + distance, engine.state.track_length - 1)

            # Priority 4: Advance to field with team riders (only if moving forward to join them)
            riders_at_dest = engine.state.get_riders_at_position(destination)
            teammates_at_dest = [r for r in riders_at_dest if r.player_id == player.player_id and r != move.rider]
            # Only give bonus if destination is ahead of current position
            if destination > move.rider.position:
                score += len(teammates_at_dest) * 50

            # Priority 5: When El Patron, move to fields with opponents
            is_el_patron = (engine.state.el_patron == player.player_id)
            if is_el_patron:
                opponents_at_dest = [r for r in riders_at_dest if r.player_id != player.player_id]
                score += len(opponents_at_dest) * 40

            # Priority 6: Maximize team advancement while respecting terrain limits
            total_advancement = calculate_total_advancement(engine, move)
            score += total_advancement * 10

            # Additional bonus for card efficiency (advancement per card)
            cards_used = len(move.cards) if move.cards else 0
            if cards_used > 0 and total_advancement > 0:
                efficiency = total_advancement / cards_used
                score += efficiency * 5  # Bonus for efficient card usage

            # For team moves, check if we're respecting terrain limits
            if move.action_type in [ActionType.TEAM_PULL, ActionType.TEAM_DRAFT]:
                # Calculate minimum movement among all riders
                min_movement = distance
                for rider in [move.rider] + list(move.drafting_riders):
                    rider_movement = self._get_rider_movement(move, rider, engine)
                    min_movement = min(min_movement, rider_movement)

                # Bonus if we're keeping team together (all riders move similar distance)
                if min_movement > 0:
                    score += min_movement * 5

            scored_moves.append((score, move))

        if scored_moves:
            return max(scored_moves, key=lambda x: x[0])[1]
        return moves[0]


class ClaudeBot2Agent(Agent):
    """
    ClaudeBot 2.0: Redesigned based on comprehensive 250-game analysis.

    Adopts TobiBot's proven priority hierarchy approach (97.1% win rate):
    1. Score points when possible (finish > sprint priority)
    2. Hand management: TeamCar if hand ≤ 6 AND no efficient move (>1 field/card)
    3. Prefer efficient moves: TeamDraft > Draft > TeamPull > Pull
    4. Maximize advancement with terrain-aware optimization
    5. Position strategically (group with teammates ahead, draft opponents)

    Key metrics to achieve (from winning data):
    - Card efficiency: <0.40 cards/field (vs losers' 0.50)
    - Early game: 90+ fields in first third
    - Free movement: 3+ drafts per game
    - Finish points: 15+ from finish line
    - Hand management: 4+ average cards

    Strategy: Strict priority hierarchy with efficiency gating, not weighted scoring.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "ClaudeBot2.0")
        from game_engine import TERRAIN_LIMITS
        self.terrain_limits = TERRAIN_LIMITS

    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        """Choose move using TobiBot-inspired priority hierarchy"""
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None

        # PRIORITY 1: Score points when possible (finish > sprint)
        scoring_moves = self._get_scoring_moves(valid_moves, engine)
        if scoring_moves:
            # Return move that scores most points, preferring finish over sprint
            return max(scoring_moves, key=lambda m: self._calculate_points_with_priority(m, engine))

        # PRIORITY 2: Hand management - TeamCar if hand ≤ 6 and no efficient moves
        if len(player.hand) <= 6:
            # Check if any move has >1 field per card efficiency
            has_efficient_move = False
            for move in valid_moves:
                if move.action_type == ActionType.TEAM_CAR:
                    continue
                advancement = calculate_total_advancement(engine, move)
                if advancement == 0:
                    continue
                cards_used = len(move.cards)
                if cards_used == 0:
                    has_efficient_move = True
                    break
                if advancement / cards_used > 1.0:
                    has_efficient_move = True
                    break

            if not has_efficient_move:
                team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
                if team_car_moves:
                    worst_card = choose_card_to_discard(player)
                    if worst_card:
                        team_car_moves[0].cards = [worst_card]
                    return team_car_moves[0]

        # PRIORITY 3: Prefer efficient free movement (TeamDraft > Draft > TeamPull)
        # Filter out 0-advancement moves
        productive_moves = [m for m in valid_moves
                           if m.action_type != ActionType.TEAM_CAR
                           and calculate_total_advancement(engine, m) > 0]

        if not productive_moves:
            # Fallback to TeamCar if nothing productive
            team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
            if team_car_moves:
                worst_card = choose_card_to_discard(player)
                if worst_card:
                    team_car_moves[0].cards = [worst_card]
                return team_car_moves[0]
            return valid_moves[0] if valid_moves else None

        # TeamDraft: Multiple riders move for free
        team_draft_moves = [m for m in productive_moves if m.action_type == ActionType.TEAM_DRAFT]
        if team_draft_moves:
            return max(team_draft_moves, key=lambda m: calculate_total_advancement(engine, m))

        # Draft: Single rider moves for free
        draft_moves = [m for m in productive_moves if m.action_type == ActionType.DRAFT]
        if draft_moves:
            return max(draft_moves, key=lambda m: calculate_total_advancement(engine, m))

        # TeamPull: One rider pulls, others draft (efficient team coordination)
        team_pull_moves = [m for m in productive_moves if m.action_type == ActionType.TEAM_PULL]
        if team_pull_moves:
            return self._select_best_team_pull(team_pull_moves, engine, player)

        # PRIORITY 4: Remaining moves (Pull, Attack) - select with terrain optimization
        remaining_moves = [m for m in productive_moves
                          if m.action_type in [ActionType.PULL, ActionType.ATTACK]]
        if remaining_moves:
            return self._select_best_advancement_move(remaining_moves, engine, player)

        # Fallback: any productive move
        if productive_moves:
            return max(productive_moves, key=lambda m: calculate_total_advancement(engine, m))

        # Last resort: TeamCar
        team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
        if team_car_moves:
            worst_card = choose_card_to_discard(player)
            if worst_card:
                team_car_moves[0].cards = [worst_card]
            return team_car_moves[0]

        return valid_moves[0] if valid_moves else None

    def _get_scoring_moves(self, valid_moves: List[Move], engine: GameEngine) -> List[Move]:
        """Get moves that can score points at sprint or finish"""
        scoring_moves = []
        for move in valid_moves:
            if move.action_type == ActionType.TEAM_CAR:
                continue
            if self._calculate_points(move, engine) > 0:
                scoring_moves.append(move)
        return scoring_moves

    def _calculate_points(self, move: Move, engine: GameEngine) -> int:
        """Calculate total points this move would score"""
        points = 0
        riders = [move.rider]
        if move.drafting_riders:
            riders.extend(move.drafting_riders)

        for rider in riders:
            distance = self._get_rider_movement(move, rider, engine)
            if distance == 0:
                continue

            old_pos = rider.position
            new_pos = min(old_pos + distance, engine.state.track_length - 1)

            for pos in range(old_pos + 1, new_pos + 1):
                tile = engine.state.get_tile_at_position(pos)
                if tile and tile.terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
                    arrivals = engine.state.sprint_arrivals.get(pos, [])
                    if rider in arrivals:
                        continue
                    current_rank = len(arrivals)
                    if tile.sprint_points and current_rank < len(tile.sprint_points):
                        points += tile.sprint_points[current_rank]
        return points

    def _calculate_points_with_priority(self, move: Move, engine: GameEngine) -> float:
        """Calculate points with finish line heavily prioritized over sprints"""
        finish_points = 0
        sprint_points = 0

        riders = [move.rider]
        if move.drafting_riders:
            riders.extend(move.drafting_riders)

        for rider in riders:
            distance = self._get_rider_movement(move, rider, engine)
            if distance == 0:
                continue

            old_pos = rider.position
            new_pos = min(old_pos + distance, engine.state.track_length - 1)

            for pos in range(old_pos + 1, new_pos + 1):
                tile = engine.state.get_tile_at_position(pos)
                if tile and tile.terrain == TerrainType.FINISH:
                    arrivals = engine.state.sprint_arrivals.get(pos, [])
                    if rider not in arrivals:
                        current_rank = len(arrivals)
                        if tile.sprint_points and current_rank < len(tile.sprint_points):
                            finish_points += tile.sprint_points[current_rank]
                elif tile and tile.terrain == TerrainType.SPRINT:
                    arrivals = engine.state.sprint_arrivals.get(pos, [])
                    if rider not in arrivals:
                        current_rank = len(arrivals)
                        if tile.sprint_points and current_rank < len(tile.sprint_points):
                            sprint_points += tile.sprint_points[current_rank]

        # Finish points are 55% of winner's score, weight them 3x higher
        return finish_points * 3.0 + sprint_points

    def _get_rider_movement(self, move: Move, rider: Rider, engine: GameEngine) -> int:
        """Get movement for a specific rider in a move"""
        if rider == move.rider:
            # Primary rider
            if move.action_type == ActionType.PULL:
                base = engine._calculate_pull_movement(move.rider, move.cards)
            elif move.action_type == ActionType.ATTACK:
                base = engine._calculate_attack_movement(move.rider, move.cards)
            elif move.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT]:
                base = engine.state.last_move.get('movement', 0) if engine.state.last_move else 0
            elif move.action_type == ActionType.TEAM_PULL:
                base = engine._calculate_pull_movement(move.rider, move.cards)
            else:
                return 0
            return engine._calculate_limited_movement(rider, rider.position, base)
        else:
            # Drafting rider
            if move.action_type == ActionType.TEAM_PULL:
                base = engine._calculate_pull_movement(move.rider, move.cards)
            elif move.action_type == ActionType.TEAM_DRAFT:
                base = engine.state.last_move.get('movement', 0) if engine.state.last_move else 0
            else:
                return 0
            return engine._calculate_limited_movement(rider, rider.position, base)

    def _select_best_team_pull(self, moves: List[Move], engine: GameEngine, player: Player) -> Move:
        """Select best TeamPull considering efficiency and positioning"""
        scored_moves = []

        for move in moves:
            score = 0.0

            # Base score: total advancement
            total_advancement = calculate_total_advancement(engine, move)
            score += total_advancement * 10

            # Card efficiency bonus
            cards_used = len(move.cards)
            if cards_used > 0 and total_advancement > 0:
                efficiency = total_advancement / cards_used
                score += efficiency * 20  # Reward high efficiency

            # Bonus for grouping riders together (team coordination)
            destination = min(move.rider.position + self._get_rider_movement(move, move.rider, engine),
                            engine.state.track_length - 1)
            riders_at_dest = engine.state.get_riders_at_position(destination)
            own_riders = [r for r in riders_at_dest if r.player_id == player.player_id and r != move.rider]
            score += len(own_riders) * 15

            # Terrain matching bonus
            score += self._score_terrain_matching_simple(move, engine)

            scored_moves.append((score, move))

        return max(scored_moves, key=lambda x: x[0])[1]

    def _select_best_advancement_move(self, moves: List[Move], engine: GameEngine, player: Player) -> Move:
        """Select best Pull/Attack move with terrain optimization"""
        scored_moves = []

        for move in moves:
            score = 0.0

            # Base score: actual movement after terrain limits
            distance = self._get_rider_movement(move, move.rider, engine)
            score += distance * 10

            # Card efficiency penalty
            cards_used = len(move.cards)
            if cards_used > 0 and distance > 0:
                efficiency = distance / cards_used
                score += efficiency * 15
            else:
                score -= 50  # Penalize inefficient moves

            # Terrain matching
            score += self._score_terrain_matching_simple(move, engine)

            # Positioning for future drafts
            destination = min(move.rider.position + distance, engine.state.track_length - 1)
            riders_at_dest = engine.state.get_riders_at_position(destination)
            opponent_riders = [r for r in riders_at_dest if r.player_id != player.player_id]
            score += len(opponent_riders) * 20  # Good for future drafting

            scored_moves.append((score, move))

        return max(scored_moves, key=lambda x: x[0])[1]

    def _score_terrain_matching_simple(self, move: Move, engine: GameEngine) -> float:
        """Simple terrain matching bonus"""
        score = 0.0
        rider_type = move.rider.rider_type
        current_terrain = engine._get_terrain_at_position(move.rider.position)

        # Bonus for good matches
        if rider_type == CardType.CLIMBER and current_terrain == TerrainType.CLIMB:
            score += 30
        elif rider_type == CardType.SPRINTER and current_terrain in [TerrainType.FLAT, TerrainType.DESCENT]:
            score += 25
        elif rider_type == CardType.ROULEUR:
            score += 10

        # Penalty for terrain-limited riders
        if (rider_type, current_terrain) in self.terrain_limits:
            score -= 20

        return score



class ChatGPTAgent(Agent):
    """
    ChatGPT Bot: A balanced agent that values steady advancement, sprint points,
    and card efficiency while preferring free movement when possible.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "ChatGPT")

    def choose_move(self, engine: GameEngine, player: Player, eligible_riders: List[Rider] = None) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None

        # Low hand: prioritize free movement, then refill
        if len(player.hand) < 3:
            draft_move = get_best_draft_move(valid_moves)
            if draft_move:
                return draft_move
            if should_use_team_car(player, valid_moves):
                team_car_moves = [m for m in valid_moves if m.action_type == ActionType.TEAM_CAR]
                if team_car_moves:
                    worst_card = choose_card_to_discard(player)
                    if worst_card:
                        team_car_moves[0].cards = [worst_card]
                    return team_car_moves[0]

        # Filter out moves that cost cards but have 0 advancement
        valid_moves = filter_wasteful_moves(valid_moves, engine)

        scored_moves = []
        for move in valid_moves:
            score = self._score_move(move, engine, player)
            scored_moves.append((score, move))

        scored_moves.sort(key=lambda x: x[0], reverse=True)
        best_move = scored_moves[0][1]

        if best_move.action_type == ActionType.TEAM_CAR and not best_move.cards:
            worst_card = choose_card_to_discard(player)
            if worst_card:
                best_move.cards = [worst_card]

        return best_move

    def _score_move(self, move: Move, engine: GameEngine, player: Player) -> float:
        # TeamCar is a fallback unless hand is low
        if move.action_type == ActionType.TEAM_CAR:
            if len(player.hand) <= 1:
                return 40.0
            if len(player.hand) <= 2:
                return 20.0
            return -30.0

        base_movement = self._get_base_movement(move, engine)
        if base_movement == 0:
            return -10.0

        # Advancement: total team movement with terrain limits
        advancement = self._calculate_total_movement(move, engine, base_movement)
        score = advancement * 8.0

        # Sprint/finish potential
        score += self._score_sprints(move, engine, base_movement) * 30.0

        # Card efficiency
        score -= len(move.cards) * 6.0

        # Prefer free movement
        if move.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT]:
            score += 15.0

        # Small bonus for drafting multiple riders
        if move.action_type in [ActionType.TEAM_PULL, ActionType.TEAM_DRAFT]:
            score += len(move.drafting_riders) * 5.0

        # Terrain matching bonus
        current_terrain = engine._get_terrain_at_position(move.rider.position)
        if move.rider.rider_type == CardType.CLIMBER and current_terrain == TerrainType.CLIMB:
            score += 10.0
        elif move.rider.rider_type == CardType.SPRINTER and current_terrain in [TerrainType.FLAT, TerrainType.DESCENT]:
            score += 8.0
        elif move.rider.rider_type == CardType.ROULEUR:
            score += 4.0

        return score

    def _get_base_movement(self, move: Move, engine: GameEngine) -> int:
        if move.action_type in [ActionType.PULL, ActionType.TEAM_PULL]:
            return engine._calculate_pull_movement(move.rider, move.cards)
        if move.action_type == ActionType.ATTACK:
            return engine._calculate_attack_movement(move.rider, move.cards)
        if move.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT]:
            if engine.state.last_move:
                return engine.state.last_move.get('movement', 0)
        return 0

    def _calculate_total_movement(self, move: Move, engine: GameEngine, base_movement: int) -> int:
        total = engine._calculate_limited_movement(move.rider, move.rider.position, base_movement)
        for drafter in move.drafting_riders:
            total += engine._calculate_limited_movement(drafter, drafter.position, base_movement)
        return total

    def _score_sprints(self, move: Move, engine: GameEngine, base_movement: int) -> float:
        score = 0.0
        riders = [move.rider] + list(move.drafting_riders)
        for rider in riders:
            actual = engine._calculate_limited_movement(rider, rider.position, base_movement)
            old_pos = rider.position
            new_pos = min(old_pos + actual, engine.state.track_length - 1)

            for pos in range(old_pos + 1, new_pos + 1):
                tile = engine.state.get_tile_at_position(pos)
                if tile and tile.terrain in [TerrainType.SPRINT, TerrainType.FINISH]:
                    arrivals = engine.state.sprint_arrivals.get(pos, [])
                    if rider in arrivals:
                        continue
                    if tile.sprint_points and len(arrivals) < len(tile.sprint_points):
                        score += tile.sprint_points[len(arrivals)]
        return score


# Factory function to create agents
def create_agent(agent_type: str, player_id: int) -> Agent:
    """Create an agent of the specified type"""
    agent_map = {
        'random': RandomAgent,
        'marc_soler': MarcSolerAgent,
        'wheelsucker': WheelsuckerAgent,
        'gemini': GeminiAgent,
        'chatgpt': ChatGPTAgent,
        'claudebot': ClaudeBotAgent,
        'claudebot2': ClaudeBot2Agent,
        'tobibot': TobiBotAgent,
    }

    if agent_type not in agent_map:
        raise ValueError(f"Unknown agent type: {agent_type}")

    return agent_map[agent_type](player_id)


def get_available_agents() -> List[str]:
    """Get list of all available agent types"""
    return [
        'random', 'marc_soler',
        'wheelsucker', 'gemini', 'chatgpt', 'claudebot', 'claudebot2', 'tobibot'
    ]


def verify_no_wasteful_moves() -> bool:
    """Verify that all agents avoid choosing moves that cost cards but have 0 advancement.

    This is a self-test to ensure agents never waste cards on 0-advancement moves.
    Returns True if all agents pass, False otherwise.
    """
    from game_state import GameState, Card
    from game_engine import GameEngine

    # Create test scenario: Sprinter on climb with only Sprinter cards
    # Sprinter is terrain-limited on climbs, so moves may have 0 advancement
    state = GameState(num_players=2)
    engine = GameEngine(state)

    # Position Sprinter at middle of climb tile
    state.players[0].riders[1].position = 14  # Sprinter

    # Give player only Sprinter cards
    state.players[0].hand = [
        Card(CardType.SPRINTER),
        Card(CardType.SPRINTER),
        Card(CardType.SPRINTER),
    ]

    all_passed = True
    failures = []

    for agent_type in get_available_agents():
        # Reset scenario for each agent
        state = GameState(num_players=2)
        engine = GameEngine(state)
        state.players[0].riders[1].position = 14
        state.players[0].hand = [
            Card(CardType.SPRINTER),
            Card(CardType.SPRINTER),
            Card(CardType.SPRINTER),
        ]

        agent = create_agent(agent_type, 0)
        chosen_move = agent.choose_move(engine, state.players[0])

        if chosen_move:
            # Free moves (Draft, TeamDraft, TeamCar) are always acceptable
            if chosen_move.action_type in [ActionType.DRAFT, ActionType.TEAM_DRAFT, ActionType.TEAM_CAR]:
                continue

            # Paid moves must have advancement > 0
            if len(chosen_move.cards) > 0:
                advancement = calculate_total_advancement(engine, chosen_move)
                if advancement == 0:
                    failures.append(f"{agent_type}: chose {chosen_move.action_type.value} with {len(chosen_move.cards)} cards but 0 advancement")
                    all_passed = False

    if not all_passed:
        print("WASTEFUL MOVE VERIFICATION FAILED:")
        for failure in failures:
            print(f"  ✗ {failure}")

    return all_passed
