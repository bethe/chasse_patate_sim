"""
Chasse Patate - Game Simulator
Runs games and logs detailed statistics
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from game_state import GameState
from game_engine import GameEngine
from agents import Agent, create_agent


class GameLogger:
    """Logs detailed game information"""
    
    def __init__(self, log_dir: str = "game_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.current_game_log = []
        self.move_history = []
    
    def start_game(self, game_id: int, agents: List[Agent], num_players: int):
        """Initialize logging for a new game"""
        self.current_game_log = []
        self.move_history = []
        
        self.game_info = {
            'game_id': game_id,
            'timestamp': datetime.now().isoformat(),
            'num_players': num_players,
            'agents': [{'player_id': a.player_id, 'type': a.name} for a in agents]
        }
    
    def log_turn(self, turn_num: int, player_id: int, move_result: dict, 
                 game_state: dict):
        """Log a single turn"""
        turn_data = {
            'turn': turn_num,
            'player': player_id,
            'move': move_result,
            'state': game_state
        }
        self.move_history.append(turn_data)
    
    def end_game(self, final_result: dict):
        """Finalize and save game log"""
        self.game_info['final_result'] = final_result
        self.game_info['move_history'] = self.move_history
        
        # Save detailed JSON log
        game_file = self.log_dir / f"game_{self.game_info['game_id']}.json"
        with open(game_file, 'w') as f:
            json.dump(self.game_info, f, indent=2)
        
        return self.game_info
    
    def save_summary_csv(self, summary_data: List[Dict], filename: str = "game_summary.csv"):
        """Save summary statistics to CSV"""
        csv_file = self.log_dir / filename
        
        if not summary_data:
            return
        
        keys = summary_data[0].keys()
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(summary_data)


class GameSimulator:
    """Simulates multiple games for testing"""
    
    def __init__(self, num_players: int = 2, track_length: int = 50,
                 log_dir: str = "game_logs", verbose: bool = False):
        self.num_players = num_players
        self.track_length = track_length
        self.verbose = verbose
        self.logger = GameLogger(log_dir)
        
        self.simulation_results = []
    
    def run_game(self, agents: List[Agent], game_id: int = 0) -> Dict:
        """Run a single game with specified agents"""
        
        # Initialize game
        state = GameState(self.num_players, self.track_length)
        engine = GameEngine(state)
        
        # Assign agents to players
        for i, agent in enumerate(agents):
            state.players[i].name = str(agent)
        
        # Start logging
        self.logger.start_game(game_id, agents, self.num_players)
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Starting Game {game_id}")
            print(f"Players: {[str(a) for a in agents]}")
            print(f"{'='*60}\n")
        
        # Game loop
        turn_count = 0
        max_turns = 500  # Safety limit
        
        while not state.game_over and turn_count < max_turns:
            current_player = state.get_current_player()
            agent = agents[current_player.player_id]
            
            # Agent chooses move
            move = agent.choose_move(engine, current_player)
            
            if move is None:
                if self.verbose:
                    print(f"Turn {turn_count}: {agent} has no valid moves!")
                state.advance_turn()
                continue
            
            # Execute move
            move_result = engine.execute_move(move)
            
            # Log the turn
            game_summary = state.get_game_summary()
            self.logger.log_turn(turn_count, current_player.player_id, 
                               move_result, game_summary)
            
            if self.verbose:
                print(f"Turn {turn_count}: {agent} - "
                      f"Rider {move.rider.rider_id} "
                      f"moved to position {move.target_position} "
                      f"(card: {move.card.card_type.value}, "
                      f"slipstream: {move.uses_slipstream})")
            
            # Check if game is over
            state.check_game_over()
            
            # Next turn
            state.advance_turn()
            turn_count += 1
        
        # Calculate final results
        final_result = engine.process_end_of_race()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Game {game_id} Complete after {turn_count} turns")
            print(f"Winner: {final_result['winner']} "
                  f"with {final_result['winner_score']} points")
            print(f"Final Scores: {final_result['final_scores']}")
            print(f"{'='*60}\n")
        
        # End logging
        game_log = self.logger.end_game(final_result)
        
        return game_log
    
    def run_tournament(self, agent_types: List[str], 
                      games_per_matchup: int = 10) -> Dict:
        """Run a round-robin tournament with specified agent types"""
        
        print(f"\n{'='*60}")
        print(f"Starting Tournament")
        print(f"Agent types: {agent_types}")
        print(f"Games per matchup: {games_per_matchup}")
        print(f"{'='*60}\n")
        
        results = []
        game_id = 0
        
        # Generate all matchups (for 2-player games)
        matchups = []
        for i, agent1_type in enumerate(agent_types):
            for agent2_type in agent_types[i:]:
                matchups.append((agent1_type, agent2_type))
        
        total_games = len(matchups) * games_per_matchup
        
        for agent1_type, agent2_type in matchups:
            matchup_results = {
                'agent1_type': agent1_type,
                'agent2_type': agent2_type,
                'agent1_wins': 0,
                'agent2_wins': 0,
                'agent1_total_score': 0,
                'agent2_total_score': 0,
                'games_played': 0
            }
            
            for game_num in range(games_per_matchup):
                # Create agents
                agents = [
                    create_agent(agent1_type, 0),
                    create_agent(agent2_type, 1)
                ]
                
                # Run game
                game_log = self.run_game(agents, game_id)
                game_id += 1
                
                # Extract results
                scores = [game_log['final_result']['final_scores'][f'Player {i}'] 
                         for i in range(2)]
                
                matchup_results['agent1_total_score'] += scores[0]
                matchup_results['agent2_total_score'] += scores[1]
                matchup_results['games_played'] += 1
                
                if scores[0] > scores[1]:
                    matchup_results['agent1_wins'] += 1
                elif scores[1] > scores[0]:
                    matchup_results['agent2_wins'] += 1
                
                print(f"Progress: {game_id}/{total_games} games complete")
            
            results.append(matchup_results)
        
        # Save tournament summary
        self.logger.save_summary_csv(results, "tournament_results.csv")
        
        print(f"\n{'='*60}")
        print(f"Tournament Complete!")
        print(f"Total games: {game_id}")
        print(f"Results saved to: {self.logger.log_dir}")
        print(f"{'='*60}\n")
        
        return {
            'matchups': results,
            'total_games': game_id
        }
    
    def run_batch_simulation(self, agent_types: List[str], 
                            num_games: int = 100) -> List[Dict]:
        """Run multiple games with same agent configuration"""
        
        print(f"\n{'='*60}")
        print(f"Running Batch Simulation")
        print(f"Agent configuration: {agent_types}")
        print(f"Number of games: {num_games}")
        print(f"{'='*60}\n")
        
        results = []
        
        for game_id in range(num_games):
            # Create agents
            agents = [create_agent(agent_type, i) 
                     for i, agent_type in enumerate(agent_types)]
            
            # Run game
            game_log = self.run_game(agents, game_id)
            
            # Extract key statistics
            game_result = {
                'game_id': game_id,
                'turns': len(game_log['move_history']),
                'winner_id': int(game_log['final_result']['winner'].split()[-1]),
                'winner_score': game_log['final_result']['winner_score'],
                'scores': [game_log['final_result']['final_scores'][f'Player {i}']
                          for i in range(self.num_players)]
            }
            
            results.append(game_result)
            
            if (game_id + 1) % 10 == 0:
                print(f"Progress: {game_id + 1}/{num_games} games complete")
        
        # Save batch results
        self.logger.save_summary_csv(results, "batch_results.csv")
        
        print(f"\n{'='*60}")
        print(f"Batch Simulation Complete!")
        print(f"Results saved to: {self.logger.log_dir}")
        print(f"{'='*60}\n")
        
        return results
