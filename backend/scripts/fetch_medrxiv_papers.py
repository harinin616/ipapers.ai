import os
import sys
import asyncio
import logging
import requests
import json
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fetch_medrxiv_papers")

from app.models.paper import Paper
from app.services.db_service import db_service
from app.services.vector_search_service import vector_search_service
from app.services.pdf_service import pdf_service

# Constants
MEDRXIV_API_BASE_URL = "https://api.biorxiv.org/pubs/medrxiv"
RESULTS_PER_PAGE = 100
BATCH_DELAY = 3  # seconds between API calls to avoid rate limiting
DEFAULT_DAYS = 3
MAX_RESULTS_PER_BATCH = 500


async def fetch_papers_batch(start_date, end_date, cursor=0):
    """
    Fetch medRxiv papers for a specific date range using the official medRxiv API.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        cursor (int): Starting position for pagination
        
    Returns:
        List of Paper objects
    """
    url = f"{MEDRXIV_API_BASE_URL}/{start_date}/{end_date}/{cursor}"
    logger.info(f"Fetching papers from {url}")
    
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url))
        response.raise_for_status()
        data = response.json()
        
        collection = data.get('collection', [])
        messages = data.get('messages', [])
        total = int(messages[0].get('total', 0)) if messages else 0
        
        # Convert to Paper objects
        papers = []
        for item in collection:
            try:
                # Log response for debugging
                logger.info(f"Processing paper with DOI: {item['preprint_doi']}")
                
                # medRxiv papers are hosted on the same platform as bioRxiv
                # Extract DOI suffix for PDF URL construction
                doi_suffix = item['preprint_doi'].split('/')[-1]
                pdf_url = f"https://www.medrxiv.org/content/10.1101/{doi_suffix}.full.pdf"
                logger.info(f"Generated PDF URL: {pdf_url}")
                
                # Map medRxiv fields to our Paper model
                paper_id = f"medrxiv_{item['preprint_doi'].replace('/', '_')}"
                
                # Convert dates from medRxiv format to datetime objects
                published_date = datetime.strptime(item['preprint_date'], '%Y-%m-%d')
                
                # Format authors - medRxiv returns a string with authors separated by semicolons
                authors = [a.strip() for a in item['preprint_authors'].split(';') if a.strip()]
                
                # Create Paper object
                paper = Paper(
                    paper_id=paper_id,
                    title=item['preprint_title'],
                    authors=authors,
                    abstract=item['preprint_abstract'],
                    categories=[item['preprint_category']] if item.get('preprint_category') else [],
                    pdf_url=pdf_url,
                    published_date=published_date,
                    updated_date=published_date,  # Use same date as published since medRxiv doesn't provide separate updated date
                    platform="medrxiv"
                )
                papers.append(paper)
            except Exception as e:
                logger.error(f"Error processing paper: {e}", exc_info=True)
        
        return papers, total
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch papers: {e}", exc_info=True)
        return [], 0


async def fetch_all_papers_for_date_range(start_date, end_date, max_results=MAX_RESULTS_PER_BATCH):
    """
    Fetch all medRxiv papers for a given date range, handling pagination.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        max_results (int): Maximum number of results to fetch
        
    Returns:
        list: All Paper objects in the date range
    """
    all_papers = []
    cursor = 0
    total_fetched = 0
    
    # Get first batch and determine total
    batch, total_count = await fetch_papers_batch(start_date, end_date, cursor)
    all_papers.extend(batch)
    total_fetched += len(batch)
    
    # Calculate how many results to fetch in total (either all available or max_results)
    target_count = min(total_count, max_results)
    
    # Continue fetching if there are more papers and we haven't reached our limit
    while total_fetched < target_count:
        logger.info(f"Fetched {total_fetched} of {target_count} papers...")
        cursor += RESULTS_PER_PAGE
        
        await asyncio.sleep(BATCH_DELAY)  # Delay to avoid hitting rate limits
        
        batch, _ = await fetch_papers_batch(start_date, end_date, cursor)
        if not batch:
            logger.warning(f"No more papers returned at cursor {cursor}, stopping")
            break
            
        all_papers.extend(batch)
        total_fetched += len(batch)
        
        # Stop if we've reached our maximum
        if total_fetched >= max_results:
            logger.info(f"Reached maximum result limit ({max_results})")
            break
    
    logger.info(f"Completed fetching {len(all_papers)} papers for {start_date} to {end_date}")
    return all_papers


async def fetch_papers(days=None):
    """
    Main function to fetch medRxiv papers for a specified number of days
    """
    if days is None:
        days = DEFAULT_DAYS
    
    today = date.today()
    earliest_date = today - timedelta(days=days)
    
    logger.info(f"Starting medRxiv paper fetch task")
    logger.info(f"Fetching papers from {earliest_date} to {today} ({days} days total)")
    
    total_fetched = 0
    total_added_db = 0
    all_fetched_paper_ids = []
    
    try:
        # Convert dates to string format required by medRxiv API
        end_date_str = today.isoformat()
        start_date_str = earliest_date.isoformat()
        
        # Fetch all papers in the date range
        batch_papers = await fetch_all_papers_for_date_range(
            start_date=start_date_str, 
            end_date=end_date_str,
            max_results=MAX_RESULTS_PER_BATCH
        )
        
        if not batch_papers:
            logger.info("No papers returned, exiting.")
            return
        
        # Extract paper IDs for tracking
        batch_paper_ids = [paper.paper_id for paper in batch_papers]
        all_fetched_paper_ids.extend(batch_paper_ids)
        logger.info(f"Accumulated {len(batch_paper_ids)} paper IDs")
        
        total_fetched += len(batch_papers)
        
        # Add papers to database and get IDs of newly added papers
        added_db_ids = await db_service.add_papers(batch_papers, platform="medrxiv")
        
        if not added_db_ids:
            logger.info("No new papers added to DB. All papers already exist.")
        
        # Filter papers to only those newly added
        new_papers = [p for p in batch_papers if p.paper_id in added_db_ids]
        
        # Add new papers to vector search index
        if new_papers:
            await vector_search_service.add_papers(new_papers)
        else:
            logger.info("No new papers for vector index, skipping add_papers()")
        
        total_added_db += len(added_db_ids)
        logger.info(f"Fetched {len(batch_papers)} papers, added {len(added_db_ids)} new papers to DB and vector search.")
        
        # Generate embeddings for new papers
        if new_papers:
            logger.info(f"Generating embeddings for {len(new_papers)} newly added papers")
            for p in new_papers:
                try:
                    pid = p.paper_id
                    ok = await pdf_service.generate_embeddings_for_paper(pid, "medrxiv")
                    if ok:
                        logger.info(f"Generated embeddings for paper {pid}")
                    else:
                        logger.warning(f"Failed to generate embeddings for paper {pid}")
                except Exception as e:
                    logger.error(f"Error generating embeddings for paper {p.paper_id}: {e}", exc_info=True)
        else:
            logger.info("No new papers to generate embeddings for")
        
        logger.info(f"Total fetched: {total_fetched} papers, added to DB: {total_added_db} new papers.")
        
            
    except Exception as e:
        logger.error(f"Error occurred during fetch_papers task: {e}", exc_info=True)
        if all_fetched_paper_ids:
            logger.info("Saving accumulated paper IDs despite error...")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fetch papers from medRxiv')
    parser.add_argument('--days', type=int, default=None, 
                       help=f'Number of days to fetch (default: {DEFAULT_DAYS})')
    args = parser.parse_args()
    
    logger.info(f"args: {args.days}")
    logger.info("=" * 80)
    logger.info("Starting medRxiv paper fetch script")
    logger.info(f"Configuration: Default days={DEFAULT_DAYS}, API delay={BATCH_DELAY} seconds")
    logger.info(f"Max results per fetch: {MAX_RESULTS_PER_BATCH}")

    await fetch_papers(days=args.days)
    
    logger.info("medRxiv paper fetch script completed")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main()) 