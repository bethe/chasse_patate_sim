# ML Agent Development Notes

## Overview

PPO (Proximal Policy Optimization) agent that learns to play Chasse Patate by playing thousands of games against heuristic bots and itself. The goal is to optimize for having more points than opponents (score differential).

## Architecture

### State Features (580-dim vector)

| Block | Dims | Description |
|---|---|---|
| Own riders (3 x 7) | 21 | Position (normalized), finished flag, terrain one-hot (4), terrain-limited flag |
| Full track terrain (100 x 4) | 400 | Static one-hot encoding of entire track, zero-padded to 100 fields |
| Per-rider lookahead (3 x 10 x 4) | 120 | Next 10 fields of terrain ahead of each rider |
| Hand composition | 4 | Count of each card type (Energy/Rouleur/Sprinter/Climber), normalized by /10 |
| Scores (self + 3 opponents) | 4 | Points normalized by /30, zero-padded for absent opponents |
| Opponent riders (3 x 3 x 2) | 18 | Position + finished flag for each opponent's riders |
| Opponent finished counts | 3 | Per-opponent count of finished riders, /3 |
| Opponent hand sizes | 3 | Card count per opponent, /15 |
| Last move info | 5 | Exists flag, is_pull, is_draft, movement/10, old_position normalized |
| El Patron flag | 1 | Whether current player is El Patron |
| Deck pressure | 1 | Cards remaining in deck, /90 |

All values normalized to roughly [0, 1] range for stable training.

### Move Features (22-dim per move)

- Action type one-hot (6): Pull, Attack, Draft, TeamPull, TeamDraft, TeamCar
- Primary rider one-hot (3): Rouleur, Sprinter, Climber
- Movement metrics (5): base/actual movement, total advancement, rider count, cards used
- Card economy (2): cards remaining after, efficiency (advancement per card)
- Terrain context (4): terrain-limited, rider matches terrain, hits sprint, hits finish
- Position context (2): opponent at destination, teammate at destination

### Neural Network (Actor-Critic)

```
State encoder:  580 -> 256 (LayerNorm+ReLU) -> 256 (LayerNorm+ReLU) -> 128 (ReLU)
Move scorer:    [128 state_emb | 22 move_feats] -> 256 (ReLU) -> 128 (ReLU) -> 1
Value head:     128 -> 128 (ReLU) -> 1
```

The network scores each valid move individually (state embedding + move features -> scalar score), then softmax over scores to pick an action. This handles the variable-size action space (50-200+ valid moves per turn).

- **Actor**: Picks which move to play (samples during training, argmax during inference)
- **Critic**: Estimates "how good is this game state?" — only used during training to compute advantages (was this move better or worse than expected?)

## Reward Design

- **Terminal**: `(my_score - best_opponent_score) / 30.0` — score differential, roughly [-1, 1]
- **Intermediate** (per turn, small coefficient 0.01):
  - Points scored this turn (sprint/finish crossing) / 30
  - Movement bonus: `0.01 * (movement / track_length)`
  - Card draw bonus: `0.01 * (cards_drawn / 10)`

Intermediate rewards accelerate learning by providing turn-by-turn feedback instead of only at game end. They're kept small so they don't distort the main objective.

## Training

### PPO Hyperparameters

- clip_epsilon=0.2, gamma=0.99, gae_lambda=0.95
- lr=3e-4 (Adam), entropy_coef=0.01, value_loss_coef=0.5
- 16 games per update, 4 PPO epochs per batch
- max_grad_norm=0.5

### 3-Phase Curriculum

| Phase | Iterations | Setup | Why |
|---|---|---|---|
| 1 | 0-500 | 2-player: PPO vs TobiBot | Learn basics from strong heuristic bot |
| 2 | 500-1500 | 3-player: PPO vs TobiBot + self-play copy | Multi-player dynamics, push beyond heuristic ceiling |
| 3 | 1500+ | Mix of 2p and 3p self-play | Discover novel strategies |

### When to Transition to Self-Play

- **< 20% win rate vs TobiBot**: Still learning basics, stay on Phase 1
- **30-40%**: Good threshold to start self-play (Phase 2)
- **40-50%+**: Already competitive, self-play will push beyond TobiBot's ceiling

Note: 50% vs TobiBot is very strong — TobiBot has ~97% win rate vs most other bots.

### Running

```bash
# Phase 1 only (~30 min)
python3 ml/train_ml_agent.py --iterations 500

# Full curriculum (~2-3 hours)
python3 ml/train_ml_agent.py

# Resume training
python3 ml/train_ml_agent.py --resume ml/ml_agent_checkpoint.pt --iterations 1000

# Force a specific phase
python3 ml/train_ml_agent.py --phase 1 --iterations 1000
```

Checkpoints save to `ml/checkpoints/` every 100 iterations. Final weights go to `ml/ml_agent_checkpoint.pt`.

### Using the Trained Agent

```python
from agents import create_agent
agent = create_agent('ppo', player_id=0)  # loads ml/ml_agent_checkpoint.pt
```

Works with all existing scripts (quick_test.py, run_tournament.py, simulator, etc).

## Design Decisions

- **Move scoring (not fixed output head)**: Action space is combinatorial and varies each turn. Network scores each valid move's features individually, then softmax to select.
- **LayerNorm in state encoder**: Features have different scales; LayerNorm stabilizes training better than BatchNorm with small PPO batch sizes.
- **filter_wasteful_moves()**: Applied before the network sees moves — no point learning to avoid obvious bad moves (0-advancement card plays). Domain knowledge as action filter.
- **Position alternation**: RL agent alternates player_id each game during training to avoid position bias (El Patron advantage).
- **Lazy import in agents.py**: `create_agent('ppo', ...)` uses lazy import so torch isn't required unless the PPO agent is actually used.

## Files

| File | Purpose |
|---|---|
| `ml/ml_agent.py` | PPOAgent class, neural network, state/move encoders |
| `ml/train_ml_agent.py` | Training loop, trajectory collection, PPO updates, curriculum |
| `ml/__init__.py` | Package marker |
| `ml/ml_agent_checkpoint.pt` | Trained weights (created after training) |
| `ml/checkpoints/` | Periodic checkpoints during training |
