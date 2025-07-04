#!/usr/bin/env python3
"""
Full Daily Feed Pipeline Runner

This script runs the complete daily feed pipeline:
1. Collect data from arXiv
2. Generate word clouds and extract top phrases
3. Generate summaries using Gemini API
4. Copy files to website location

Usage:
    python run_full_pipeline.py --date 2024-07-04
"""

import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import os

def run_command(command, description, cwd=None):
    """Run a command and handle errors."""
    print(f"\n🚀 {description}")
    print(f"💻 Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command, 
            cwd=cwd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ {description} completed successfully")
        if result.stdout.strip():
            print("📄 Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        if e.stdout:
            print("📄 Output:")
            print(e.stdout)
        if e.stderr:
            print("📄 Error:")
            print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {command[0]}")
        return False

def check_requirements():
    """Check if required dependencies are available."""
    print("🔍 Checking requirements...")
    
    # Check if Python is available
    try:
        result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        print(f"✅ Python: {result.stdout.strip()}")
    except:
        print("❌ Python not found")
        return False
    
    # Check if .env file exists with GEMINI_API_KEY
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
        if "GEMINI_API_KEY" in env_content:
            print("✅ GEMINI_API_KEY found in .env file")
        else:
            print("⚠️  GEMINI_API_KEY not found in .env file")
            print("💡 Make sure to add GEMINI_API_KEY=your_key_here to .env file")
    else:
        print("⚠️  .env file not found")
        print("💡 Create a .env file with GEMINI_API_KEY=your_key_here")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Run the complete daily feed pipeline')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Date to process in YYYY-MM-DD format (default: yesterday)')
    parser.add_argument('--top-n', type=int, default=3,
                       help='Number of top phrases to process per discipline (default: 3)')
    parser.add_argument('--max-terms', type=int, default=80,
                       help='Maximum terms per word cloud (default: 80)')
    parser.add_argument('--min-papers', type=int, default=1,
                       help='Minimum papers per category (default: 1)')
    parser.add_argument('--skip-collect', action='store_true',
                       help='Skip data collection step (use existing data)')
    parser.add_argument('--skip-wordcloud', action='store_true',
                       help='Skip word cloud generation step')
    parser.add_argument('--skip-summaries', action='store_true',
                       help='Skip summary generation step')
    parser.add_argument('--skip-copy', action='store_true',
                       help='Skip copying files to website location')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    script_dir = Path(__file__).parent
    
    print("🔬 Daily Feed Pipeline Runner")
    print("=" * 60)
    print(f"📅 Date: {args.date}")
    print(f"📊 Top phrases per discipline: {args.top_n}")
    print(f"🎨 Max terms per word cloud: {args.max_terms}")
    print(f"📄 Min papers per category: {args.min_papers}")
    
    # Check requirements
    if not check_requirements():
        print("❌ Requirements check failed. Please fix the issues above.")
        return
    
    success_steps = 0
    total_steps = 0
    
    # Step 1: Collect data from arXiv
    if not args.skip_collect:
        total_steps += 1
        command = [sys.executable, "collect_data.py", "--date", args.date]
        if run_command(command, "Step 1: Collecting data from arXiv", cwd=script_dir):
            success_steps += 1
        else:
            print("❌ Data collection failed. Stopping pipeline.")
            return
    else:
        print("⏭️  Skipping data collection step")
    
    # Step 2: Generate word clouds and extract top phrases
    if not args.skip_wordcloud:
        total_steps += 1
        command = [
            sys.executable, "run_wordcloud_pipeline.py", 
            "--date", args.date,
            "--min-papers", str(args.min_papers),
            "--max-terms", str(args.max_terms)
        ]
        if run_command(command, "Step 2: Generating word clouds and extracting phrases", cwd=script_dir):
            success_steps += 1
        else:
            print("❌ Word cloud generation failed. Stopping pipeline.")
            return
    else:
        print("⏭️  Skipping word cloud generation step")
    
    # Step 3: Generate summaries using Gemini API
    if not args.skip_summaries:
        total_steps += 1
        command = [
            sys.executable, "summary_generator.py",
            "--date", args.date,
            "--top-n", str(args.top_n)
        ]
        if run_command(command, "Step 3: Generating summaries with Gemini API", cwd=script_dir):
            success_steps += 1
        else:
            print("❌ Summary generation failed. Stopping pipeline.")
            return
    else:
        print("⏭️  Skipping summary generation step")
    
    # Step 4: Copy files to website location
    if not args.skip_copy:
        total_steps += 1
        command = [
            sys.executable, "copy_to_website.py",
            "--date", args.date
        ]
        if run_command(command, "Step 4: Copying files to website location", cwd=script_dir):
            success_steps += 1
        else:
            print("⚠️  File copying failed, but pipeline data is still available.")
    else:
        print("⏭️  Skipping file copying step")
    
    # Final summary
    print(f"\n🎉 Pipeline Execution Summary")
    print("=" * 60)
    print(f"✅ Successfully completed: {success_steps}/{total_steps} steps")
    
    if success_steps == total_steps:
        print(f"🎊 Full pipeline completed successfully for {args.date}!")
        print(f"🌐 Daily Feed is now ready on your website!")
        print(f"📱 Visit your website and navigate to 'Daily Feed' to see the results.")
        
        # Show expected file locations
        website_data_dir = script_dir.parent.parent / "data" / "daily_feed"
        print(f"\n📁 Files are available at:")
        print(f"   📷 Word clouds: {website_data_dir}/{{category}}/images/")
        print(f"   📄 Summaries: {website_data_dir}/{{category}}/summaries/")
    else:
        print(f"⚠️  Pipeline completed with some issues.")
        print(f"💡 Check the output above for details on failed steps.")
    
    # Show useful commands for debugging
    print(f"\n🔧 Useful debugging commands:")
    print(f"   📊 Check pipeline output: ls -la {script_dir}/output/{args.date}/")
    print(f"   🌐 Check website files: ls -la {script_dir.parent.parent}/data/daily_feed/")
    print(f"   🔄 Re-run specific step: python {{script_name}} --date {args.date}")

if __name__ == "__main__":
    main() 