#!/usr/bin/env python3
"""
Complete Daily Feed Pipeline Runner

This script runs the complete daily feed pipeline from data collection to frontend deployment:
1. Collect data from arXiv
2. Generate word clouds and extract top phrases
3. Generate summaries using Gemini API
4. Copy files to frontend for immediate use

Usage:
    python run_daily_feed.py --date 2024-07-04
    python run_daily_feed.py  # Uses yesterday's date by default
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

def verify_frontend_accessibility():
    """Verify that the frontend directory is accessible."""
    script_dir = Path(__file__).parent
    frontend_dir = script_dir.parent.parent.parent / "frontend"
    
    if not frontend_dir.exists():
        print(f"❌ Frontend directory not found: {frontend_dir}")
        return False
    
    public_dir = frontend_dir / "public"
    if not public_dir.exists():
        print(f"❌ Frontend public directory not found: {public_dir}")
        return False
    
    print(f"✅ Frontend directory accessible: {frontend_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Run the complete daily feed pipeline')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Date to process in YYYY-MM-DD format (default: yesterday)')
    parser.add_argument('--top-n', type=int, default=5,
                       help='Number of top phrases to process per discipline (default: 5)')
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
    parser.add_argument('--quick', action='store_true',
                       help='Quick mode: skip data collection and use existing data')
    
    args = parser.parse_args()
    
    # Quick mode implies skip-collect
    if args.quick:
        args.skip_collect = True
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    script_dir = Path(__file__).parent
    
    print("🔬 Complete Daily Feed Pipeline Runner")
    print("=" * 60)
    print(f"📅 Date: {args.date}")
    print(f"📊 Top phrases per discipline: {args.top_n}")
    print(f"🎨 Max terms per word cloud: {args.max_terms}")
    print(f"📄 Min papers per category: {args.min_papers}")
    if args.quick:
        print("⚡ Quick mode: Using existing data")
    
    # Check requirements
    if not check_requirements():
        print("❌ Requirements check failed. Please fix the issues above.")
        return
    
    # Verify frontend accessibility
    if not verify_frontend_accessibility():
        print("❌ Frontend accessibility check failed. Please ensure the frontend directory structure is correct.")
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
            "--max-terms", str(args.max_terms),
            "--top-phrases", str(args.top_n)
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
    
    # Step 4: Copy files to frontend (always run this step)
    total_steps += 1
    command = [
        sys.executable, "copy_to_frontend.py",
        "--date", args.date
    ]
    if run_command(command, "Step 4: Copying files to frontend", cwd=script_dir):
        success_steps += 1
    else:
        print("❌ File copying to frontend failed. Pipeline data is available but not deployed.")
        return
    
    # Final summary
    print(f"\n🎉 Daily Feed Pipeline Execution Summary")
    print("=" * 60)
    print(f"✅ Successfully completed: {success_steps}/{total_steps} steps")
    
    if success_steps == total_steps:
        print(f"🎊 Complete pipeline executed successfully for {args.date}!")
        print(f"🌐 Daily Feed is now ready and deployed to frontend!")
        print(f"📱 You can now view the daily feed in your web application.")
        
        # Show expected file locations
        script_dir = Path(__file__).parent
        frontend_dir = script_dir.parent.parent.parent / "frontend" / "public" / "daily_feed"
        print(f"\n📁 Files deployed to frontend:")
        print(f"   📄 JSON data: {frontend_dir}/daily_feed.json")
        print(f"   📷 Word clouds: {frontend_dir}/*_wordcloud.png")
        print(f"\n💡 Usage examples:")
        print(f"   🔄 Update today's feed: python {Path(__file__).name}")
        print(f"   ⚡ Quick update (skip data collection): python {Path(__file__).name} --quick")
        print(f"   📅 Specific date: python {Path(__file__).name} --date 2024-07-04")
    else:
        print(f"⚠️  Pipeline completed with {total_steps - success_steps} failed steps.")
        print(f"💡 Check the error messages above and try running individual steps manually.")

if __name__ == "__main__":
    main() 