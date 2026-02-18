"""
Chasse Patate - PPO Training Script

Trains the ML agent via self-play and curriculum learning against heuristic bots.

Usage:
    python train_ml_agent.py                          # Full training (2500 iters)
    python train_ml_agent.py --iterations 500         # Custom iteration count
    python train_ml_agent.py --resume checkpoint.pt   # Resume from checkpoint
    python train_ml_agent.py --phase 2                # Start at phase 2

3-Phase Curriculum:
    Phase 1 (0-500):    2-player PPO vs TobiBot
    Phase 2 (500-1500): 3-player PPO vs TobiBot + self-play copy
    Phase 3 (1500+):    Mix of 2p and 3p self-play
"""

import argparse
import copy
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Add project root to path so we can import game modules
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

from game_state import GameState
from game_engine import GameEngine
from agents import Agent, create_agent, filter_wasteful_moves
from ml.ml_agent import (
    PPOAgent, ChassePatatePolicyNetwork,
    encode_state, encode_moves, encode_move,
    STATE_DIM, MOVE_DIM,
)


# ── Transition storage ────────────────────────────────────────────────────────

@dataclass
class Transition:
    state_vec: torch.Tensor       # (STATE_DIM,)
    move_feats: torch.Tensor      # (N, MOVE_DIM) — all valid moves at this step
    action_idx: int               # index into move_feats that was chosen
    log_prob: float
    value: float
    reward: float
    done: bool


# ── Reward helpers ─────────────────────────────────────────────────────────────

SHAPING_COEF = 0.01


def compute_terminal_reward(my_score: int, opponent_scores: List[int]) -> float:
    """Score differential normalised to roughly [-1, 1]."""
    best_opp = max(opponent_scores) if opponent_scores else 0
    return (my_score - best_opp) / 30.0


def compute_step_reward(move_result: dict, track_length: int) -> float:
    """Small intermediate reward for forward progress and scoring."""
    r = 0.0
    # Points scored this turn (direct game signal)
    r += move_result.get('points_earned', 0) / 30.0
    # Total advancement bonus (all riders in the move)
    total_adv = move_result.get('total_advancement', move_result.get('movement', 0))
    r += SHAPING_COEF * (total_adv / max(track_length, 1))
    # Hand size delta bonus (cards gained minus cards spent)
    hand_before = move_result.get('hand_size_before', 0)
    hand_after = move_result.get('hand_size_after', 0)
    if hand_before or hand_after:
        r += SHAPING_COEF * ((hand_after - hand_before) / 10.0)
    return r


def compute_round_reward(round_results: list, track_length: int) -> float:
    """Per-round intermediate reward (intentionally zero — step rewards cover this)."""
    return 0.0


# ── GAE ────────────────────────────────────────────────────────────────────────

def compute_gae(rewards: List[float], values: List[float],
                dones: List[bool], gamma: float = 0.99,
                lam: float = 0.95):
    """Generalised Advantage Estimation."""
    advantages = []
    gae = 0.0
    next_value = 0.0

    for t in reversed(range(len(rewards))):
        if dones[t]:
            next_value = 0.0
            gae = 0.0
        delta = rewards[t] + gamma * next_value - values[t]
        gae = delta + gamma * lam * gae
        advantages.insert(0, gae)
        next_value = values[t]

    returns = [adv + val for adv, val in zip(advantages, values)]
    return advantages, returns


# ── Trajectory collection ─────────────────────────────────────────────────────

def collect_trajectory(network: ChassePatatePolicyNetwork,
                       rl_player_id: int,
                       opponent_agents: List[Agent],
                       num_players: int) -> List[Transition]:
    """Play one full game and collect transitions for the RL agent."""
    state = GameState(num_players)
    engine = GameEngine(state)

    # Build agent list with RL agent at rl_player_id
    all_agents: List[Optional[Agent]] = [None] * num_players
    opp_idx = 0
    for pid in range(num_players):
        if pid == rl_player_id:
            all_agents[pid] = None  # handled inline
        else:
            all_agents[pid] = opponent_agents[opp_idx]
            all_agents[pid].player_id = pid
            opp_idx += 1

    transitions: List[Transition] = []
    max_rounds = 150

    while not state.game_over and state.current_round < max_rounds:
        state.start_new_round()
        round_move_results: list = []  # RL agent's move results this round

        while True:
            turn_info = state.determine_next_turn()
            if turn_info is None:
                break

            current_player, eligible_riders = turn_info
            pid = current_player.player_id
            acted_position = eligible_riders[0].position

            if pid == rl_player_id:
                # ── RL agent's turn ─────────────────────────────────
                valid_moves = engine.get_valid_moves(current_player, eligible_riders)
                if not valid_moves:
                    state.mark_riders_moved(eligible_riders, acted_position)
                    if state.check_game_over():
                        break
                    continue

                valid_moves = filter_wasteful_moves(valid_moves, engine)
                state_vec = encode_state(engine, current_player)
                move_feats = encode_moves(engine, current_player, valid_moves)

                with torch.no_grad():
                    logits, value = network(state_vec, move_feats)

                dist = Categorical(logits=logits)
                action_idx = dist.sample()
                log_prob = dist.log_prob(action_idx)

                move = valid_moves[action_idx.item()]
                move_result = engine.execute_move(move)

                step_reward = compute_step_reward(move_result, state.track_length)
                round_move_results.append(move_result)

                transitions.append(Transition(
                    state_vec=state_vec,
                    move_feats=move_feats,
                    action_idx=action_idx.item(),
                    log_prob=log_prob.item(),
                    value=value.item(),
                    reward=step_reward,
                    done=False,
                ))

                moved_riders = [move.rider] + (move.drafting_riders or [])
                state.mark_riders_moved(moved_riders, acted_position)
            else:
                # ── Opponent agent's turn ───────────────────────────
                agent = all_agents[pid]
                move = agent.choose_move(engine, current_player, eligible_riders)
                if move is None:
                    state.mark_riders_moved(eligible_riders, acted_position)
                    if state.check_game_over():
                        break
                    continue
                engine.execute_move(move)
                moved_riders = [move.rider] + (move.drafting_riders or [])
                state.mark_riders_moved(moved_riders, acted_position)

            if state.check_game_over():
                break

        # Add per-round reward to the last RL transition this round
        if round_move_results and transitions:
            round_r = compute_round_reward(round_move_results, state.track_length)
            last = transitions[-1]
            transitions[-1] = Transition(
                state_vec=last.state_vec,
                move_feats=last.move_feats,
                action_idx=last.action_idx,
                log_prob=last.log_prob,
                value=last.value,
                reward=last.reward + round_r,
                done=last.done,
            )

    # Handle round-limit
    if not state.game_over:
        state.check_game_over()
        if not state.game_over:
            state.game_over = True

    # Add terminal reward
    if transitions:
        my_score = state.players[rl_player_id].points
        opp_scores = [state.players[p].points for p in range(num_players)
                      if p != rl_player_id]
        terminal_r = compute_terminal_reward(my_score, opp_scores)
        last = transitions[-1]
        transitions[-1] = Transition(
            state_vec=last.state_vec,
            move_feats=last.move_feats,
            action_idx=last.action_idx,
            log_prob=last.log_prob,
            value=last.value,
            reward=last.reward + terminal_r,
            done=True,
        )

    return transitions


# ── PPO update ─────────────────────────────────────────────────────────────────

def ppo_update(network: ChassePatatePolicyNetwork,
               optimizer: torch.optim.Optimizer,
               all_transitions: List[Transition],
               clip_epsilon: float = 0.2,
               entropy_coef: float = 0.03,
               value_loss_coef: float = 0.5,
               n_epochs: int = 4,
               max_grad_norm: float = 0.5,
               gamma: float = 0.99,
               gae_lambda: float = 0.95,
               minibatch_size: int = 64) -> dict:
    """Run PPO update over collected transitions using minibatches."""
    if not all_transitions:
        return {'policy_loss': 0, 'value_loss': 0, 'entropy': 0}

    rewards = [t.reward for t in all_transitions]
    values = [t.value for t in all_transitions]
    dones = [t.done for t in all_transitions]

    advantages, returns = compute_gae(rewards, values, dones, gamma, gae_lambda)

    adv_t = torch.tensor(advantages, dtype=torch.float32)
    adv_t = (adv_t - adv_t.mean()) / (adv_t.std() + 1e-8)
    ret_t = torch.tensor(returns, dtype=torch.float32)
    old_log_probs = torch.tensor([t.log_prob for t in all_transitions],
                                  dtype=torch.float32)

    total_policy_loss = 0.0
    total_value_loss = 0.0
    total_entropy = 0.0
    n_updates = 0
    n_transitions = len(all_transitions)

    for _epoch in range(n_epochs):
        indices = torch.randperm(n_transitions)

        for batch_start in range(0, n_transitions, minibatch_size):
            batch_idx = indices[batch_start:batch_start + minibatch_size]

            # Accumulate losses over the minibatch
            batch_policy_loss = torch.tensor(0.0)
            batch_value_loss = torch.tensor(0.0)
            batch_entropy = torch.tensor(0.0)

            for i in batch_idx:
                i = i.item()
                t = all_transitions[i]

                logits, value_new = network(t.state_vec, t.move_feats)
                dist = Categorical(logits=logits)
                log_prob_new = dist.log_prob(torch.tensor(t.action_idx))
                entropy = dist.entropy()

                ratio = torch.exp(log_prob_new - old_log_probs[i])
                surr1 = ratio * adv_t[i]
                surr2 = torch.clamp(ratio, 1 - clip_epsilon, 1 + clip_epsilon) * adv_t[i]
                policy_loss = -torch.min(surr1, surr2)

                value_loss = F.mse_loss(value_new, ret_t[i].unsqueeze(0)
                                        if value_new.dim() > 0 else ret_t[i])

                batch_policy_loss = batch_policy_loss + policy_loss
                batch_value_loss = batch_value_loss + value_loss
                batch_entropy = batch_entropy + entropy

            batch_size = len(batch_idx)
            batch_policy_loss = batch_policy_loss / batch_size
            batch_value_loss = batch_value_loss / batch_size
            batch_entropy = batch_entropy / batch_size

            loss = (batch_policy_loss
                    + value_loss_coef * batch_value_loss
                    - entropy_coef * batch_entropy)

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(network.parameters(), max_grad_norm)
            optimizer.step()

            total_policy_loss += batch_policy_loss.item()
            total_value_loss += batch_value_loss.item()
            total_entropy += batch_entropy.item()
            n_updates += 1

    n = max(n_updates, 1)
    return {
        'policy_loss': total_policy_loss / n,
        'value_loss': total_value_loss / n,
        'entropy': total_entropy / n,
    }


# ── Evaluation ─────────────────────────────────────────────────────────────────

def evaluate(network: ChassePatatePolicyNetwork,
             opponent_type: str = 'tobibot',
             n_games: int = 20,
             num_players: int = 2) -> dict:
    """Evaluate current network against a heuristic bot."""
    wins = 0
    total_score_diff = 0.0

    for game_num in range(n_games):
        state = GameState(num_players)
        engine = GameEngine(state)

        rl_pid = game_num % num_players  # alternate position
        agents = {}
        opp_idx = 0
        for pid in range(num_players):
            if pid != rl_pid:
                agents[pid] = create_agent(opponent_type, pid)
                opp_idx += 1

        max_rounds = 150
        while not state.game_over and state.current_round < max_rounds:
            state.start_new_round()
            while True:
                turn_info = state.determine_next_turn()
                if turn_info is None:
                    break
                current_player, eligible_riders = turn_info
                pid = current_player.player_id
                acted_position = eligible_riders[0].position

                if pid == rl_pid:
                    valid_moves = engine.get_valid_moves(current_player, eligible_riders)
                    if not valid_moves:
                        state.mark_riders_moved(eligible_riders, acted_position)
                        if state.check_game_over():
                            break
                        continue
                    valid_moves = filter_wasteful_moves(valid_moves, engine)
                    state_vec = encode_state(engine, current_player)
                    move_feats = encode_moves(engine, current_player, valid_moves)
                    with torch.no_grad():
                        logits, _ = network(state_vec, move_feats)
                    move = valid_moves[logits.argmax().item()]
                else:
                    move = agents[pid].choose_move(engine, current_player, eligible_riders)
                    if move is None:
                        state.mark_riders_moved(eligible_riders, acted_position)
                        if state.check_game_over():
                            break
                        continue

                engine.execute_move(move)
                moved_riders = [move.rider] + (move.drafting_riders or [])
                state.mark_riders_moved(moved_riders, acted_position)
                if state.check_game_over():
                    break

        if not state.game_over:
            state.game_over = True

        my_score = state.players[rl_pid].points
        opp_scores = [state.players[p].points for p in range(num_players)
                      if p != rl_pid]
        best_opp = max(opp_scores) if opp_scores else 0
        if my_score > best_opp:
            wins += 1
        total_score_diff += (my_score - best_opp)

    return {
        'win_rate': wins / max(n_games, 1),
        'avg_score_diff': total_score_diff / max(n_games, 1),
        'games': n_games,
    }


# ── Phase management ──────────────────────────────────────────────────────────

def get_opponents_for_phase(phase: int, iteration: int,
                            old_network: Optional[ChassePatatePolicyNetwork],
                            num_players_out: list,
                            phase1_end: int = 500,
                            phase2_end: int = 1500) -> List[Agent]:
    """Return opponent agents and set num_players for current phase/iteration."""
    if phase == 1 or (phase == 0 and iteration < phase1_end):
        # Phase 1: 2-player, PPO vs TobiBot
        num_players_out.append(2)
        return [create_agent('tobibot', 1)]

    elif phase == 2 or (phase == 0 and iteration < phase2_end):
        # Phase 2: 3-player, PPO vs TobiBot + self-play copy
        num_players_out.append(3)
        opponents = [create_agent('tobibot', 1)]
        if old_network is not None:
            opponents.append(PPOAgent(2, network=copy.deepcopy(old_network)))
        else:
            opponents.append(create_agent('tobibot', 2))
        return opponents

    else:
        # Phase 3: mix of 2p and 3p self-play
        import random
        if random.random() < 0.5:
            # 2-player self-play
            num_players_out.append(2)
            if old_network is not None:
                return [PPOAgent(1, network=copy.deepcopy(old_network))]
            return [create_agent('tobibot', 1)]
        else:
            # 3-player self-play
            num_players_out.append(3)
            opponents = []
            if old_network is not None:
                opponents.append(PPOAgent(1, network=copy.deepcopy(old_network)))
                opponents.append(PPOAgent(2, network=copy.deepcopy(old_network)))
            else:
                opponents.append(create_agent('tobibot', 1))
                opponents.append(create_agent('tobibot', 2))
            return opponents


# ── Main training loop ─────────────────────────────────────────────────────────

def train(total_iterations: int = 2500,
          games_per_update: int = 16,
          start_phase: int = 0,
          resume_path: str = None,
          checkpoint_dir: str = None,
          eval_interval: int = 50,
          save_interval: int = 100,
          lr: float = 3e-4,
          phase1_end: int = 500,
          phase2_end: int = 1500):
    """Main PPO training loop with 3-phase curriculum."""
    _ml_dir = Path(__file__).resolve().parent
    if checkpoint_dir is None:
        checkpoint_dir = str(_ml_dir / 'checkpoints')
    Path(checkpoint_dir).mkdir(exist_ok=True)

    network = ChassePatatePolicyNetwork()
    optimizer = torch.optim.Adam(network.parameters(), lr=lr)
    start_iter = 0

    if resume_path and Path(resume_path).exists():
        checkpoint = torch.load(resume_path, map_location='cpu', weights_only=False)
        network.load_state_dict(checkpoint['network'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        start_iter = checkpoint.get('iteration', 0)
        print(f"Resumed from {resume_path} at iteration {start_iter}")

    # Keep a snapshot for self-play opponents
    old_network: Optional[ChassePatatePolicyNetwork] = None

    print(f"\n{'='*60}")
    print(f"PPO Training — {total_iterations} iterations, {games_per_update} games/update")
    print(f"Starting at iteration {start_iter}, phase {start_phase or 'auto'}")
    print(f"{'='*60}\n")

    for iteration in range(start_iter, start_iter + total_iterations):
        t0 = time.time()
        network.train()

        # Determine phase
        if start_phase > 0:
            phase = start_phase
        else:
            phase = 0  # auto: get_opponents_for_phase handles thresholds

        # Collect trajectories
        all_transitions: List[Transition] = []
        game_rewards = []

        for game_num in range(games_per_update):
            num_players_list: list = []
            opponents = get_opponents_for_phase(
                phase, iteration, old_network, num_players_list,
                phase1_end=phase1_end, phase2_end=phase2_end
            )
            num_players = num_players_list[0]

            rl_player_id = game_num % num_players
            transitions = collect_trajectory(
                network, rl_player_id, opponents, num_players
            )
            all_transitions.extend(transitions)

            if transitions:
                game_rewards.append(sum(t.reward for t in transitions))

        # PPO update
        stats = ppo_update(network, optimizer, all_transitions)
        elapsed = time.time() - t0

        avg_reward = sum(game_rewards) / max(len(game_rewards), 1)
        current_phase = 1 if iteration < phase1_end else (2 if iteration < phase2_end else 3)

        print(f"[Iter {iteration:5d}] phase={current_phase} "
              f"transitions={len(all_transitions):5d} "
              f"avg_reward={avg_reward:+.3f} "
              f"p_loss={stats['policy_loss']:.4f} "
              f"v_loss={stats['value_loss']:.4f} "
              f"entropy={stats['entropy']:.3f} "
              f"({elapsed:.1f}s)")

        # Snapshot for self-play (update every 100 iterations)
        if iteration > 0 and iteration % 100 == 0:
            old_network = copy.deepcopy(network)
            old_network.eval()

        # Evaluation
        if iteration % eval_interval == 0:
            network.eval()
            eval_result = evaluate(network, 'tobibot', n_games=100)
            print(f"  ► EVAL vs TobiBot: win_rate={eval_result['win_rate']:.1%} "
                  f"avg_score_diff={eval_result['avg_score_diff']:+.1f}")

        # Save checkpoint
        if iteration % save_interval == 0:
            ckpt_path = Path(checkpoint_dir) / f'ml_agent_iter_{iteration}.pt'
            torch.save({
                'network': network.state_dict(),
                'optimizer': optimizer.state_dict(),
                'iteration': iteration,
            }, ckpt_path)

    # Save resumable checkpoint to checkpoints directory
    final_iter = start_iter + total_iterations
    ckpt_path = Path(checkpoint_dir) / f'ml_agent_iter_{final_iter}.pt'
    torch.save({
        'network': network.state_dict(),
        'optimizer': optimizer.state_dict(),
        'iteration': final_iter,
    }, ckpt_path)
    print(f"\nResumable checkpoint saved to {ckpt_path}")

    # Save weights-only for PPOAgent inference
    weights_path = _ml_dir / 'ml_agent_checkpoint.pt'
    torch.save(network.state_dict(), weights_path)
    print(f"Inference weights saved to {weights_path}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Train PPO agent for Chasse Patate')
    parser.add_argument('--iterations', type=int, default=2500,
                        help='Total training iterations (default: 2500)')
    parser.add_argument('--games-per-update', type=int, default=16,
                        help='Games per PPO update (default: 16)')
    parser.add_argument('--resume', type=str, default=None,
                        help='Path to checkpoint to resume from')
    parser.add_argument('--phase', type=int, default=0, choices=[0, 1, 2, 3],
                        help='Force a specific phase (0=auto)')
    parser.add_argument('--eval-interval', type=int, default=50,
                        help='Evaluate every N iterations (default: 50)')
    parser.add_argument('--save-interval', type=int, default=100,
                        help='Save checkpoint every N iterations (default: 100)')
    parser.add_argument('--lr', type=float, default=3e-4,
                        help='Learning rate (default: 3e-4)')
    parser.add_argument('--phase1-end', type=int, default=500,
                        help='Iteration where phase 1 ends (default: 500)')
    parser.add_argument('--phase2-end', type=int, default=1500,
                        help='Iteration where phase 2 ends (default: 1500)')
    args = parser.parse_args()

    train(
        total_iterations=args.iterations,
        games_per_update=args.games_per_update,
        start_phase=args.phase,
        resume_path=args.resume,
        eval_interval=args.eval_interval,
        save_interval=args.save_interval,
        lr=args.lr,
        phase1_end=args.phase1_end,
        phase2_end=args.phase2_end,
    )


if __name__ == '__main__':
    main()
