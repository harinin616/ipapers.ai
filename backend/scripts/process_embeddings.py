import os
import sys
import asyncio
import logging

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("process_embeddings")

from app.services.chat_service import chat_service

# Configuration
PROCESS_DELAY = 1  


def load_paper_ids(data_dir):
    """Load paper IDs from the saved file"""
    try:
        file_path = os.path.join(data_dir, 'latest_paper_ids.txt')
        
        if not os.path.exists(file_path):
            logger.error(f"Paper IDs file not found: {file_path}")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            paper_ids = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(paper_ids)} paper IDs")
        return paper_ids
        
    except Exception as e:
        logger.error(f"Failed to load paper IDs: {e}")
        return []


async def process_single_paper(paper_id: str) -> bool:
    try:
        success = await chat_service.process_embeddings(paper_id, "arxiv")
        if not success:
            logger.warning(f"Failed to process: {paper_id}")
        return success
        
    except Exception as e:
        logger.error(f"Error processing {paper_id}: {e}")
        return False


async def process_embeddings_batch(paper_ids: list):
    total_papers = len(paper_ids)
    success_count = 0
    
    logger.info(f"Processing {total_papers} papers")
    
    # Process papers one by one
    for i, paper_id in enumerate(paper_ids):
        logger.info(f"Processing {i+1}/{total_papers}: {paper_id}")
        
        success = await process_single_paper(paper_id)
        if success:
            success_count += 1
        
        # Delay between papers (except for the last one)
        if i < total_papers - 1:
            await asyncio.sleep(PROCESS_DELAY)
    
    return success_count, total_papers


async def process_embeddings():
    try:
        # Setup data directory path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, '..', 'data')
        
        # Load paper IDs
        paper_ids = load_paper_ids(data_dir)
        
        if not paper_ids:
            logger.warning("No paper IDs found to process")
            return
        
        # Process embeddings
        success_count, total_count = await process_embeddings_batch(paper_ids)
        
        # Final summary
        failure_count = total_count - success_count
        
        logger.info(f"Processing completed: {success_count}/{total_count}")
        
    except Exception as e:
        logger.error(f"Error in main processing: {e}")


async def main():
    logger.info("Starting embedding processing")
    await process_embeddings()
    logger.info("Embedding processing completed")


if __name__ == "__main__":
    asyncio.run(main()) 