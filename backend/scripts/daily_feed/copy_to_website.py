#!/usr/bin/env python3
"""
Copy Daily Feed Files to Website Location

This script copies the generated word cloud images and summary markdown files
from the pipeline output directory to the website's expected location.

Usage:
    python copy_to_website.py --date 2024-07-04
"""

import argparse
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta
import glob

# Category mapping from pipeline output to website structure
CATEGORY_MAPPING = {
    'cs': 'computer_science',
    'econ': 'economics', 
    'eess': 'electrical_engineering',
    'math': 'mathematics',
    'stat': 'statistics',
    'q-bio': 'quantitative_biology',
    'q-fin': 'quantitative_finance',
    'physics': 'physics'
}

def get_website_data_dir():
    """Get the path to the website's daily feed data directory."""
    # From the script location: backend/scripts/daily_feed/
    # Go back to: backend/data/daily_feed/
    script_dir = Path(__file__).parent
    website_data_dir = script_dir.parent.parent / "data" / "daily_feed"
    return website_data_dir

def get_pipeline_output_dir(date: str):
    """Get the path to the pipeline output directory."""
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output" / date
    return output_dir

def copy_word_clouds(source_category_dir: Path, target_category_dir: Path):
    """Copy word cloud images from source to target directory."""
    target_images_dir = target_category_dir / "images"
    target_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Look for image files in the source directory
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif']
    copied_files = []
    
    for ext in image_extensions:
        image_files = list(source_category_dir.glob(ext))
        for image_file in image_files:
            target_file = target_images_dir / image_file.name
            shutil.copy2(image_file, target_file)
            copied_files.append(image_file.name)
            print(f"  📷 Copied image: {image_file.name}")
    
    return copied_files

def copy_summaries(source_category_dir: Path, target_category_dir: Path):
    """Copy summary markdown files from source to target directory."""
    source_summaries_dir = source_category_dir / "summaries"
    target_summaries_dir = target_category_dir / "summaries"
    
    if not source_summaries_dir.exists():
        print(f"  ⚠️  No summaries directory found: {source_summaries_dir}")
        return []
    
    target_summaries_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all markdown files
    md_files = list(source_summaries_dir.glob("*.md"))
    copied_files = []
    
    for md_file in md_files:
        target_file = target_summaries_dir / md_file.name
        shutil.copy2(md_file, target_file)
        copied_files.append(md_file.name)
        print(f"  📄 Copied summary: {md_file.name}")
    
    return copied_files

def clean_old_files(target_category_dir: Path):
    """Clean old files from the target directory."""
    # Clean images
    images_dir = target_category_dir / "images"
    if images_dir.exists():
        for file in images_dir.iterdir():
            if file.is_file():
                file.unlink()
                print(f"  🗑️  Removed old image: {file.name}")
    
    # Clean summaries
    summaries_dir = target_category_dir / "summaries"
    if summaries_dir.exists():
        for file in summaries_dir.iterdir():
            if file.is_file():
                file.unlink()
                print(f"  🗑️  Removed old summary: {file.name}")

def copy_category_files(date: str, source_category: str, target_category: str, clean_old: bool = True):
    """Copy files for a single category."""
    pipeline_output_dir = get_pipeline_output_dir(date)
    website_data_dir = get_website_data_dir()
    
    source_category_dir = pipeline_output_dir / source_category
    target_category_dir = website_data_dir / target_category
    
    if not source_category_dir.exists():
        print(f"  ⚠️  Source category directory not found: {source_category_dir}")
        return False
    
    print(f"📂 Processing category: {source_category} → {target_category}")
    
    # Clean old files if requested
    if clean_old:
        clean_old_files(target_category_dir)
    
    # Copy word clouds
    copied_images = copy_word_clouds(source_category_dir, target_category_dir)
    
    # Copy summaries
    copied_summaries = copy_summaries(source_category_dir, target_category_dir)
    
    if copied_images or copied_summaries:
        print(f"  ✅ Copied {len(copied_images)} images and {len(copied_summaries)} summaries")
        return True
    else:
        print(f"  ⚠️  No files found to copy for {source_category}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Copy pipeline output files to website location')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Date to process in YYYY-MM-DD format (default: yesterday)')
    parser.add_argument('--no-clean', action='store_true',
                       help='Do not clean old files before copying new ones')
    parser.add_argument('--category', type=str,
                       help='Process only a specific category (e.g., cs, math)')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    pipeline_output_dir = get_pipeline_output_dir(args.date)
    website_data_dir = get_website_data_dir()
    
    print("🔄 Copying Daily Feed Files to Website Location")
    print("=" * 60)
    print(f"📅 Date: {args.date}")
    print(f"📁 Source: {pipeline_output_dir}")
    print(f"🎯 Target: {website_data_dir}")
    print(f"🧹 Clean old files: {not args.no_clean}")
    
    if not pipeline_output_dir.exists():
        print(f"❌ Pipeline output directory not found: {pipeline_output_dir}")
        print("💡 Make sure to run the word cloud pipeline first!")
        return
    
    # Get available categories from pipeline output
    available_categories = [d.name for d in pipeline_output_dir.iterdir() if d.is_dir()]
    
    if not available_categories:
        print(f"❌ No category directories found in {pipeline_output_dir}")
        return
    
    print(f"📊 Available categories: {', '.join(available_categories)}")
    
    # Process categories
    success_count = 0
    clean_old = not args.no_clean
    
    if args.category:
        # Process only specified category
        if args.category not in available_categories:
            print(f"❌ Category '{args.category}' not found in pipeline output")
            return
        
        target_category = CATEGORY_MAPPING.get(args.category, args.category)
        if copy_category_files(args.date, args.category, target_category, clean_old):
            success_count += 1
    else:
        # Process all available categories
        for source_category in available_categories:
            target_category = CATEGORY_MAPPING.get(source_category, source_category)
            if copy_category_files(args.date, source_category, target_category, clean_old):
                success_count += 1
    
    print(f"\n🎉 File copying completed!")
    print(f"✅ Successfully processed {success_count} categories")
    print(f"🌐 Files are now ready for the website at: {website_data_dir}")
    
    if success_count > 0:
        print(f"\n💡 You can now view the Daily Feed on your website!")
        print(f"📝 The API will serve files from: /api/daily_feed/")

if __name__ == "__main__":
    main() 