#!/usr/bin/env python3
"""
Daily Tree Generator - Create dendrograms from daily arXiv feed abstracts

This script reads JSON data from daily_feed/data, generates embeddings for abstracts
using SPECTER2 model, and performs Ward's agglomerative clustering to create dendrograms.
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

def create_dendrogram(embeddings, papers, date, method='ward'):
    """Create dendrogram using Ward's hierarchical clustering"""
    print(f"🌳 Creating dendrogram using {method} linkage")
    
    # Calculate distance matrix
    distance_matrix = cosine_distances(embeddings)
    
    # Convert to condensed distance matrix for linkage
    condensed_distances = squareform(distance_matrix, checks=False)
    
    # Perform hierarchical clustering
    linkage_matrix = linkage(condensed_distances, method=method)
    
    # Create dendrogram
    plt.figure(figsize=(20, 10))
    
    # Create labels from paper titles (truncated for readability)
    labels = [f"{paper['arxiv_id']}: {paper['title'][:50]}..." for paper in papers]
    
    dendrogram_data = dendrogram(
        linkage_matrix,
        labels=labels,
        orientation='top',
        distance_sort='descending',
        show_leaf_counts=True,
        leaf_rotation=90,
        leaf_font_size=8
    )
    
    plt.title(f'Hierarchical Clustering Dendrogram - {date}\n'
              f'Papers: {len(papers)}, Method: {method.title()}, Model: SPECTER2', 
              fontsize=16, fontweight='bold')
    plt.xlabel('Paper Index / arXiv ID: Title', fontsize=12)
    plt.ylabel('Distance', fontsize=12)
    
    # Improve layout
    plt.tight_layout()
    
    # Save the dendrogram
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    dendrogram_path = output_dir / f"dendrogram_{date}.png"
    plt.savefig(dendrogram_path, dpi=300, bbox_inches='tight')
    print(f"   Saved dendrogram to: {dendrogram_path}")
    
    # Also save as PDF for vector graphics
    dendrogram_pdf = output_dir / f"dendrogram_{date}.pdf"
    plt.savefig(dendrogram_pdf, bbox_inches='tight')
    print(f"   Saved dendrogram (PDF) to: {dendrogram_pdf}")
    
    plt.show()
    
    return linkage_matrix, dendrogram_data

def save_clustering_data(papers, embeddings, linkage_matrix, date):
    """Save clustering data for further analysis"""
    print("💾 Saving clustering data")
    
    output_dir = Path("output")
    
    # Save embeddings
    embeddings_path = output_dir / f"embeddings_{date}.npy"
    np.save(embeddings_path, embeddings)
    print(f"   Saved embeddings to: {embeddings_path}")
    
    # Save linkage matrix
    linkage_path = output_dir / f"linkage_matrix_{date}.npy"
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
    metadata_path = output_dir / f"paper_metadata_{date}.csv"
    metadata_df.to_csv(metadata_path, index=False)
    print(f"   Saved paper metadata to: {metadata_path}")
    
    # Save clustering summary
    summary = {
        'date': date,
        'total_papers': len(papers),
        'embedding_dimension': embeddings.shape[1],
        'clustering_method': 'ward',
        'model_used': 'allenai/specter2_base',
        'files_generated': {
            'dendrogram_png': str(output_dir / f"dendrogram_{date}.png"),
            'dendrogram_pdf': str(output_dir / f"dendrogram_{date}.pdf"),
            'embeddings': str(embeddings_path),
            'linkage_matrix': str(linkage_path),
            'metadata': str(metadata_path)
        }
    }
    
    summary_path = output_dir / f"clustering_summary_{date}.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"   Saved clustering summary to: {summary_path}")

def main():
    """Main function to orchestrate the daily tree generation"""
    # Set up argument parser (similar to collect_data.py)
    parser = argparse.ArgumentParser(description='Generate hierarchical clustering dendrogram for daily arXiv papers')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Date in YYYY-MM-DD format (default: yesterday)')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    print("🌳 Daily Tree Generator")
    print("=" * 50)
    print(f"📅 Processing papers for date: {args.date}")
    
    try:
        # Load papers data
        papers = load_papers_data(args.date)
        
        if not papers:
            print("❌ No papers with abstracts found for the given date.")
            return
        
        # Generate embeddings
        embeddings = generate_embeddings(papers)
        
        # Create dendrogram
        linkage_matrix, dendrogram_data = create_dendrogram(embeddings, papers, args.date)
        
        # Save all data for further analysis
        save_clustering_data(papers, embeddings, linkage_matrix, args.date)
        
        print("\n✅ Daily tree generation completed successfully!")
        print(f"   You can use the saved linkage matrix and embeddings for further analysis.")
        print(f"   Files are saved in the 'output/' directory.")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("   Make sure the daily_feed data has been collected for the specified date.")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Please check the error details and try again.")

if __name__ == "__main__":
    main() 