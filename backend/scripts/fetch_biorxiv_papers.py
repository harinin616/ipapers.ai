import os
import sys
import json
import time
import logging
import argparse
import requests
from datetime import date, timedelta, datetime

# Add the parent directory to the path so we can import modules from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fetch_biorxiv_papers")

# Constants
BIORXIV_API_BASE_URL = "https://api.biorxiv.org/details/biorxiv"
RESULTS_PER_PAGE = 100
BATCH_DELAY = 3  # seconds between API calls to avoid rate limiting


def fetch_papers_by_date(start_date, end_date, cursor=0):
    """
    Fetch bioRxiv papers for a specific date range using the official bioRxiv API.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        cursor (int): Starting position for pagination
        
    Returns:
        tuple: (list of paper data, total count, messages)
    """
    url = f"{BIORXIV_API_BASE_URL}/{start_date}/{end_date}/{cursor}"
    logger.info(f"Fetching papers from {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        collection = data.get('collection', [])
        messages = data.get('messages', [])
        total = int(messages[0].get('total', 0)) if messages else 0
        
        return collection, total, messages
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch papers: {e}", exc_info=True)
        return [], 0, []


def fetch_all_papers_for_date_range(start_date, end_date):
    """
    Fetch all bioRxiv papers for a given date range, handling pagination.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        list: All papers in the date range
    """
    all_papers = []
    cursor = 0
    total_fetched = 0
    
    # Get first batch and determine total
    batch, total_count, messages = fetch_papers_by_date(start_date, end_date, cursor)
    all_papers.extend(batch)
    total_fetched += len(batch)
    
    # Continue fetching if there are more papers
    while total_fetched < total_count:
        logger.info(f"Fetched {total_fetched} of {total_count} papers...")
        cursor += RESULTS_PER_PAGE
        time.sleep(BATCH_DELAY)  # Delay to avoid hitting rate limits
        
        batch, _, _ = fetch_papers_by_date(start_date, end_date, cursor)
        if not batch:
            logger.warning(f"No more papers returned at cursor {cursor}, stopping")
            break
            
        all_papers.extend(batch)
        total_fetched += len(batch)
    
    logger.info(f"Completed fetching {len(all_papers)} papers for {start_date} to {end_date}")
    return all_papers


def save_papers_to_json(papers, filename):
    """
    Save papers data to a JSON file
    
    Args:
        papers (list): List of paper data
        filename (str): Output filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        directory = os.path.dirname(filename)
        os.makedirs(directory, exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "papers": papers,
                "count": len(papers),
                "date_generated": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(papers)} papers to {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to save papers to {filename}: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(description='Fetch papers from bioRxiv')
    parser.add_argument('--days', type=int, default=1,
                      help='Number of days to fetch (default: 1)')
    parser.add_argument('--start-date', type=str,
                      help='Start date in YYYY-MM-DD format (overrides days parameter)')
    parser.add_argument('--end-date', type=str, default=date.today().isoformat(),
                      help=f'End date in YYYY-MM-DD format (default: today {date.today().isoformat()})')
    args = parser.parse_args()
    
    # Set up date range
    end_date = args.end_date
    if args.start_date:
        start_date = args.start_date
    else:
        start_date = (date.fromisoformat(end_date) - timedelta(days=args.days)).isoformat()
    
    logger.info(f"Fetching bioRxiv papers from {start_date} to {end_date}")
    
    # Determine output file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    output_filename = f"biorxiv_papers_{start_date}_to_{end_date}.json"
    output_path = os.path.join(data_dir, output_filename)
    
    # Fetch papers and save to file
    papers = fetch_all_papers_for_date_range(start_date, end_date)
    
    if papers:
        save_papers_to_json(papers, output_path)
        logger.info(f"Successfully processed {len(papers)} papers")
    else:
        logger.warning("No papers were fetched")
    
    logger.info("Script completed")


if __name__ == "__main__":
    main() 