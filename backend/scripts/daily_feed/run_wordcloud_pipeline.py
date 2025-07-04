#!/usr/bin/env python3
"""
Test script for running the word cloud pipeline on existing arXiv data.
This script will process your existing data and generate word clouds and clusters.
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path to allow absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from src.wordcloud_pipeline import WordCloudPipeline

def main():
    parser = argparse.ArgumentParser(
        description='Test the word cloud pipeline with existing data'
    )
    parser.add_argument('--date', type=str, 
        default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        help='Start date in YYYY-MM-DD format (default: yesterday)'
    )
    parser.add_argument(
        '--output-dir', type=str, 
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '--min-papers', type=int,
        default=3,  # Lower threshold for testing
        help='Minimum papers per category (default: 3)'
    )
    parser.add_argument(
        '--max-terms', type=int,
        default=80,
        help='Maximum terms per word cloud (default: 80)'
    )
    
    args = parser.parse_args()
    
    print("🧪 Testing Word Cloud Pipeline")
    print("=" * 50)
    
    try:
        # Initialize pipeline
        pipeline = WordCloudPipeline(
            output_dir=args.output_dir,
            min_papers_per_category=args.min_papers
        )
        
        # Process the data
        results = pipeline.process_date_range(args.date, max_terms=args.max_terms)
        
        if results:
            print("\n🎉 Test completed successfully!")
            
            if 'summary' in results:
                summary = results['summary']
                print("\n📊 Test Results:")
                print(f"  ✅ Categories processed: {len(summary['categories_processed'])}")
                print(f"  ✅ Total papers: {summary['total_papers']}")
                print(f"  ✅ Total terms extracted: {summary['total_terms']}")
                print(f"  ✅ Total top phrases: {summary['total_top_phrases']}")
                print(f"  ⏱️ Processing time: {summary['processing_time']:.1f}s")
            
            print(f"\n💡 Check the '{args.output_dir}' directory for all generated files!")
            
        else:
            print("\n❌ Test failed - no results generated")
            print("💡 Make sure you have data files in the 'data' directory")
            print(f"💡 Looking for file: data/{args.date}-{(datetime.strptime(args.date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')}.json")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure you have the required dependencies installed")
        print("2. Check that your .env file contains GEMINI_API_KEY")
        print("3. Ensure you have arXiv data files in the 'data' directory")
        print("4. Try running: python -m spacy download en_core_web_sm")

if __name__ == "__main__":
    main() 