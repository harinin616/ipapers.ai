import os
import sys
import asyncio
import logging
import csv
from datetime import date, timedelta, datetime
from typing import List
import ast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fetch_papers")

try:
    from app.services.db_service import db_service
    from app.services.vector_search_service import vector_search_service
    from app.services.pdf_service import pdf_service
    from app.models.paper import Paper
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some services not available: {e}. Running in CSV-only mode.")
    SERVICES_AVAILABLE = False
    
    # Create a mock Paper class for testing
    class Paper:
        def __init__(self, paper_id, title, authors, abstract, categories=None, pdf_url="", published_date=None, updated_date=None, platform="pubmed"):
            self.paper_id = paper_id
            self.title = title
            self.authors = authors
            self.abstract = abstract
            self.categories = categories or []
            self.pdf_url = pdf_url
            self.published_date = published_date
            self.updated_date = updated_date
            self.platform = platform

BATCH_DAYS = 1
DEFAULT_DAYS = 3
BATCH_DELAY = 3
MAX_RESULTS_PER_BATCH = 10000


def save_paper_ids(paper_ids, data_dir):
    try:
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, 'latest_paper_ids.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            for paper_id in paper_ids:
                f.write(f"{paper_id}\n")
        logger.info(f"Saved {len(paper_ids)} total paper IDs to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save paper IDs to file: {e}", exc_info=True)


def read_papers_from_csv(csv_file_path: str) -> List[Paper]:
    """Read papers from CSV file and convert to Paper objects"""
    papers = []
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:

                    authors_str = row['authors']
                    try:
                        authors = ast.literal_eval(authors_str) if authors_str else []
                        if not isinstance(authors, list):
                            authors = [str(authors)]
                    except Exception:
                        authors = [authors_str] if authors_str else []


                    
                    categories_str = row['categories']
                    if categories_str.startswith('[') and categories_str.endswith(']'):
                        categories_str = categories_str[1:-1]  # Remove brackets
                        categories = [cat.strip().strip('"\'') for cat in categories_str.split(',')]
                    else:
                        categories = [categories_str]
                    
                    published_date = datetime.strptime(row['published_date'], '%Y-%m-%d').date()
                    updated_date = datetime.strptime(row['updated_date'], '%Y-%m-%d').date()
                    
                    paper = Paper(
                        paper_id=row['paper_id'],
                        title=row['title'],
                        authors=authors,
                        abstract=row['abstract'],
                        categories=categories,
                        pdf_url=row['pdf_url'],
                        published_date=published_date,
                        updated_date=updated_date,
                        platform=row['platform']
                    )
                    papers.append(paper)
                except Exception as e:
                    logger.error(f"Error parsing row {row}: {e}")
                    continue
                    
        logger.info(f"Successfully read {len(papers)} papers from CSV file")
        return papers
    except Exception as e:
        logger.error(f"Failed to read CSV file {csv_file_path}: {e}", exc_info=True)
        return []


_csv_papers = None
_csv_batch_index = 0
BATCH_SIZE = 100

async def fetch_papers_batch(start_date, end_date):
    global _csv_papers, _csv_batch_index
    
    logger.info(f"Reading batch from CSV file (batch #{_csv_batch_index + 1}, simulating dates {start_date} to {end_date})...")
    try:
        if _csv_papers is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            CSV_ROOT_DIR = "pubmed_csvs"  # <- set this to your actual folder
            CSV_FILE_NAME = "pubmed25n1274.csv"            # <- change this to the file you want to process
            csv_file_path = os.path.join(CSV_ROOT_DIR, CSV_FILE_NAME)
            _csv_papers = read_papers_from_csv(csv_file_path)
            logger.info(f"Read {len(_csv_papers)} total papers from CSV file (cached)")
        
        start_idx = _csv_batch_index * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(_csv_papers))
        
        if start_idx >= len(_csv_papers):
            logger.info("No more papers to process from CSV file")
            return []
        
        batch_papers = _csv_papers[start_idx:end_idx]
        logger.info(f"Returning batch {_csv_batch_index + 1}: papers {start_idx + 1}-{end_idx} ({len(batch_papers)} papers)")
        
        # Increment batch index for next call
        _csv_batch_index += 1
        
        return batch_papers
    except Exception as e:
        logger.error(f"Failed to read papers from CSV: {e}", exc_info=True)
        return []


async def fetch_papers(days=None):
    if days is None:
        days = DEFAULT_DAYS
    
    today = date.today()
    earliest_date = today - timedelta(days=days)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    
    logger.info(f"Starting paper fetch task")
    logger.info(f"Processing CSV file in batches of {BATCH_SIZE} papers")
    logger.info(f"Simulating date range {earliest_date} to {today}")
    
    total_fetched = 0
    total_added_db = 0
    batch_num = 1
    all_fetched_paper_ids = []
    
    try:
        # Process CSV file in batches
        while True:
            batch_papers = await fetch_papers_batch(
                start_date=earliest_date,
                end_date=today,
            )
            
            if not batch_papers:
                logger.info(f"No more papers to process. Finished processing CSV file.")
                break
            
            batch_paper_ids = [paper.paper_id for paper in batch_papers]
            all_fetched_paper_ids.extend(batch_paper_ids)
            logger.info(f"Batch {batch_num}: Accumulated {len(batch_paper_ids)} paper IDs (total so far: {len(all_fetched_paper_ids)})")
            
            total_fetched += len(batch_papers)
            
            if SERVICES_AVAILABLE:
                added_db_ids = await db_service.add_papers(batch_papers, platform="pubmed")
                
                if not added_db_ids:
                    logger.info(f"No new papers in batch {batch_num} added to DB. All papers already exist.")

                new_papers = [p for p in batch_papers if p.paper_id in added_db_ids]

                if new_papers:
                    await vector_search_service.add_papers(new_papers)
                else:
                    logger.info(f"Batch {batch_num}: no new papers for vector index, skipping add_papers()")
                total_added_db += len(added_db_ids)
                logger.info(f"Batch {batch_num}: Fetched {len(batch_papers)} papers, added {len(added_db_ids)} new papers to DB and vector search.")
            else:
                logger.info(f"Batch {batch_num}: CSV-only mode - read {len(batch_papers)} papers from CSV file")
                total_added_db += len(batch_papers)  # For display purposes

            # --- 新增：生成 embeddings ---
         #   logger.info(f"Generating embeddings for {len(batch_papers)} new papers")
          #  for p in batch_papers:
           #     try:
            #        pid= p.paper_id
             #       ok = await pdf_service.generate_embeddings_for_paper(pid, "pubmed")
              #      if ok:
               #         logger.info(f"Generated embeddings for paper {pid}")
                #    else:
                 #       logger.warning(f"Failed to generate embeddings for paper {pid}")
             #   except Exception as e:
              #      logger.error(f"Error generating embeddings for paper {pid}: {e}", exc_info=True)
            # ---------------------------

            batch_num += 1
            
            logger.info(f"Waiting {BATCH_DELAY} seconds before processing the next batch...")
            await asyncio.sleep(BATCH_DELAY)
        
        logger.info(f"Total fetched: {total_fetched} papers, added to DB: {total_added_db} new papers.")
        
        if all_fetched_paper_ids:
            save_paper_ids(all_fetched_paper_ids, data_dir)
        else:
            logger.info("No paper IDs to save - no papers were fetched.")
        
    except Exception as e:
        logger.error(f"Error occurred during fetch_papers task: {e}", exc_info=True)
        if all_fetched_paper_ids:
            logger.info("Saving accumulated paper IDs despite error...")
            save_paper_ids(all_fetched_paper_ids, data_dir)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fetch papers from CSV file (PubMed format)')
    parser.add_argument('--days', type=int, default=None)
    args = parser.parse_args()
    logger.info(f"args: {args.days}")
    logger.info("=" * 80)
    logger.info("Starting paper fetch script")
    logger.info(f"Configuration: Batch days={BATCH_DAYS}, Default days={DEFAULT_DAYS}, Batch delay={BATCH_DELAY} seconds")
    logger.info(f"Max results per batch: {MAX_RESULTS_PER_BATCH}")

    await fetch_papers(days=args.days)
    
    logger.info("Paper fetch script completed")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
