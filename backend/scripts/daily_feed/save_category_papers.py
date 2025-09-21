#!/usr/bin/env python3
"""
Save Category Papers Script

This script reads the raw paper data and saves category-specific paper data
into each category folder under output. This ensures all JSON data is available
in each category folder for complete data organization.

Usage:
    python save_category_papers.py --date 2024-07-04
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add current directory to path to allow absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from src.text_processor import TextProcessor

def load_papers_from_file(json_file_path: str) -> List[Dict[str, Any]]:
    """Load papers from JSON file."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)
        
        print(f"📄 Loaded {len(papers)} papers from {json_file_path}")
        return papers
        
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error decoding JSON: {e}")
        return []
    except Exception as e:
        print(f"❌ Error loading papers: {e}")
        return []

def save_category_papers(papers: List[Dict[str, Any]], category: str, 
                        output_dir: Path, date: str) -> bool:
    """Save papers for a specific category to its folder."""
    try:
        category_dir = output_dir / date / category
        
        if not category_dir.exists():
            print(f"⚠️  Category directory not found: {category_dir}")
            return False
        
        # Save the papers data
        papers_file = category_dir / "papers.json"
        
        # Create metadata for the papers
        papers_data = {
            "category": category,
            "date": date,
            "total_papers": len(papers),
            "papers": papers,
            "generated_at": datetime.now().isoformat()
        }
        
        with open(papers_file, 'w', encoding='utf-8') as f:
            json.dump(papers_data, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Saved {len(papers)} papers to: {papers_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving papers for {category}: {e}")
        return False

def save_all_category_papers(date: str, output_dir: str = "output") -> Dict[str, Any]:
    """Save paper data for all categories."""
    try:
        # Parse date
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        end_date_obj = date_obj + timedelta(days=1)
        
        date_str = date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')
        
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        return {}
    
    # Look for data file
    data_dir = Path("data")
    json_filename = f"{date_str}-{end_date_str}.json"
    json_file_path = data_dir / json_filename
    
    if not json_file_path.exists():
        print(f"❌ Data file not found: {json_file_path}")
        print("💡 Please run collect_data.py first to collect the data")
        return {}
    
    # Load papers
    papers = load_papers_from_file(str(json_file_path))
    if not papers:
        print("❌ No papers found or failed to load data")
        return {}
    
    # Initialize text processor to categorize papers
    text_processor = TextProcessor()
    
    # Group papers by category
    category_papers = text_processor.categorize_papers_by_discipline(papers)
    
    output_path = Path(output_dir)
    results = {
        "date": date,
        "total_papers": len(papers),
        "categories_processed": [],
        "saved_successfully": []
    }
    
    print(f"\n💾 Saving category papers for {len(category_papers)} categories:")
    for category, cat_papers in category_papers.items():
        print(f"  - {category}: {len(cat_papers)} papers")
        results["categories_processed"].append(category)
        
        if save_category_papers(cat_papers, category, output_path, date):
            results["saved_successfully"].append(category)
    
    # Save a summary of what was saved
    date_dir = output_path / date
    if date_dir.exists():
        summary_file = date_dir / "category_papers_summary.json"
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"📁 Summary saved: {summary_file}")
        except Exception as e:
            print(f"⚠️  Error saving summary: {e}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Save category-specific paper data to output folders')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Date to process in YYYY-MM-DD format (default: yesterday)')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory (default: output)')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    print("💾 Saving Category Papers to Output Folders")
    print("=" * 60)
    print(f"📅 Date: {args.date}")
    print(f"📁 Output directory: {args.output_dir}")
    
    results = save_all_category_papers(args.date, args.output_dir)
    
    if results:
        successful_count = len(results["saved_successfully"])
        total_count = len(results["categories_processed"])
        
        print(f"\n🎉 Category Papers Saving Summary")
        print("=" * 60)
        print(f"✅ Successfully saved: {successful_count}/{total_count} categories")
        print(f"📄 Total papers processed: {results['total_papers']}")
        
        if results["saved_successfully"]:
            print(f"\n📂 Categories saved:")
            for category in results["saved_successfully"]:
                print(f"   - {category}")
        
        if successful_count == total_count:
            print(f"\n🎊 All category papers saved successfully!")
            print(f"📁 Each category folder now contains its papers.json file")
        else:
            failed_categories = set(results["categories_processed"]) - set(results["saved_successfully"])
            print(f"\n⚠️  Some categories failed:")
            for category in failed_categories:
                print(f"   - {category}")
    else:
        print("\n❌ Failed to save category papers")

if __name__ == "__main__":
    main() 