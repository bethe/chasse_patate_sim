"""
Chasse Patate - PPO Machine Learning Agent
Neural network-based agent trained via Proximal Policy Optimization.
"""

import sys
from pathlib import Path

# Add project root to path so we can import game modules
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
from typing import List, Optional, Tuple

from game_state import Player, Card, CardType, TerrainType, ActionType, Rider
from game_engine import GameEngine, Move, TERRAIN_LIMITS
from agents import Agent, filter_wasteful_moves, calculate_move_distance, calculate_total_advancement


# ── Constants ──────────────────────────────────────────────────────────────────

STATE_DIM = 580
MOVE_DIM = 22
MAX_OPPONENTS = 3          # support up to 4-player games
MAX_TRACK_LENGTH = 100     # padded track encoding size (fields)
LOOKAHEAD_FIELDS = 10      # per-rider terrain lookahead

# Terrain categories for one-hot encoding (SPRINT/FINISH treated as FLAT)
TERRAIN_CATEGORIES = [TerrainType.FLAT, TerrainType.COBBLES, TerrainType.CLIMB, TerrainType.DESCENT]


# ── Feature Encoding ──────────────────────────────────────────────────────────

def _terrain_one_hot(terrain: TerrainType) -> List[float]:
    """Encode terrain as 4-element one-hot (SPRINT/FINISH → FLAT)."""
    effective = terrain
    if terrain in (TerrainType.SPRINT, TerrainType.FINISH):
        effective = TerrainType.FLAT
    return [1.0 if effective == t else 0.0 for t in TERRAIN_CATEGORIES]


def encode_state(engine: GameEngine, player: Player) -> torch.Tensor:
    """Encode full game state into a fixed-size float tensor (STATE_DIM,)."""
    state = engine.state
    finish_pos = state.track_length - 1
    features: List[float] = []

    # ── Own riders (3 × 7 = 21) ──────────────────────────────────────────
    for rider in player.riders:
        pos_norm = rider.position / max(finish_pos, 1)
        finished = float(rider.position >= finish_pos)
        terrain = engine._get_terrain_at_position(rider.position)
        t_hot = _terrain_one_hot(terrain)
        limited = float((rider.rider_type, terrain) in TERRAIN_LIMITS)
        features.extend([pos_norm, finished] + t_hot + [limited])

    # ── Full track terrain (MAX_TRACK_LENGTH × 4 = 400) ──────────────────
    # Static for the whole game; zero-padded if track < MAX_TRACK_LENGTH
    for pos in range(MAX_TRACK_LENGTH):
        if pos < state.track_length:
            tile = state.track[pos]
            features.extend(_terrain_one_hot(tile.terrain))
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])

    # ── Per-rider 10-field lookahead (3 × 10 × 4 = 120) ─────────────────
    for rider in player.riders:
        for offset in range(1, LOOKAHEAD_FIELDS + 1):
            ahead_pos = rider.position + offset
            if ahead_pos < state.track_length:
                tile = state.track[ahead_pos]
                features.extend(_terrain_one_hot(tile.terrain))
            else:
                features.extend([0.0, 0.0, 0.0, 0.0])

    # ── Hand composition (4) ─────────────────────────────────────────────
    counts = {ct: 0 for ct in CardType}
    for card in player.hand:
        counts[card.card_type] += 1
    features.extend([
        counts[CardType.ENERGY] / 10.0,
        counts[CardType.ROULEUR] / 10.0,
        counts[CardType.SPRINTER] / 10.0,
        counts[CardType.CLIMBER] / 10.0,
    ])

    # ── Scores: self + up to 3 opponents (4) ─────────────────────────────
    features.append(player.points / 30.0)
    opp_idx = 0
    for p in state.players:
        if p.player_id != player.player_id:
            features.append(p.points / 30.0)
            opp_idx += 1
    for _ in range(MAX_OPPONENTS - opp_idx):
        features.append(0.0)

    # ── Opponent riders (MAX_OPPONENTS × 3 × 2 = 18) ────────────────────
    opp_idx = 0
    for p in state.players:
        if p.player_id == player.player_id:
            continue
        for r in p.riders:
            features.append(r.position / max(finish_pos, 1))
            features.append(float(r.position >= finish_pos))
        opp_idx += 1
    for _ in range(MAX_OPPONENTS - opp_idx):
        features.extend([0.0] * 6)  # 3 riders × 2 features

    # ── Opponent finished rider counts (MAX_OPPONENTS = 3) ───────────────
    opp_idx = 0
    for p in state.players:
        if p.player_id == player.player_id:
            continue
        finished_count = sum(1 for r in p.riders if r.position >= finish_pos)
        features.append(finished_count / 3.0)
        opp_idx += 1
    for _ in range(MAX_OPPONENTS - opp_idx):
        features.append(0.0)

    # ── Opponent hand sizes (MAX_OPPONENTS = 3) ─────────────────────────
    opp_idx = 0
    for p in state.players:
        if p.player_id == player.player_id:
            continue
        features.append(len(p.hand) / 15.0)
        opp_idx += 1
    for _ in range(MAX_OPPONENTS - opp_idx):
        features.append(0.0)

    # ── Last move info (5) ───────────────────────────────────────────────
    lm = state.last_move
    if lm is not None:
        action = lm.get('action', '')
        features.append(1.0)  # has last move
        features.append(float(action in ('Pull', 'TeamPull')))
        features.append(float(action in ('Draft', 'TeamDraft')))
        features.append(lm.get('movement', 0) / 10.0)
        features.append(lm.get('old_position', 0) / max(finish_pos, 1))
    else:
        features.extend([0.0, 0.0, 0.0, 0.0, 0.0])

    # ── El Patron (1) ───────────────────────────────────────────────────
    features.append(float(state.el_patron == player.player_id))

    # ── Deck pressure (1) ───────────────────────────────────────────────
    features.append(len(state.deck) / 90.0)

    return torch.tensor(features, dtype=torch.float32)


def encode_move(engine: GameEngine, player: Player, move: Move) -> torch.Tensor:
    """Encode a single move into a fixed-size float tensor (MOVE_DIM,)."""
    state = engine.state
    finish_pos = state.track_length - 1
    features: List[float] = []

    # ── Action type one-hot (6) ──────────────────────────────────────────
    action_types = [ActionType.PULL, ActionType.ATTACK, ActionType.DRAFT,
                    ActionType.TEAM_PULL, ActionType.TEAM_DRAFT, ActionType.TEAM_CAR]
    features.extend([float(move.action_type == at) for at in action_types])

    # ── Primary rider one-hot (3) ───────────────────────────────────────
    rider_types = [CardType.ROULEUR, CardType.SPRINTER, CardType.CLIMBER]
    features.extend([float(move.rider.rider_type == rt) for rt in rider_types])

    # ── Movement metrics (5) ────────────────────────────────────────────
    base_movement = _get_base_movement(engine, move)
    actual_movement = engine._calculate_limited_movement(
        move.rider, move.rider.position, base_movement
    )
    total_advancement = calculate_total_advancement(engine, move)
    num_riders = 1 + len(move.drafting_riders)
    cards_used = len(move.cards)

    features.append(base_movement / 10.0)
    features.append(actual_movement / 10.0)
    features.append(total_advancement / 20.0)
    features.append(num_riders / 3.0)
    features.append(cards_used / 3.0)

    # ── Card economy (2) ────────────────────────────────────────────────
    cards_remaining = len(player.hand) - cards_used
    features.append(cards_remaining / 10.0)
    efficiency = (total_advancement / max(cards_used, 1)) / 10.0
    features.append(efficiency)

    # ── Terrain context (4) ─────────────────────────────────────────────
    terrain = engine._get_terrain_at_position(move.rider.position)
    limited = float((move.rider.rider_type, terrain) in TERRAIN_LIMITS)

    # Rider matches terrain well?
    rt = move.rider.rider_type
    good_match = (
        (rt == CardType.CLIMBER and terrain == TerrainType.CLIMB) or
        (rt == CardType.SPRINTER and terrain in (TerrainType.FLAT, TerrainType.DESCENT)) or
        (rt == CardType.ROULEUR)
    )
    features.append(limited)
    features.append(float(good_match))

    # Does the move cross a sprint or finish line?
    old_pos = move.rider.position
    new_pos = min(old_pos + actual_movement, finish_pos)
    hits_sprint = False
    hits_finish = False
    for pos in range(old_pos + 1, new_pos + 1):
        tile = state.get_tile_at_position(pos)
        if tile:
            if tile.terrain == TerrainType.SPRINT:
                hits_sprint = True
            elif tile.terrain == TerrainType.FINISH:
                hits_finish = True
    features.append(float(hits_sprint))
    features.append(float(hits_finish))

    # ── Position context (2) ────────────────────────────────────────────
    dest_riders = state.get_riders_at_position(new_pos)
    has_opponent = any(r.player_id != player.player_id for r in dest_riders)
    has_teammate = any(r.player_id == player.player_id and r != move.rider
                       for r in dest_riders)
    features.append(float(has_opponent))
    features.append(float(has_teammate))

    return torch.tensor(features, dtype=torch.float32)


def encode_moves(engine: GameEngine, player: Player,
                 moves: List[Move]) -> torch.Tensor:
    """Encode a list of moves into a (N, MOVE_DIM) tensor."""
    return torch.stack([encode_move(engine, player, m) for m in moves])


def _get_base_movement(engine: GameEngine, move: Move) -> int:
    """Get base movement before terrain limits for any move type."""
    if move.action_type in (ActionType.PULL, ActionType.TEAM_PULL):
        return engine._calculate_pull_movement(move.rider, move.cards)
    elif move.action_type == ActionType.ATTACK:
        return engine._calculate_attack_movement(move.rider, move.cards)
    elif move.action_type in (ActionType.DRAFT, ActionType.TEAM_DRAFT):
        if engine.state.last_move:
            return engine.state.last_move.get('movement', 0)
        return 0
    return 0


# ── Neural Network ────────────────────────────────────────────────────────────

class ChassePatatePolicyNetwork(nn.Module):
    """Actor-Critic network with move-scoring head.

    State encoder embeds the game state, then each valid move is scored by
    concatenating the state embedding with per-move features.  A separate
    value head estimates V(s).
    """

    def __init__(self, state_dim: int = STATE_DIM, move_dim: int = MOVE_DIM,
                 hidden: int = 256, embed_dim: int = 128):
        super().__init__()

        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.LayerNorm(hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.LayerNorm(hidden),
            nn.ReLU(),
            nn.Linear(hidden, embed_dim),
            nn.ReLU(),
        )

        self.move_scorer = nn.Sequential(
            nn.Linear(embed_dim + move_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, embed_dim),
            nn.ReLU(),
            nn.Linear(embed_dim, 1),
        )

        self.value_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.ReLU(),
            nn.Linear(embed_dim, 1),
        )

    def forward(self, state_vec: torch.Tensor,
                move_feats: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            state_vec:  (state_dim,) or (B, state_dim)
            move_feats: (N, move_dim) — N valid moves for this state

        Returns:
            logits: (N,) unnormalised log-probs over valid moves
            value:  scalar state value
        """
        if state_vec.dim() == 1:
            state_vec = state_vec.unsqueeze(0)  # (1, state_dim)

        state_emb = self.state_encoder(state_vec)          # (1, embed)
        n_moves = move_feats.shape[0]
        state_expanded = state_emb.expand(n_moves, -1)     # (N, embed)
        combined = torch.cat([state_expanded, move_feats], dim=1)  # (N, embed+move)
        logits = self.move_scorer(combined).squeeze(-1)    # (N,)
        value = self.value_head(state_emb).squeeze()       # scalar
        return logits, value


# ── PPO Agent ─────────────────────────────────────────────────────────────────

DEFAULT_CHECKPOINT = str(Path(__file__).resolve().parent / 'ml_agent_checkpoint.pt')


class PPOAgent(Agent):
    """PPO-trained agent compatible with the existing Agent interface.

    During inference it greedily picks the highest-scoring valid move.
    During training, the training loop handles sampling.
    """

    def __init__(self, player_id: int, checkpoint_path: str = None,
                 network: ChassePatatePolicyNetwork = None):
        super().__init__(player_id, "PPO")
        self.network = network or ChassePatatePolicyNetwork()

        # Load weights if available
        path = checkpoint_path or DEFAULT_CHECKPOINT
        if Path(path).exists():
            self.network.load_state_dict(
                torch.load(path, map_location='cpu', weights_only=True)
            )
        self.network.eval()

    def choose_move(self, engine: GameEngine, player: Player,
                    eligible_riders: List[Rider] = None) -> Optional[Move]:
        valid_moves = engine.get_valid_moves(player, eligible_riders)
        if not valid_moves:
            return None

        valid_moves = filter_wasteful_moves(valid_moves, engine)

        state_vec = encode_state(engine, player)
        move_feats = encode_moves(engine, player, valid_moves)

        with torch.no_grad():
            logits, _ = self.network(state_vec, move_feats)

        action_idx = logits.argmax().item()
        return valid_moves[action_idx]
