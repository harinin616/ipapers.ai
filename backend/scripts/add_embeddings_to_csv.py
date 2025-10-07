import os
import sys
import csv
import logging
import ast
import json
import numpy as np
from typing import List, Dict, Any

# Set default environment variables for embedding service
os.environ.setdefault("EMBEDDING_BATCH_SIZE", "100")
os.environ.setdefault("SPECTER2_MODEL", "allenai/specter2_base")
os.environ.setdefault("EMBEDDING_DIMENSIONS", "768")

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_service import llm_service

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("csv_embedding_calculator")


def read_papers_from_csv(csv_file_path: str) -> List[Dict[str, Any]]:
    """Read papers from CSV file"""
    papers = []
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                try:
                    authors_str = row.get('authors', '')
                    authors = ast.literal_eval(authors_str) if authors_str else []
                    if not isinstance(authors, list):
                        authors = [str(authors)]

                    categories_str = row.get('categories', '')
                    if categories_str.startswith('[') and categories_str.endswith(']'):
                        categories_str = categories_str[1:-1]
                        categories = [cat.strip().strip('"\'') for cat in categories_str.split(',')]
                    else:
                        categories = [categories_str]

                    paper_data = {
                        'paper_id': row.get('paper_id', ''),
                        'title': row.get('title', ''),
                        'authors': authors,
                        'abstract': row.get('abstract', ''),
                        'categories': categories,
                        'pdf_url': row.get('pdf_url', ''),
                        'published_date': row.get('published_date', ''),
                        'updated_date': row.get('updated_date', ''),
                        'platform': row.get('platform', 'pubmed')
                    }

                    # Preserve existing embeddings if present
                    paper_data['db_embedding'] = row.get('db_embedding', None)
                    paper_data['vector_embedding'] = row.get('vector_embedding', None)

                    papers.append(paper_data)
                except Exception as e:
                    logger.error(f"Error parsing row {row_num}: {e}")
                    continue
        logger.info(f"Successfully read {len(papers)} papers from CSV")
        return papers
    except Exception as e:
        logger.error(f"Failed to read CSV file {csv_file_path}: {e}", exc_info=True)
        return []


async def calculate_embeddings_for_papers(papers: List[Dict[str, Any]]) -> tuple[List[Any], List[Any], List[int]]:
    """Calculate embeddings and handle failures"""
    if not papers:
        return [], [], []

    db_texts = [f"{p['title']}\n\n{p['abstract'] or ''}".strip() for p in papers]
    vector_texts = [f"{p['title']} {p['abstract'] or ''}".strip() for p in papers]

    db_embeddings = [None] * len(papers)
    vector_embeddings = [None] * len(papers)
    failed_indices = []

    try:
        logger.info("Generating DB embeddings...")
        db_raw = await llm_service.get_embeddings(db_texts)
        if db_raw is None:
            failed_indices = list(range(len(papers)))
        else:
            db_array = np.array(db_raw, dtype='float32')
            db_embeddings = [db_array[i] for i in range(len(papers))]

        logger.info("Generating Vector embeddings...")
        vec_raw = await llm_service.get_embeddings(vector_texts)
        if vec_raw is None:
            failed_indices = list(range(len(papers)))
        else:
            vec_array = np.array(vec_raw, dtype='float32')
            vec_array = vec_array / np.linalg.norm(vec_array, axis=1, keepdims=True)
            vec_array = vec_array.astype('float32')
            vector_embeddings = [vec_array[i] for i in range(len(papers))]

    except Exception as e:
        logger.error(f"Error during embedding calculation: {e}")
        failed_indices = list(range(len(papers)))

    return db_embeddings, vector_embeddings, failed_indices


def append_embeddings_to_csv(
    csv_file_path: str,
    papers: List[Dict[str, Any]],
    db_embeddings: List[Any],
    vector_embeddings: List[Any],
    failed_indices: List[int]
):
    """Append embeddings to the same CSV file (in-place)"""
    temp_path = csv_file_path + ".tmp"
    try:
        with open(temp_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = list(papers[0].keys())
            if 'db_embedding' not in fieldnames:
                fieldnames.append('db_embedding')
            if 'vector_embedding' not in fieldnames:
                fieldnames.append('vector_embedding')

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for i, (paper, db_emb, vec_emb) in enumerate(zip(papers, db_embeddings, vector_embeddings)):
                row = paper.copy()
                row['db_embedding'] = json.dumps(db_emb.tolist()) if db_emb is not None else "null"
                row['vector_embedding'] = json.dumps(vec_emb.tolist()) if vec_emb is not None else "null"
                writer.writerow(row)

        os.replace(temp_path, csv_file_path)
        logger.info(f"✅ Appended embeddings in-place to {csv_file_path}")
        logger.info(f"{len(papers) - len(failed_indices)} embeddings succeeded, {len(failed_indices)} failed.")

    except Exception as e:
        logger.error(f"Failed to append embeddings to CSV: {e}", exc_info=True)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        logger.error("Please provide the CSV file path as an argument.")
        sys.exit(1)

    input_csv_path = sys.argv[1]

    if not os.path.exists(input_csv_path):
        logger.error(f"CSV file not found: {input_csv_path}")
        sys.exit(1)

    papers = read_papers_from_csv(input_csv_path)
    if not papers:
        logger.error("No papers found in CSV.")
        sys.exit(1)

    db_embeddings, vector_embeddings, failed_indices = await calculate_embeddings_for_papers(papers)
    append_embeddings_to_csv(input_csv_path, papers, db_embeddings, vector_embeddings, failed_indices)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
