"""
Chasse Patate - Analysis Tools
Analyze simulation results to identify balance issues
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
import matplotlib.pyplot as plt
from collections import defaultdict


class GameAnalyzer:
    """Analyze game simulation results"""
    
    def __init__(self, log_dir: str = "game_logs"):
        self.log_dir = Path(log_dir)
    
    def load_game_logs(self, game_ids: List[int] = None) -> List[Dict]:
        """Load game logs from files"""
        logs = []
        
        if game_ids is None:
            # Load all games
            game_files = sorted(self.log_dir.glob("game_*.json"))
        else:
            game_files = [self.log_dir / f"game_{gid}.json" for gid in game_ids]
        
        for game_file in game_files:
            if game_file.exists():
                with open(game_file, 'r') as f:
                    logs.append(json.load(f))
        
        return logs
    
    def analyze_win_rates(self, logs: List[Dict]) -> pd.DataFrame:
        """Calculate win rates by agent type"""
        
        agent_stats = defaultdict(lambda: {'games': 0, 'wins': 0, 
                                           'total_score': 0, 'positions': []})
        
        for log in logs:
            # Get final scores
            final_scores = log['final_result']['final_scores']
            winner = log['final_result']['winner']
            
            # Extract scores and determine positions
            player_scores = [(name, score) for name, score in final_scores.items()]
            player_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Update statistics for each agent
            for agent_info in log['agents']:
                player_name = f"Player {agent_info['player_id']}"
                agent_type = agent_info['type']
                
                score = final_scores.get(player_name, 0)
                position = next(i for i, (name, _) in enumerate(player_scores) 
                               if name == player_name) + 1
                
                agent_stats[agent_type]['games'] += 1
                agent_stats[agent_type]['total_score'] += score
                agent_stats[agent_type]['positions'].append(position)
                
                if winner == player_name:
                    agent_stats[agent_type]['wins'] += 1
        
        # Create DataFrame
        results = []
        for agent_type, stats in agent_stats.items():
            results.append({
                'agent_type': agent_type,
                'games_played': stats['games'],
                'wins': stats['wins'],
                'win_rate': stats['wins'] / stats['games'] if stats['games'] > 0 else 0,
                'avg_score': stats['total_score'] / stats['games'] if stats['games'] > 0 else 0,
                'avg_position': np.mean(stats['positions']) if stats['positions'] else 0
            })
        
        df = pd.DataFrame(results)
        df = df.sort_values('win_rate', ascending=False)
        
        return df
    
    def analyze_game_length(self, logs: List[Dict]) -> Dict:
        """Analyze game length statistics"""
        
        turn_counts = [len(log['move_history']) for log in logs]
        
        return {
            'mean_turns': np.mean(turn_counts),
            'median_turns': np.median(turn_counts),
            'min_turns': min(turn_counts),
            'max_turns': max(turn_counts),
            'std_turns': np.std(turn_counts)
        }
    
    def analyze_card_usage(self, logs: List[Dict]) -> pd.DataFrame:
        """Analyze which card types are used most"""
        
        card_usage = defaultdict(int)
        action_usage = defaultdict(int)
        total_moves = 0
        
        for log in logs:
            for turn in log['move_history']:
                if turn['move']['success']:
                    # Count actions
                    action = turn['move'].get('action', 'unknown')
                    action_usage[action] += 1
                    
                    # Count cards (new system uses 'cards_played' list)
                    cards_played = turn['move'].get('cards_played', [])
                    for card in cards_played:
                        card_usage[card] += 1
                    
                    total_moves += 1
        
        # Build results dataframe
        results = []
        for card_type, count in card_usage.items():
            results.append({
                'card_type': card_type,
                'times_played': count,
                'usage_rate': count / total_moves if total_moves > 0 else 0
            })
        
        # If no cards found (old logs), return empty dataframe
        if not results:
            return pd.DataFrame(columns=['card_type', 'times_played', 'usage_rate'])
        
        return pd.DataFrame(results).sort_values('usage_rate', ascending=False)
    
    
    def analyze_score_distribution(self, logs: List[Dict]) -> Dict:
        """Analyze score distributions"""
        
        all_scores = []
        winning_scores = []
        
        for log in logs:
            scores = list(log['final_result']['final_scores'].values())
            all_scores.extend(scores)
            winning_scores.append(max(scores))
        
        return {
            'mean_score': np.mean(all_scores),
            'median_score': np.median(all_scores),
            'std_score': np.std(all_scores),
            'mean_winning_score': np.mean(winning_scores),
            'score_range': (min(all_scores), max(all_scores))
        }
    
    def detect_dominant_strategies(self, logs: List[Dict], 
                                   significance_threshold: float = 0.15) -> List[str]:
        """Detect potentially dominant strategies"""
        
        win_rates = self.analyze_win_rates(logs)
        
        # Find agents that win significantly more than expected
        expected_win_rate = 1.0 / len(win_rates)
        dominant = []
        
        for _, row in win_rates.iterrows():
            if row['win_rate'] > expected_win_rate + significance_threshold:
                dominant.append({
                    'agent': row['agent_type'],
                    'win_rate': row['win_rate'],
                    'expected': expected_win_rate,
                    'advantage': row['win_rate'] - expected_win_rate
                })
        
        return dominant
    
    def generate_report(self, logs: List[Dict], output_file: str = "analysis_report.txt"):
        """Generate comprehensive analysis report"""
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("CHASSE PATATE - GAME BALANCE ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"\nTotal games analyzed: {len(logs)}\n")
        
        # Win rates
        report_lines.append("-" * 80)
        report_lines.append("WIN RATES BY AGENT TYPE")
        report_lines.append("-" * 80)
        win_rates = self.analyze_win_rates(logs)
        report_lines.append(win_rates.to_string())
        report_lines.append("")
        
        # Game length
        report_lines.append("-" * 80)
        report_lines.append("GAME LENGTH STATISTICS")
        report_lines.append("-" * 80)
        length_stats = self.analyze_game_length(logs)
        for key, value in length_stats.items():
            report_lines.append(f"{key}: {value:.2f}")
        report_lines.append("")
        
        # Card usage
        report_lines.append("-" * 80)
        report_lines.append("CARD USAGE STATISTICS")
        report_lines.append("-" * 80)
        card_usage = self.analyze_card_usage(logs)
        report_lines.append(card_usage.to_string())
        report_lines.append("")
        
        # Score distribution
        report_lines.append("-" * 80)
        report_lines.append("SCORE DISTRIBUTION")
        report_lines.append("-" * 80)
        scores = self.analyze_score_distribution(logs)
        for key, value in scores.items():
            report_lines.append(f"{key}: {value}")
        report_lines.append("")
        
        # Dominant strategies
        report_lines.append("-" * 80)
        report_lines.append("POTENTIAL DOMINANT STRATEGIES")
        report_lines.append("-" * 80)
        dominant = self.detect_dominant_strategies(logs)
        if dominant:
            for strat in dominant:
                report_lines.append(f"\n{strat['agent']}:")
                report_lines.append(f"  Win rate: {strat['win_rate']:.2%}")
                report_lines.append(f"  Expected: {strat['expected']:.2%}")
                report_lines.append(f"  Advantage: +{strat['advantage']:.2%}")
        else:
            report_lines.append("No dominant strategies detected!")
        
        report_lines.append("\n" + "=" * 80)
        
        # Write to file
        report_path = self.log_dir / output_file
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        # Also print to console
        print('\n'.join(report_lines))
        
        return report_path
    
    def plot_win_rates(self, logs: List[Dict], output_file: str = "win_rates.png"):
        """Create visualization of win rates"""
        
        win_rates = self.analyze_win_rates(logs)
        
        plt.figure(figsize=(12, 6))
        plt.bar(win_rates['agent_type'], win_rates['win_rate'])
        plt.axhline(y=1.0/len(win_rates), color='r', linestyle='--', 
                   label='Expected (random)')
        plt.xlabel('Agent Type')
        plt.ylabel('Win Rate')
        plt.title('Win Rates by Agent Type')
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        
        output_path = self.log_dir / output_file
        plt.savefig(output_path)
        plt.close()
        
        return output_path