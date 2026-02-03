# How to Run Comprehensive Analysis

## What Does "analyzer.generate_report(logs)" Mean?

This command generates a **detailed analysis report** that includes:
- Win rates by agent type
- Game length statistics
- Card usage patterns
- Score distribution
- Dominant strategy detection
- Slipstream usage (deprecated)

The report is saved as a text file that you can read.

---

## Three Ways to Run It

### Method 1: Use the Standalone Script (EASIEST)

```bash
python generate_report.py
```

**What it does:**
1. Loads all game logs from `game_logs/` directory
2. Analyzes all the games
3. Generates `analysis_report.txt`
4. Shows you a preview

**When to use:** When you just want a quick report after running games

---

### Method 2: Run from quick_test.py (AUTOMATIC)

The quick_test.py script tells you:
```
For comprehensive analysis, run: analyzer.generate_report(logs)
```

Here's how:

```bash
# First, run quick test to generate games
python quick_test.py

# Then, in Python interactive mode:
python
>>> from analysis import GameAnalyzer
>>> analyzer = GameAnalyzer(log_dir="game_logs")
>>> logs = analyzer.load_game_logs()
>>> analyzer.generate_report(logs)
```

Or create a simple script:

```python
# my_analysis.py
from analysis import GameAnalyzer

analyzer = GameAnalyzer(log_dir="game_logs")
logs = analyzer.load_game_logs()
report_path = analyzer.generate_report(logs)
print(f"Report saved to: {report_path}")
```

Then run: `python my_analysis.py`

---

### Method 3: Add to example_usage.py (FOR CUSTOM ANALYSIS)

Edit `example_usage.py` and uncomment line 180:

```python
# Line 179-181 in example_usage.py
example_tournament()
example_full_analysis()  # ← Uncomment this line
# example_test_specific_matchup()
```

Then run:
```bash
python example_usage.py
```

This will:
1. Run 100 games
2. Generate comprehensive report
3. Create visualizations (plots)

---

## What You Get

### The Report File: `analysis_report.txt`

Located in: `game_logs/analysis_report.txt`

**Example content:**

```
================================================================================
CHASSE PATATE - GAME BALANCE ANALYSIS REPORT
================================================================================

Total games analyzed: 50

--------------------------------------------------------------------------------
WIN RATES BY AGENT TYPE
--------------------------------------------------------------------------------
  agent_type  games_played  wins  win_rate  avg_score  avg_position
    Greedy            50    18      36.0%      14.2         1.4
  Balanced            50    16      32.0%      12.8         1.6
Aggressive            50    16      32.0%      13.1         1.5

--------------------------------------------------------------------------------
GAME LENGTH STATISTICS
--------------------------------------------------------------------------------
mean_turns: 145.2
median_turns: 150.0
min_turns: 120
max_turns: 150
std_turns: 12.4

--------------------------------------------------------------------------------
CARD USAGE STATISTICS
--------------------------------------------------------------------------------
  card_type  times_played  usage_rate
    Energy          2450       42.3%
   Rouleur          1230       21.2%
  Sprinter          1100       19.0%
   Climber          1020       17.5%

--------------------------------------------------------------------------------
SCORE DISTRIBUTION
--------------------------------------------------------------------------------
mean_score: 13.4
median_score: 12.0
mean_winning_score: 18.2
score_range: (5, 32)

--------------------------------------------------------------------------------
POTENTIAL DOMINANT STRATEGIES
--------------------------------------------------------------------------------
⚠️ Greedy appears dominant with 36.0% win rate
```

---

## Step-by-Step Tutorial

### Complete Workflow

```bash
# Step 1: Generate game data
python quick_test.py
# This creates logs in game_logs/ directory

# Step 2: Generate comprehensive report
python generate_report.py
# This creates analysis_report.txt

# Step 3: View the report
cat game_logs/analysis_report.txt
# Or open in your editor

# Step 4 (Optional): Run more games for better analysis
python example_usage.py
# Then generate report again
python generate_report.py
```

---

## Understanding the Analysis

### Win Rates
Shows which agents win most often. Ideal is ~50% in 2-player or ~33% in 3-player games.

### Game Length
- **Too short** (<50 turns): Games end before strategy matters
- **Too long** (>200 turns): Games are tedious
- **Just right** (50-150 turns): Strategic depth with reasonable time

### Card Usage
Shows which cards are played most. Should be relatively balanced.

### Dominant Strategies
Automatically detects if any agent type is significantly stronger.

---

## Troubleshooting

### "No game logs found!"

**Problem:** No games have been run yet.

**Solution:**
```bash
python quick_test.py      # Generates 50 games
# OR
python example_usage.py   # Generates tournament games
```

### "KeyError" or other errors

**Problem:** Old game logs with different format.

**Solution:**
```bash
rm -rf game_logs/*        # Delete old logs
python quick_test.py      # Generate fresh logs
python generate_report.py # Generate report
```

### Empty report

**Problem:** Logs exist but contain no valid data.

**Solution:** Same as above - delete and regenerate.

---

## Quick Reference

| Task | Command |
|------|---------|
| Generate games | `python quick_test.py` |
| Generate report | `python generate_report.py` |
| View report | `cat game_logs/analysis_report.txt` |
| Run 100 games + report | Edit `example_usage.py`, uncomment line 180, run it |
| Clean old data | `rm -rf game_logs/*` |

---

## Advanced: Custom Analysis

You can also call specific analysis methods:

```python
from analysis import GameAnalyzer

analyzer = GameAnalyzer(log_dir="game_logs")
logs = analyzer.load_game_logs()

# Specific analyses
win_rates = analyzer.analyze_win_rates(logs)
game_length = analyzer.analyze_game_length(logs)
card_usage = analyzer.analyze_card_usage(logs)
scores = analyzer.analyze_score_distribution(logs)

# Print specific results
print(win_rates)
print(f"Average game length: {game_length['mean_turns']}")
```

---

## Summary

**Simplest way:**
```bash
python quick_test.py       # Generate games
python generate_report.py  # Create analysis_report.txt
```

The report will be saved in `game_logs/analysis_report.txt` and you can read it to see detailed statistics about game balance!
