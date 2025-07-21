#!/usr/bin/env python3
"""
Copy Daily Feed Files to Frontend Public Folder

This script copies the generated word cloud images, summary markdown files, and
filtered papers data from the pipeline output directory to the frontend's public 
folder and generates a JSON file that the frontend can consume directly without 
backend API calls.

The papers data is filtered to include only: arxiv_id, categories, title, 
authors, abstract, and submitted_date_parsed.

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
import re

# Import audio generation modules
from kokoro import KPipeline
import soundfile as sf

# Initialize the audio pipeline
audio_pipeline = KPipeline(lang_code='a')

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

def load_pipeline_summary(date: str):
    """Load the pipeline summary JSON with paper counts."""
    pipeline_output_dir = get_pipeline_output_dir(date)
    summary_file = pipeline_output_dir / "pipeline_summary.json"
    
    if not summary_file.exists():
        print(f"  ⚠️  Pipeline summary file not found: {summary_file}")
        return None
    
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️  Error reading pipeline summary: {e}")
        return None

def load_phrases_summary(category_dir: Path):
    """Load the phrases summary JSON with paper counts for phrase clusters."""
    phrases_file = category_dir / "phrases_summary.json"
    
    if not phrases_file.exists():
        print(f"  ⚠️  Phrases summary file not found: {phrases_file}")
        return None
    
    try:
        with open(phrases_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️  Error reading phrases summary: {e}")
        return None

def load_category_papers(category_dir: Path):
    """Load the category papers JSON and filter to required fields only."""
    papers_file = category_dir / "papers.json"
    
    if not papers_file.exists():
        print(f"  ⚠️  Category papers file not found: {papers_file}")
        return []
    
    try:
        with open(papers_file, 'r', encoding='utf-8') as f:
            papers_data = json.load(f)
        
        # Extract just the papers array
        papers = papers_data.get('papers', [])
        
        # Filter to only the required fields
        required_fields = ['arxiv_id', 'categories', 'title', 'authors', 'abstract', 'submitted_date_parsed']
        filtered_papers = []
        
        for paper in papers:
            filtered_paper = {}
            for field in required_fields:
                filtered_paper[field] = paper.get(field)
            filtered_papers.append(filtered_paper)
        
        print(f"  📄 Loaded and filtered {len(filtered_papers)} papers")
        return filtered_papers
        
    except Exception as e:
        print(f"  ⚠️  Error reading category papers: {e}")
        return []

def extract_summary_title_and_phrase(markdown_content: str, filename: str):
    """Extract title from markdown content and determine the corresponding phrase."""
    if not markdown_content:
        return 'Summary', None
    
    # Extract H1 title from markdown
    h1_match = re.search(r'^#\s+(.+)', markdown_content, re.MULTILINE)
    if h1_match:
        # Clean up the title by removing extra text after colons
        title = h1_match.group(1).strip()
        # Remove patterns like ": A Tsunami of Innovation..." or similar
        title = re.sub(r':\s*.+$', '', title)
        
        # Extract phrase from filename (format: rank_phrase.md)
        filename_match = re.match(r'^\d+_(.+)\.md$', filename)
        if filename_match:
            phrase = filename_match.group(1).replace('_', ' ')
            return title, phrase
        
        return title, None
    
    return 'Summary', None

def clean_content_for_audio(content: str):
    """Remove hyperlinks and other unwanted formatting from content for audio generation."""
    if not content:
        return ""
    
    # Remove double bracket hyperlinks in format [[text](url)] - remove completely
    cleaned_content = re.sub(r'\[\[([^\]]+)\]\([^\)]+\)\]', '', content)
    
    # Remove single bracket hyperlinks in format [text](url) as backup - remove completely
    cleaned_content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', '', cleaned_content)
    
    # Remove any remaining markdown formatting that might interfere with audio
    # Remove headers (# ## ###)
    cleaned_content = re.sub(r'^#+\s+', '', cleaned_content, flags=re.MULTILINE)
    
    # Remove bold/italic formatting
    cleaned_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned_content)
    cleaned_content = re.sub(r'\*([^*]+)\*', r'\1', cleaned_content)
    
    # Clean up extra spaces that might result from removing hyperlinks
    cleaned_content = re.sub(r'\s+', ' ', cleaned_content)
    
    # Remove extra whitespace and newlines
    cleaned_content = re.sub(r'\n\s*\n', '\n\n', cleaned_content)
    cleaned_content = cleaned_content.strip()
    
    return cleaned_content

def split_content_into_sentences(content: str):
    """Split content into individual sentences for audio generation."""
    # Split by sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    # Filter out empty sentences and clean them up
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 10:  # Skip very short fragments
            cleaned_sentences.append(sentence)
    
    return cleaned_sentences

def generate_audio_for_summary(content: str, title: str, category_name: str, phrase: str, daily_feed_dir: Path):
    """Generate audio file for a summary and return the relative path."""
    try:
        # Clean the content for audio generation
        cleaned_content = clean_content_for_audio(content)
        
        if not cleaned_content:
            print(f"  ⚠️  No content to generate audio for: {title}")
            return None
        
        # Create audio subdirectory
        audio_dir = daily_feed_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a safe filename
        safe_phrase = re.sub(r'[^\w\s-]', '', phrase or 'summary').strip()
        safe_phrase = re.sub(r'[-\s]+', '_', safe_phrase)
        safe_category = re.sub(r'[^\w\s-]', '', category_name).strip()
        safe_category = re.sub(r'[-\s]+', '_', safe_category)
        
        audio_filename = f"{safe_category}_{safe_phrase}.wav"
        audio_filepath = audio_dir / audio_filename
        
        # Split content into sentences for individual audio generation
        sentences = split_content_into_sentences(cleaned_content)
        print(f"  🎵 Generating audio for: {title} ({len(sentences)} sentences)")
        
        # Generate audio for each sentence
        audio_segments = []
        for i, sentence in enumerate(sentences):
            try:
                print(f"    Processing sentence {i+1}/{len(sentences)}...")
                generator = audio_pipeline([sentence], voice='af_heart')
                
                for gs, ps, audio in generator:
                    print(f"      Sentence {i+1}: gs={gs}, ps={ps}")
                    audio_segments.append(audio)
                    break  # We only have one text to process per sentence
                    
            except Exception as e:
                print(f"      ⚠️  Error generating audio for sentence {i+1}: {e}")
                continue
        
        if not audio_segments:
            print(f"  ⚠️  No audio segments generated for: {title}")
            return None
        
        # Combine all audio segments
        import numpy as np
        combined_audio = np.concatenate(audio_segments)
        
        # Save combined audio
        sf.write(str(audio_filepath), combined_audio, 24000)
        print(f"    ✅ Combined {len(audio_segments)} audio segments into final file")
        
        # Return relative path for frontend
        return f"/daily_feed/audio/{audio_filename}"
        
    except Exception as e:
        print(f"  ⚠️  Error generating audio for {title}: {e}")
        return None

def read_summary_files_with_metadata(summaries_dir: Path, phrases_summary_data, category_name: str, daily_feed_dir: Path):
    """Read all markdown summary files and return their contents with paper counts and audio."""
    summaries = []
    phrase_paper_counts = {}
    
    # Create a mapping from phrase to paper count
    if phrases_summary_data and 'phrases_summary' in phrases_summary_data:
        for phrase_info in phrases_summary_data['phrases_summary']:
            # Normalize phrase for matching
            normalized_phrase = phrase_info['phrase'].replace(' ', '_')
            phrase_paper_counts[normalized_phrase] = phrase_info['paper_count']
    
    if summaries_dir.exists():
        md_files = sorted(summaries_dir.glob("*.md"))
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        title, phrase = extract_summary_title_and_phrase(content, md_file.name)
                        
                        # Get paper count for this phrase
                        paper_count = None
                        if phrase:
                            normalized_phrase = phrase.replace(' ', '_')
                            paper_count = phrase_paper_counts.get(normalized_phrase)
                        
                        # Generate audio for this summary
                        audio_url = generate_audio_for_summary(content, title, category_name, phrase, daily_feed_dir)
                        
                        summary_data = {
                            'content': content,
                            'title': title,
                            'phrase': phrase,
                            'paper_count': paper_count,
                            'audio_url': audio_url
                        }
                        summaries.append(summary_data)
                        
            except Exception as e:
                print(f"  ⚠️  Error reading summary file {md_file}: {e}")
    
    # Sort summaries by paper count in descending order (largest to smallest)
    summaries.sort(key=lambda x: x['paper_count'] or 0, reverse=True)
    
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
    
    # Load pipeline summary for paper counts
    pipeline_summary = load_pipeline_summary(date)
    if not pipeline_summary:
        print(f"❌ Could not load pipeline summary for date {date}")
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
        
        # Get paper count for this category
        category_paper_count = None
        if pipeline_summary and 'categories' in pipeline_summary:
            category_info = pipeline_summary['categories'].get(category_name)
            if category_info:
                category_paper_count = category_info.get('papers_count')
        
        # Load phrases summary for this category
        phrases_summary_data = load_phrases_summary(source_category_dir)
        
        # Load and filter category papers
        category_papers = load_category_papers(source_category_dir)
        
        # Read summaries with metadata and generate audio
        summaries_dir = source_category_dir / "summaries"
        summaries = read_summary_files_with_metadata(summaries_dir, phrases_summary_data, category_name, daily_feed_dir)
        
        # Copy word cloud image
        word_cloud_url = copy_images_to_frontend(source_category_dir, daily_feed_dir, category_name.replace(' ', '_').replace('(', '').replace(')', '').replace('.', ''))
        
        # Create category data
        category_data = {
            "category": category_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('.', ''),
            "display_name": category_name,
            "paper_count": category_paper_count,
            "word_cloud_url": word_cloud_url,
            "summaries": summaries,
            "papers": category_papers
        }
        
        categories_data.append(category_data)
        print(f"  ✅ Added {len(summaries)} summaries, {len(category_papers)} papers (filtered), total papers: {category_paper_count}, image: {'Yes' if word_cloud_url else 'No'}")
    
    # Sort categories by paper count in descending order (largest to smallest)
    categories_data.sort(key=lambda x: x['paper_count'] or 0, reverse=True)
    print(f"📊 Categories sorted by paper count (largest to smallest)")
    print(f"📊 Summaries within each category also sorted by paper count (largest to smallest)")
    print(f"📄 Papers data included with filtered fields: arxiv_id, categories, title, authors, abstract, submitted_date_parsed")
    print(f"🎵 Audio files generated sentence-by-sentence for all summaries")
    
    # Get total papers from pipeline summary
    total_papers = None
    if pipeline_summary and 'summary' in pipeline_summary:
        total_papers = pipeline_summary['summary'].get('total_papers')
    
    # Generate the final JSON structure
    daily_feed_data = {
        "date": date,
        "total_papers": total_papers,
        "categories": categories_data,
        "last_updated": datetime.now().isoformat(),
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
        print(f"📄 Each category includes filtered papers data (arxiv_id, categories, title, authors, abstract, submitted_date_parsed)")
        print(f"💡 The frontend will work without backend API calls!")
    else:
        print(f"\n❌ Failed to generate daily feed files")

if __name__ == "__main__":
    main() 