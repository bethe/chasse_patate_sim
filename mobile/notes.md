# Mobile App Notes

## Requirements

- Human players vs bots (heuristic and PPO ML agent)
- Human vs human (pass-and-play or eventually networked multiplayer)
- JSON game logging (same format as existing simulator)
- Multiplayer is a future possibility, not immediate

## Recommended Architecture

**React Native (Expo) + TypeScript monorepo**, designed to accommodate multiplayer later.

```
packages/
  game-core/    # TS port of game_state + game_engine + agents (shared)
  mobile/       # React Native / Expo app
  server/       # Node.js server (future multiplayer)
```

- Bot-only phase: mobile imports game-core directly, runs fully offline on-device
- Multiplayer phase: server imports the same game-core as the authoritative engine, mobile becomes a thin client
- Single game engine implementation, shared types throughout

## What Needs Porting (game-core)

| Python file | Effort | Notes |
|---|---|---|
| `game_state.py` | Low | Dataclasses → TS interfaces/classes, enums → TS enums |
| `game_engine.py` | Medium | Pure logic, no library dependencies |
| `agents.py` (heuristics) | Medium | Scoring math, mechanical port |
| `config.json` | Trivial | Load as-is |

pandas / numpy / matplotlib are only used in analysis scripts — not needed for the playable app.

## PPO Agent: ONNX Export

Train in Python, export once, bundle in app:

```python
torch.onnx.export(agent.network, (dummy_state, dummy_moves), "ml_agent.onnx")
```

Use `onnxruntime-react-native` in the app to run inference. The main porting work is re-implementing `encode_state()` and `encode_move()` from `ml/ml_agent.py` in TypeScript (array-packing logic, no math libraries needed).

## Adding New Agents Later

| Agent type | Adding to mobile |
|---|---|
| New ML model (same architecture) | Easy — swap .onnx file |
| New ML model (changed encoding) | Medium — update TS encoder to match |
| New heuristic agent | Manual port each time, ~half a day + testing |

**Mitigation:** maintain a shared scenario test suite — fixed game states where each agent must pick the same move in both Python and TS. Catches divergences immediately.

## Alternative: Python Server (if heuristic iteration continues heavily)

If new heuristic agents are developed frequently, consider running bots server-side in Python permanently:

```
[React Native] <---> [FastAPI/WebSocket server] <--> [Python game engine]
```

- Bots always live in Python, no porting ever needed
- New agents available in mobile immediately
- Requires connectivity (no offline bot play)
- For local/LAN play: server runs on a laptop at game night
- For online: deploy on Railway / Fly.io

This approach makes more sense if the Python simulation and ML pipeline are still actively evolving.

## Suggested Build Order

1. Port `game_state.py` + `game_engine.py` to TypeScript — headless game working
2. Add heuristic agents (TobiBot as the strongest baseline)
3. Build mobile UI in Expo
4. When PPO training is complete: ONNX export + wire up TS state/move encoders
5. (Future) Add Node.js server using game-core for multiplayer
