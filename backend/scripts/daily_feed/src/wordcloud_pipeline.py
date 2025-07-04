#!/usr/bin/env python3
"""
Main pipeline for processing arXiv papers and generating word clouds with top phrases.
Simplified to focus on extracting top phrases and their contributing papers.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time

from src.text_processor import TextProcessor, TermInfo
from src.wordcloud_generator import WordCloudGenerator, WordCloudConfig

class WordCloudPipeline:
    def __init__(self, output_dir: str = "output", 
                 min_papers_per_category: int = 5):
        """
        Initialize the word cloud pipeline.
        
        Args:
            output_dir: Base output directory
            min_papers_per_category: Minimum papers needed to process a category
        """
        self.base_output_dir = Path(output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.min_papers_per_category = min_papers_per_category
        
        # Initialize components
        print("🚀 Initializing Word Cloud Pipeline...")
        self.text_processor = TextProcessor()
        print("✅ Pipeline initialized")
    
    def load_papers_from_file(self, json_file_path: str) -> List[Dict[str, Any]]:
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
    
    def process_category(self, papers: List[Dict[str, Any]], 
                        category: str, 
                        date: str,
                        max_terms: int = 50,
                        top_phrases_count: int = 5) -> Dict[str, Any]:
        """
        Process a single category: extract terms, generate word cloud, and save top phrases.
        
        Args:
            papers: List of papers in this category
            category: Category name (e.g., 'cs', 'math')
            date: Date string for output files
            max_terms: Maximum terms for word cloud
            top_phrases_count: Number of top phrases to save with contributing papers
            
        Returns:
            Dictionary with processing results
        """
        if len(papers) < self.min_papers_per_category:
            print(f"⚠️  Skipping {category}: only {len(papers)} papers (minimum: {self.min_papers_per_category})")
            return None
        
        print(f"\n📊 Processing category: {category} ({len(papers)} papers)")
        
        # Create hierarchical output directory: output/{date}/{category}/
        category_output_dir = self.base_output_dir / date / category
        category_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize category-specific wordcloud generator
        wordcloud_generator = WordCloudGenerator(str(category_output_dir))
        
        start_time = time.time()
        
        # Step 1: Extract terms from papers
        print("  🔍 Extracting terms...")
        terms_info = self.text_processor.process_papers(papers)
        
        if not terms_info:
            print(f"  ⚠️  No terms extracted for {category}")
            return None
        
        # Step 2: Generate word cloud
        print("  🎨 Generating word cloud...")
        wordcloud_obj, wordcloud_path = wordcloud_generator.generate_wordcloud(
            terms_info, category, date, max_terms=max_terms
        )
        
        # Step 3: Generate detailed term analysis
        print("  📝 Saving term analysis...")
        analysis_path = wordcloud_generator.save_term_analysis(
            terms_info, category, date, max_terms=max_terms
        )
        
        # Step 4: Extract top phrases and their contributing papers
        print(f"  🔤 Extracting top {top_phrases_count} phrases...")
        top_phrases_data = self._extract_top_phrases(terms_info, papers, top_phrases_count)
        
        processing_time = time.time() - start_time
        
        # Compile results
        result = {
            'category': category,
            'date': date,
            'papers_count': len(papers),
            'terms_count': len(terms_info),
            'processing_time': processing_time,
            'wordcloud_path': wordcloud_path,
            'analysis_path': analysis_path,
            'top_phrases': top_phrases_data,
            'category_output_dir': category_output_dir
        }
        
        # Save top phrases data
        self._save_top_phrases_data(result, category, date)
        
        print(f"  ✅ Completed {category} in {processing_time:.1f}s")
        return result
    
    def _extract_top_phrases(self, terms_info: Dict[str, TermInfo], 
                           papers: List[Dict[str, Any]], 
                           top_count: int = 5) -> List[Dict[str, Any]]:
        """
        Extract top phrases and their contributing papers.
        
        Args:
            terms_info: Dictionary of all terms
            papers: List of all papers
            top_count: Number of top phrases to extract
            
        Returns:
            List of dictionaries with phrase data and contributing papers
        """
        # Filter for phrases only (terms with spaces)
        phrases = {k: v for k, v in terms_info.items() if ' ' in k}
        
        if not phrases:
            print("    ⚠️  No phrases found")
            return []
        
        # Sort by frequency and take top phrases
        top_phrases = dict(sorted(phrases.items(), 
                                 key=lambda x: x[1].frequency, 
                                 reverse=True)[:top_count])
        
        # Create paper lookup for efficiency
        papers_dict = {paper.get('arxiv_id', f'paper_{i}'): paper 
                      for i, paper in enumerate(papers)}
        
        # Build phrase data with contributing papers
        phrases_data = []
        for rank, (phrase, term_info) in enumerate(top_phrases.items(), 1):
            # Get contributing papers
            contributing_papers = []
            for arxiv_id in term_info.papers:
                if arxiv_id in papers_dict:
                    paper = papers_dict[arxiv_id]
                    contributing_papers.append({
                        'arxiv_id': arxiv_id,
                        'title': paper.get('title', 'Unknown Title'),
                        'authors': paper.get('authors', []),
                        'abstract': paper.get('abstract', ''),
                        'categories': paper.get('categories', []),
                        'published': paper.get('published', ''),
                        'url': paper.get('url', f'https://arxiv.org/abs/{arxiv_id}')
                    })
            
            phrase_data = {
                'rank': rank,
                'phrase': phrase,
                'frequency': term_info.frequency,
                'paper_count': len(contributing_papers),
                'contributing_papers': contributing_papers,
                'contexts': term_info.contexts[:5]  # Save first 5 contexts as examples
            }
            phrases_data.append(phrase_data)
        
        return phrases_data
    
    def _save_top_phrases_data(self, result: Dict[str, Any], category: str, date: str):
        """Save top phrases data to JSON file in category directory."""
        category_dir = result['category_output_dir']
        
        if result['top_phrases']:
            # Save top phrases with contributing papers
            phrases_file = category_dir / "top_phrases.json"
            with open(phrases_file, 'w', encoding='utf-8') as f:
                json.dump(result['top_phrases'], f, indent=2, ensure_ascii=False)
            
            print(f"    📁 Top phrases saved: {phrases_file}")
            
            # Also save a summary file with just the phrase names and counts
            summary_data = {
                'category': category,
                'date': date,
                'total_papers': result['papers_count'],
                'phrases_summary': [
                    {
                        'rank': p['rank'],
                        'phrase': p['phrase'],
                        'frequency': p['frequency'],
                        'paper_count': p['paper_count']
                    }
                    for p in result['top_phrases']
                ]
            }
            
            summary_file = category_dir / "phrases_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            print(f"    📁 Phrases summary saved: {summary_file}")
    
    def process_all_categories(self, papers: List[Dict[str, Any]], 
                             date: str,
                             max_terms: int = 50,
                             top_phrases_count: int = 5) -> Dict[str, Any]:
        """
        Process all categories from a list of papers.
        
        Args:
            papers: List of all papers
            date: Date string for output files
            max_terms: Maximum terms for word cloud
            top_phrases_count: Number of top phrases to save
            
        Returns:
            Dictionary with results for all categories
        """
        print(f"\n🔄 Starting pipeline for {len(papers)} papers on {date}")
        
        # Group papers by category
        category_papers = self.text_processor.categorize_papers_by_discipline(papers)
        
        print(f"📊 Found {len(category_papers)} categories:")
        for category, cat_papers in category_papers.items():
            print(f"  - {category}: {len(cat_papers)} papers")
        
        # Process each category
        results = {}
        
        for category, cat_papers in category_papers.items():
            result = self.process_category(cat_papers, category, date, 
                                         max_terms=max_terms, 
                                         top_phrases_count=top_phrases_count)
            if result:
                results[category] = result
        
        # Generate overall summary
        summary = self._generate_summary(results, date)
        results['summary'] = summary
        
        # Save overall results
        self._save_overall_results(results, date)
        
        print(f"\n✅ Pipeline completed for {date}")
        print(f"📊 Processed {len(results)} categories successfully")
        
        return results
    
    def _generate_summary(self, results: Dict[str, Any], date: str) -> Dict[str, Any]:
        """Generate overall summary statistics."""
        total_papers = sum(r['papers_count'] for r in results.values() 
                          if isinstance(r, dict) and 'papers_count' in r)
        
        total_terms = sum(r['terms_count'] for r in results.values() 
                         if isinstance(r, dict) and 'terms_count' in r)
        
        total_phrases = sum(len(r['top_phrases']) for r in results.values() 
                          if isinstance(r, dict) and 'top_phrases' in r)
        
        processing_time = sum(r['processing_time'] for r in results.values() 
                            if isinstance(r, dict) and 'processing_time' in r)
        
        categories_processed = [k for k, v in results.items() 
                              if isinstance(v, dict) and 'category' in v]
        
        return {
            'date': date,
            'categories_processed': categories_processed,
            'total_papers': total_papers,
            'total_terms': total_terms,
            'total_top_phrases': total_phrases,
            'processing_time': processing_time,
            'average_papers_per_category': total_papers / len(categories_processed) if categories_processed else 0,
            'average_terms_per_category': total_terms / len(categories_processed) if categories_processed else 0
        }
    
    def _save_overall_results(self, results: Dict[str, Any], date: str):
        """Save overall pipeline results in date directory."""
        # Save summary only
        summary_data = {
            'summary': results.get('summary', {}),
            'categories': {}
        }
        
        # Add basic info for each category
        for category, result in results.items():
            if isinstance(result, dict) and 'category' in result:
                summary_data['categories'][category] = {
                    'papers_count': result['papers_count'],
                    'terms_count': result['terms_count'],
                    'top_phrases_count': len(result['top_phrases']),
                    'wordcloud_path': result['wordcloud_path'],
                    'analysis_path': result['analysis_path'],
                    'processing_time': result['processing_time']
                }
        
        # Save summary in date directory
        date_dir = self.base_output_dir / date
        summary_file = date_dir / "pipeline_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Pipeline summary saved: {summary_file}")
    
    def process_date_range(self, start_date: str, 
                          end_date: Optional[str] = None,
                          max_terms: int = 50,
                          top_phrases_count: int = 5) -> Dict[str, Any]:
        """
        Process papers for a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to start_date + 1 day)
            max_terms: Maximum terms for word cloud
            top_phrases_count: Number of top phrases to save
            
        Returns:
            Processing results
        """
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_date_obj = start_date_obj + timedelta(days=1)
            
            date_str = start_date_obj.strftime('%Y-%m-%d')
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
            print("💡 Please run main.py first to collect the data")
            return {}
        
        # Load and process papers
        papers = self.load_papers_from_file(str(json_file_path))
        if not papers:
            print("❌ No papers found or failed to load data")
            return {}
        
        return self.process_all_categories(papers, date_str, max_terms=max_terms, 
                                         top_phrases_count=top_phrases_count)
