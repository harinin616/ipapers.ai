#!/usr/bin/env python3
"""
Cluster Summary Generator

This module generates summaries for the top N phrase clusters from each discipline
using the Gemini model. It reads top_phrases.json files and creates individual
markdown files for each phrase summary under a summaries/ folder structure.
"""

import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any
import openai
from dotenv import load_dotenv
from datetime import datetime, timedelta
import re

# Load environment variables
load_dotenv()

class ClusterSummaryGenerator:
    def __init__(self):
        """Initialize the ClusterSummaryGenerator with Gemini API configuration."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure OpenAI client for Gemini API
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    
    def load_top_phrases(self, file_path: str) -> List[Dict[str, Any]]:
        """Load top phrases data from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            print(f"✅ Loaded {len(data)} phrase clusters from {file_path}")
            return data
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON from {file_path}: {e}")
            return []
    
    def sanitize_filename(self, phrase: str) -> str:
        """Sanitize phrase to create a valid filename."""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\s-]', '', phrase)  # Remove special chars except spaces and hyphens
        sanitized = re.sub(r'[-\s]+', '_', sanitized)  # Replace spaces and hyphens with underscores
        return sanitized.lower().strip('_')
    
    def generate_cluster_summary(self, cluster_data: Dict[str, Any], discipline: str) -> str:
        """Generate a comprehensive summary for a phrase cluster using all papers."""
        try:
            phrase = cluster_data.get('phrase', 'Unknown')
            papers = cluster_data.get('contributing_papers', [])
            
            if not papers:
                return f"# {phrase.title()}\n\nNo papers found for this phrase cluster."
            
            print(f"   📄 Processing {len(papers)} papers for phrase: '{phrase}'")
            
            # Prepare papers information for the prompt - include ALL papers
            papers_info = []
            for i, paper in enumerate(papers, 1):
                paper_info = f"""[{i}] Title: {paper.get('title', 'Unknown')}
Authors: {', '.join(paper.get('authors', ['Unknown']))}
Abstract: {paper.get('abstract', 'No abstract available')}
ArXiv ID: {paper.get('arxiv_id', 'Unknown')}
Categories: {', '.join(paper.get('categories', ['Unknown']))}"""
                papers_info.append(paper_info)
            
            papers_text = "\n\n".join(papers_info)
            
            # Create news-style prompt for Gemini
            prompt = f"""You are a science journalist writing an engaging news article about exciting new progress in {discipline}, specifically focusing on recent breakthroughs related to "{phrase}". 

Write a compelling news-style article that highlights the latest developments and innovations from {len(papers)} cutting-edge research papers. Your article should:

**WRITING STYLE:**
- Use an engaging, accessible tone that excites readers about scientific progress
- Write like a science journalist for a general audience, not academic researchers
- Focus on "breakthroughs," "advances," "innovations," and "new developments"
- Make complex concepts understandable and exciting
- Use active voice and dynamic language

**ARTICLE STRUCTURE:**
1. **Opening Hook** (1 paragraph): Start with an exciting lead about the latest breakthroughs in "{phrase}" research
2. **Major Developments** (2-3 paragraphs): Highlight the most significant innovations and what makes them groundbreaking
3. **Future Impact** (1-2 paragraphs): Discuss how these advances will change the field and benefit society

**CITATION REQUIREMENTS:**
- Use [1], [2], [3] format for citations corresponding to the papers below
- Reference multiple papers to show the breadth of recent progress
- Cite papers when describing specific breakthroughs or innovations

**FORMATTING:**
- Start with: # Latest Breakthroughs in {phrase.title()}
- Use engaging subheadings if needed
- Keep paragraphs readable and flowing
- Aim for 4-5 substantial paragraphs total

**TONE EXAMPLES:**
- Instead of: "The research demonstrates..."
- Use: "Scientists have achieved a major breakthrough..."
- Instead of: "This methodology shows..."
- Use: "This innovative approach is revolutionizing..."

Recent research papers in {discipline} ({len(papers)} groundbreaking studies):
{papers_text}

Write an exciting news article that captures the momentum and significance of these recent advances, making readers excited about the future of {discipline}."""

            response = self.client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": f"You are an enthusiastic science journalist specializing in {discipline}. Write engaging news articles that make scientific breakthroughs accessible and exciting for general readers. Focus on the 'wow factor' and real-world impact of new research."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Convert citations to hyperlinks
            summary_with_links = self.convert_citations_to_links(summary, papers)
            
            return summary_with_links
            
        except Exception as e:
            print(f"❌ Error generating summary for phrase '{cluster_data.get('phrase', 'Unknown')}': {e}")
            return f"# Latest Breakthroughs in {cluster_data.get('phrase', 'Unknown').title()}\n\nError generating summary: {str(e)}"
    
    def convert_citations_to_links(self, summary: str, papers: List[Dict[str, Any]]) -> str:
        """Convert [1], [2] and [1, 2] citations to hyperlinks."""
        def replace_citation(match):
            citation_text = match.group(1)
            # Split by comma and strip whitespace from each number
            citation_nums = [num.strip() for num in citation_text.split(',')]
            
            links = []
            for num_str in citation_nums:
                try:
                    citation_num = int(num_str)
                    if 1 <= citation_num <= len(papers):
                        paper = papers[citation_num - 1]
                        arxiv_id = paper.get('arxiv_id', '')
                        title = paper.get('title', 'Unknown Title')
                        if arxiv_id:
                            links.append(f"[{title}](https://arxiv.org/abs/{arxiv_id})")
                        else:
                            links.append(f"[{title}]")
                    else:
                        # Invalid citation number, keep original
                        links.append(f"[{num_str}]")
                except ValueError:
                    # Invalid number format, keep original
                    links.append(f"[{num_str}]")
            
            if len(links) == 1:
                return f"[{links[0]}]"
            else:
                # Multiple citations: wrap in square brackets and join with commas
                return f"[{', '.join(links)}]"
        
        # Pattern to match [1], [2], [1, 2], [2, 3, 4], etc.
        citation_pattern = r'\[(\d+(?:,\s*\d+)*)\]'
        return re.sub(citation_pattern, replace_citation, summary)
    
    def process_discipline(self, discipline_path: Path, discipline_name: str, date: str, top_n: int) -> Dict[str, Any]:
        """Process a single discipline and generate markdown files for top N phrases."""
        top_phrases_file = discipline_path / "top_phrases.json"
        
        if not top_phrases_file.exists():
            print(f"⚠️  No top_phrases.json found for {discipline_name}")
            return {"discipline": discipline_name, "error": "top_phrases.json not found"}
        
        # Load the top phrases data
        phrases_data = self.load_top_phrases(str(top_phrases_file))
        
        if not phrases_data:
            return {"discipline": discipline_name, "error": "Failed to load phrases data"}
        
        # Create summaries directory
        summaries_dir = discipline_path / "summaries"
        summaries_dir.mkdir(exist_ok=True)
        print(f"📁 Created summaries directory: {summaries_dir}")
        
        # Get top N phrases (should be sorted by rank already)
        top_n_phrases = phrases_data[:top_n]
        actual_count = len(top_n_phrases)
        
        generated_files = []
        for i, phrase_cluster in enumerate(top_n_phrases, 1):
            phrase = phrase_cluster.get('phrase', 'Unknown')
            print(f"🔄 Generating summary {i}/{actual_count} for phrase: '{phrase}'")
            
            # Generate comprehensive summary using ALL papers
            summary = self.generate_cluster_summary(phrase_cluster, discipline_name)
            
            # Create filename
            filename = f"{i}_{self.sanitize_filename(phrase)}.md"
            file_path = summaries_dir / filename
            
            # Save markdown file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(summary)
                print(f"✅ Saved summary to: {file_path}")
                generated_files.append(filename)
            except Exception as e:
                print(f"❌ Error saving file {file_path}: {e}")
        
        return {
            "discipline": discipline_name,
            "date": date,
            "summaries_directory": str(summaries_dir),
            "generated_files": generated_files,
            "phrases_processed": len(top_n_phrases)
        }
    
    def generate_summaries_for_date(self, date: str, top_n: int) -> Dict[str, Any]:
        """Generate summaries for all disciplines for a given date."""
        output_dir = Path("output") / date
        
        if not output_dir.exists():
            print(f"❌ Output directory not found: {output_dir}")
            return {"error": f"Output directory not found for date {date}"}
        
        # Get all discipline directories
        discipline_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        
        if not discipline_dirs:
            print(f"❌ No discipline directories found in {output_dir}")
            return {"error": f"No discipline directories found for date {date}"}
        
        all_results = {
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "total_disciplines": len(discipline_dirs),
            "top_n": top_n,
            "disciplines": {}
        }
        
        for discipline_dir in discipline_dirs:
            discipline_name = discipline_dir.name
            print(f"\n📚 Processing discipline: {discipline_name}")
            
            discipline_result = self.process_discipline(discipline_dir, discipline_name, date, top_n)
            all_results["disciplines"][discipline_name] = discipline_result
        
        return all_results
    
    def save_processing_log(self, results: Dict[str, Any], output_dir: Path):
        """Save a processing log with summary of what was generated."""
        log_file = output_dir / "summary_generation_log.json"
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"📋 Processing log saved to: {log_file}")
        except Exception as e:
            print(f"❌ Error saving processing log: {e}")

def main():
    """Main function to run the cluster summary generation."""
    parser = argparse.ArgumentParser(description='Generate markdown summaries for top N phrase clusters from each discipline')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Date to process in YYYY-MM-DD format (default: yesterday)')
    parser.add_argument('--top-n', type=int, default=5,
                       help='Number of top phrases to process per discipline (default: 5)')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    # Validate top_n
    if args.top_n < 1:
        print("❌ Error: --top-n must be a positive integer.")
        return
    
    # Initialize the generator
    try:
        generator = ClusterSummaryGenerator()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please make sure to set your GEMINI_API_KEY in the .env file")
        return
    
    print(f"🚀 Starting cluster summary generation for date: {args.date}")
    print(f"📊 Processing top {args.top_n} phrases per discipline")
    print(f"📄 Generating individual markdown files for each phrase...")
    
    # Generate summaries
    results = generator.generate_summaries_for_date(args.date, args.top_n)
    
    # Save processing log
    output_dir = Path("output") / args.date
    if output_dir.exists():
        generator.save_processing_log(results, output_dir)
    
    # Print summary
    if "error" not in results:
        total_files = sum(len(d.get("generated_files", [])) for d in results["disciplines"].values() if isinstance(d, dict))
        print(f"\n🎉 Summary generation completed!")
        print(f"📊 Processed {results.get('total_disciplines', 0)} disciplines")
        print(f"📄 Generated {total_files} markdown files")
        print(f"🔝 Used top {args.top_n} phrases per discipline")
        print(f"📁 Files saved under: output/{args.date}/*/summaries/")
    else:
        print(f"\n❌ Error: {results['error']}")

if __name__ == "__main__":
    main() 