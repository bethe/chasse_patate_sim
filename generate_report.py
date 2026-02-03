"""
Generate Comprehensive Analysis Report

This script loads all game logs and generates a detailed analysis report.

Usage:
    python generate_report.py
    
The report will be saved to: analysis_report.txt
"""

from analysis import GameAnalyzer

def generate_comprehensive_report():
    """Load game logs and generate comprehensive analysis report"""
    
    print("\n" + "="*80)
    print("GENERATING COMPREHENSIVE ANALYSIS REPORT")
    print("="*80)
    print()
    
    # Create analyzer and load all game logs
    print("Loading game logs from: game_logs/")
    analyzer = GameAnalyzer(log_dir="game_logs")
    logs = analyzer.load_game_logs()
    
    if not logs:
        print("❌ No game logs found!")
        print("\nTo generate game logs, first run:")
        print("  python quick_test.py")
        print("  or")
        print("  python example_usage.py")
        return
    
    print(f"✓ Loaded {len(logs)} games")
    print()
    
    # Generate the comprehensive report
    print("Analyzing games and generating report...")
    report_path = analyzer.generate_report(logs, output_file="analysis_report.txt")
    
    print()
    print("="*80)
    print("✓ REPORT GENERATED SUCCESSFULLY!")
    print("="*80)
    print(f"\nReport saved to: {report_path}")
    print()
    print("The report includes:")
    print("  • Win rates by agent type")
    print("  • Game length statistics")
    print("  • Score distribution")
    print("  • Dominant strategy detection")
    print("  • Card usage patterns")
    print("  • Detailed matchup analysis")
    print()
    print(f"Open the file to view: cat {report_path}")
    print("="*80 + "\n")
    
    # Show a preview of the report
    print("Report Preview (first 30 lines):")
    print("-" * 80)
    try:
        with open(report_path, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:30]):
                print(line.rstrip())
            if len(lines) > 30:
                print(f"\n... and {len(lines) - 30} more lines")
    except Exception as e:
        print(f"Could not preview report: {e}")
    print("-" * 80)


if __name__ == "__main__":
    generate_comprehensive_report()
