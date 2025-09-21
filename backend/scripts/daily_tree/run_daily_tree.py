#!/usr/bin/env python3
"""
Daily Tree Generator - Create dendrograms from daily arXiv feed abstracts

This script reads JSON data from daily_feed/data, generates embeddings for abstracts
using SPECTER2 model, and performs Ward's agglomerative clustering to create dendrograms
for each subject category.
"""

import json
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics.pairwise import cosine_distances
import seaborn as sns
import torch
from transformers import AutoModel, AutoTokenizer
import os
import warnings
warnings.filterwarnings('ignore')

def load_papers_data(date):
    """Load papers data from JSON file for the given date"""
    # Calculate the to_date (next day)
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    to_date_obj = date_obj + timedelta(days=1)
    to_date = to_date_obj.strftime('%Y-%m-%d')
    
    # Construct the JSON file path using relative path
    json_file = Path(f"../daily_feed/data/{date}-{to_date}.json")
    
    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")
    
    print(f"📖 Loading papers data from {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        papers = json.load(f)
    
    # Filter papers that have abstracts
    papers_with_abstracts = [p for p in papers if p.get('abstract') and p.get('abstract').strip()]
    
    print(f"   Total papers: {len(papers)}")
    print(f"   Papers with abstracts: {len(papers_with_abstracts)}")
    
    return papers_with_abstracts

def categorize_papers_by_discipline(papers):
    """Group papers by their primary discipline using the same logic as daily_feed"""
    discipline_groups = {
        'Computer Science (cs.)': [],
        'Economics (econ.)': [],
        'Electrical Engineering & Systems Science (eess.)': [],
        'Mathematics (math.)': [],
        'Statistics (stat.)': [],
        'Quantitative Biology (q-bio.)': [],
        'Quantitative Finance (q-fin.)': [],
        'Physics': []
    }
    
    for paper in papers:
        categories = paper.get('categories', [])
        if categories:
            # Use first category to determine discipline
            first_category = categories[0]
            
            # Categorize using the same logic as daily_feed
            if first_category.startswith('cs.'):
                discipline_groups['Computer Science (cs.)'].append(paper)
            elif first_category.startswith('econ.'):
                discipline_groups['Economics (econ.)'].append(paper)
            elif first_category.startswith('eess.'):
                discipline_groups['Electrical Engineering & Systems Science (eess.)'].append(paper)
            elif first_category.startswith('math.'):
                discipline_groups['Mathematics (math.)'].append(paper)
            elif first_category.startswith('stat.'):
                discipline_groups['Statistics (stat.)'].append(paper)
            elif first_category.startswith('q-bio.'):
                discipline_groups['Quantitative Biology (q-bio.)'].append(paper)
            elif first_category.startswith('q-fin.'):
                discipline_groups['Quantitative Finance (q-fin.)'].append(paper)
            else:
                discipline_groups['Physics'].append(paper)
    
    # Only return categories that have papers
    return {k: v for k, v in discipline_groups.items() if v}

def generate_embeddings(papers, model_name="allenai/specter2_base", batch_size=32):
    """Generate embeddings for paper abstracts using SPECTER2 model"""
    print(f"🤖 Generating embeddings using {model_name}")
    
    # Set device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"   Using device: {device}")
    
    # Load the SPECTER2 model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = (
        AutoModel
        .from_pretrained(model_name, trust_remote_code=True)
        .to(device)
        .eval()
    )
    
    # Use FP16 to save memory if using CUDA
    if device == "cuda":
        model = model.half()
    
    # Prepare abstracts for embedding
    abstracts = [paper['abstract'] for paper in papers]
    
    print(f"   Processing {len(abstracts)} abstracts in batches of {batch_size}")
    
    all_embeddings = []
    total_batches = (len(abstracts) + batch_size - 1) // batch_size
    
    # Process in batches
    for i in range(0, len(abstracts), batch_size):
        batch = abstracts[i:i + batch_size]
        batch_idx = i // batch_size + 1
        
        print(f"   Processing batch {batch_idx}/{total_batches}")
        
        with torch.inference_mode():
            inputs = tokenizer(
                batch,
                truncation=True,
                padding=True,
                max_length=model.config.max_position_embeddings,
                return_tensors="pt"
            ).to(device)
            
            outputs = model(**inputs)
            # SPECTER-2 uses pooler_output for embeddings
            vecs = outputs.pooler_output  # (batch_size, 768)
            all_embeddings.append(vecs.detach().cpu())
    
    # Concatenate all batches
    embeddings = torch.cat(all_embeddings, dim=0).numpy()
    
    print(f"   Generated embeddings shape: {embeddings.shape}")
    
    return embeddings

def create_dendrogram_for_category(embeddings, papers, category, date, method='ward'):
    """Create dendrogram for a specific category using Ward's hierarchical clustering"""
    print(f"🌳 Creating dendrogram for {category} using {method} linkage")
    
    # Calculate distance matrix
    distance_matrix = cosine_distances(embeddings)
    
    # Convert to condensed distance matrix for linkage
    condensed_distances = squareform(distance_matrix, checks=False)
    
    # Perform hierarchical clustering
    linkage_matrix = linkage(condensed_distances, method=method)
    
    # Create dendrogram
    plt.figure(figsize=(20, 10))
    
    # Create labels from paper titles (truncated for readability)
    labels = [f"{paper['arxiv_id']}: {paper['title'][:40]}..." for paper in papers]
    
    dendrogram_data = dendrogram(
        linkage_matrix,
        labels=labels,
        orientation='top',
        distance_sort='descending',
        show_leaf_counts=True,
        leaf_rotation=90,
        leaf_font_size=8
    )
    
    plt.title(f'Hierarchical Clustering Dendrogram - {category}\n'
              f'Date: {date}, Papers: {len(papers)}, Method: {method.title()}, Model: SPECTER2', 
              fontsize=16, fontweight='bold')
    plt.xlabel('Paper Index / arXiv ID: Title', fontsize=12)
    plt.ylabel('Distance', fontsize=12)
    
    # Improve layout
    plt.tight_layout()
    
    # Create category-specific output directory
    category_output_dir = Path("output") / "each_subject" / category
    category_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the dendrogram
    dendrogram_path = category_output_dir / f"dendrogram_{date}.png"
    plt.savefig(dendrogram_path, dpi=300, bbox_inches='tight')
    print(f"   Saved dendrogram to: {dendrogram_path}")
    
    # Also save as PDF for vector graphics
    dendrogram_pdf = category_output_dir / f"dendrogram_{date}.pdf"
    plt.savefig(dendrogram_pdf, bbox_inches='tight')
    print(f"   Saved dendrogram (PDF) to: {dendrogram_pdf}")
    
    # Don't show the plot in non-interactive environments
    # plt.show()
    plt.close()  # Close to free memory
    
    return linkage_matrix, dendrogram_data

def save_clustering_data_for_category(papers, embeddings, linkage_matrix, category, date):
    """Save clustering data for a specific category"""
    print(f"💾 Saving clustering data for {category}")
    
    # Create category-specific output directory
    category_output_dir = Path("output") / "each_subject" / category
    category_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save embeddings
    embeddings_path = category_output_dir / f"embeddings_{date}.npy"
    np.save(embeddings_path, embeddings)
    print(f"   Saved embeddings to: {embeddings_path}")
    
    # Save linkage matrix
    linkage_path = category_output_dir / f"linkage_matrix_{date}.npy"
    np.save(linkage_path, linkage_matrix)
    print(f"   Saved linkage matrix to: {linkage_path}")
    
    # Create and save paper metadata
    paper_metadata = []
    for i, paper in enumerate(papers):
        metadata = {
            'index': i,
            'arxiv_id': paper['arxiv_id'],
            'title': paper['title'],
            'authors': paper['authors'],
            'categories': paper['categories'],
            'abstract_length': len(paper['abstract']),
            'date': paper.get('submitted_date_parsed', ''),
        }
        paper_metadata.append(metadata)
    
    metadata_df = pd.DataFrame(paper_metadata)
    metadata_path = category_output_dir / f"paper_metadata_{date}.csv"
    metadata_df.to_csv(metadata_path, index=False)
    print(f"   Saved paper metadata to: {metadata_path}")
    
    # Save clustering summary
    summary = {
        'date': date,
        'category': category,
        'total_papers': len(papers),
        'embedding_dimension': embeddings.shape[1],
        'clustering_method': 'ward',
        'model_used': 'allenai/specter2_base',
        'files_generated': {
            'dendrogram_png': str(category_output_dir / f"dendrogram_{date}.png"),
            'dendrogram_pdf': str(category_output_dir / f"dendrogram_{date}.pdf"),
            'embeddings': str(embeddings_path),
            'linkage_matrix': str(linkage_path),
            'metadata': str(metadata_path)
        }
    }
    
    summary_path = category_output_dir / f"clustering_summary_{date}.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"   Saved clustering summary to: {summary_path}")

def main():
    """Main function to orchestrate the daily tree generation for each subject"""
    # Set up argument parser (similar to collect_data.py)
    parser = argparse.ArgumentParser(description='Generate hierarchical clustering dendrograms for daily arXiv papers by subject')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Date in YYYY-MM-DD format (default: yesterday)')
    parser.add_argument('--min-papers', type=int, default=3,
                       help='Minimum number of papers required per category to generate dendrogram (default: 3)')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    print("🌳 Daily Tree Generator (By Subject)")
    print("=" * 60)
    print(f"📅 Processing papers for date: {args.date}")
    print(f"📊 Minimum papers per category: {args.min_papers}")
    
    try:
        # Load papers data
        papers = load_papers_data(args.date)
        
        if not papers:
            print("❌ No papers with abstracts found for the given date.")
            return
        
        # Categorize papers by discipline
        print(f"\n📂 Categorizing papers by discipline...")
        category_papers = categorize_papers_by_discipline(papers)
        
        print(f"📊 Found {len(category_papers)} categories:")
        for category, cat_papers in category_papers.items():
            print(f"  - {category}: {len(cat_papers)} papers")
        
        # Filter categories with enough papers
        valid_categories = {k: v for k, v in category_papers.items() if len(v) >= args.min_papers}
        
        if not valid_categories:
            print(f"\n❌ No categories have at least {args.min_papers} papers. Cannot generate dendrograms.")
            return
        
        print(f"\n🔄 Processing {len(valid_categories)} categories with sufficient papers...")
        
        # Process each category separately
        all_results = {}
        
        for category, cat_papers in valid_categories.items():
            print(f"\n{'='*50}")
            print(f"📊 Processing category: {category} ({len(cat_papers)} papers)")
            print(f"{'='*50}")
            
            # Generate embeddings for this category
            embeddings = generate_embeddings(cat_papers)
            
            if embeddings is None:
                print(f"❌ Failed to generate embeddings for {category}")
                continue
            
            # Create dendrogram for this category
            linkage_matrix, dendrogram_data = create_dendrogram_for_category(
                embeddings, cat_papers, category, args.date
            )
            
            # Save all data for this category
            save_clustering_data_for_category(
                cat_papers, embeddings, linkage_matrix, category, args.date
            )
            
            all_results[category] = {
                'papers_count': len(cat_papers),
                'embedding_shape': embeddings.shape,
                'linkage_shape': linkage_matrix.shape
            }
            
            print(f"✅ Completed processing for {category}")
        
        # Save overall summary
        overall_summary = {
            'date': args.date,
            'total_papers_processed': len(papers),
            'categories_processed': len(all_results),
            'min_papers_threshold': args.min_papers,
            'model_used': 'allenai/specter2_base',
            'clustering_method': 'ward',
            'categories': all_results
        }
        
        overall_output_dir = Path("output") / "each_subject"
        overall_summary_path = overall_output_dir / f"overall_summary_{args.date}.json"
        with open(overall_summary_path, 'w') as f:
            json.dump(overall_summary, f, indent=2)
        
        print(f"\n✅ Daily tree generation completed successfully!")
        print(f"📊 Processed {len(all_results)} categories:")
        for category, results in all_results.items():
            print(f"  - {category}: {results['papers_count']} papers")
        print(f"💾 Results saved in 'output/each_subject/' directory")
        print(f"📋 Overall summary saved to: {overall_summary_path}")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("   Make sure the daily_feed data has been collected for the specified date.")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Please check the error details and try again.")

if __name__ == "__main__":
    main() 