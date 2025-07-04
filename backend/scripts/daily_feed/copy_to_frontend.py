#!/usr/bin/env python3
"""
Copy Daily Feed Files to Frontend Public Folder

This script copies the generated word cloud images and summary markdown files
from the pipeline output directory to the frontend's public folder and generates
a JSON file that the frontend can consume directly without backend API calls.

Usage:
    python copy_to_frontend.py --date 2025-07-03
"""

import argparse
import shutil
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import glob

def get_frontend_public_dir():
    """Get the path to the frontend's public directory."""
    # From the script location: backend/scripts/daily_feed/
    # Go to: frontend/public/
    script_dir = Path(__file__).parent
    frontend_public_dir = script_dir.parent.parent.parent / "frontend" / "public"
    return frontend_public_dir

def get_pipeline_output_dir(date: str):
    """Get the path to the pipeline output directory."""
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output" / date
    return output_dir

def read_summary_files(summaries_dir: Path):
    """Read all markdown summary files and return their contents."""
    summaries = []
    if summaries_dir.exists():
        md_files = sorted(summaries_dir.glob("*.md"))
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        summaries.append(content)
            except Exception as e:
                print(f"  ⚠️  Error reading summary file {md_file}: {e}")
    return summaries

def copy_images_to_frontend(source_dir: Path, target_dir: Path, category_name: str):
    """Copy word cloud images to frontend and return the relative path."""
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif']
    
    for ext in image_extensions:
        image_files = list(source_dir.glob(ext))
        for image_file in image_files:
            target_file = target_dir / f"{category_name}_wordcloud{image_file.suffix}"
            shutil.copy2(image_file, target_file)
            print(f"  📷 Copied image: {image_file.name} -> {target_file.name}")
            return f"/daily_feed/{target_file.name}"  # Return relative path for frontend
    
    return None

def generate_daily_feed_json(date: str):
    """Generate the daily feed JSON file for frontend consumption."""
    pipeline_output_dir = get_pipeline_output_dir(date)
    frontend_public_dir = get_frontend_public_dir()
    
    if not pipeline_output_dir.exists():
        print(f"❌ Pipeline output directory not found: {pipeline_output_dir}")
        return False
    
    # Create daily_feed directory in frontend public folder
    daily_feed_dir = frontend_public_dir / "daily_feed"
    daily_feed_dir.mkdir(parents=True, exist_ok=True)
    
    # Get available categories from pipeline output
    available_categories = [d.name for d in pipeline_output_dir.iterdir() if d.is_dir()]
    
    if not available_categories:
        print(f"❌ No category directories found in {pipeline_output_dir}")
        return False
    
    categories_data = []
    
    print(f"📊 Processing categories: {', '.join(available_categories)}")
    
    for category_name in available_categories:
        source_category_dir = pipeline_output_dir / category_name
        
        print(f"📂 Processing category: {category_name}")
        
        # Read summaries
        summaries_dir = source_category_dir / "summaries"
        summaries = read_summary_files(summaries_dir)
        
        # Copy word cloud image
        word_cloud_url = copy_images_to_frontend(source_category_dir, daily_feed_dir, category_name.replace(' ', '_').replace('(', '').replace(')', '').replace('.', ''))
        
        # Create category data
        category_data = {
            "category": category_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('.', ''),
            "display_name": category_name,
            "word_cloud_url": word_cloud_url,
            "summaries": summaries
        }
        
        categories_data.append(category_data)
        print(f"  ✅ Added {len(summaries)} summaries, image: {'Yes' if word_cloud_url else 'No'}")
    
    # Generate the final JSON structure
    daily_feed_data = {
        "categories": categories_data,
        "last_updated": datetime.now().isoformat(),
        "date": date,
        "total_categories": len(categories_data),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Write JSON file
    json_file = daily_feed_dir / "daily_feed.json"
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(daily_feed_data, f, indent=2, ensure_ascii=False)
        print(f"📄 Generated daily feed JSON: {json_file}")
        return True
    except Exception as e:
        print(f"❌ Error writing JSON file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Copy pipeline output files to frontend public folder')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Date to process in YYYY-MM-DD format (default: yesterday)')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    pipeline_output_dir = get_pipeline_output_dir(args.date)
    frontend_public_dir = get_frontend_public_dir()
    
    print("🔄 Copying Daily Feed Files to Frontend Public Folder")
    print("=" * 60)
    print(f"📅 Date: {args.date}")
    print(f"📁 Source: {pipeline_output_dir}")
    print(f"🎯 Target: {frontend_public_dir}")
    
    if not pipeline_output_dir.exists():
        print(f"❌ Pipeline output directory not found: {pipeline_output_dir}")
        print("💡 Make sure to run the word cloud pipeline first!")
        return
    
    # Ensure frontend public directory exists
    frontend_public_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate daily feed JSON and copy files
    if generate_daily_feed_json(args.date):
        print(f"\n🎉 File copying completed!")
        print(f"🌐 Files are now ready for the frontend at: {frontend_public_dir}/daily_feed/")
        print(f"📱 Frontend can now access data via: /daily_feed/daily_feed.json")
        print(f"💡 The frontend will work without backend API calls!")
    else:
        print(f"\n❌ Failed to generate daily feed files")

if __name__ == "__main__":
    main() 