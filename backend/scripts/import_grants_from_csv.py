import os
import sys
import asyncio
import csv
import logging
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("import_grants_from_csv")

from app.models.grant import Grant
from app.services.grant_db_service import grant_db_service


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string in various formats"""
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    # Try common date formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Strip timezone info to match DB expectations
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def csv_row_to_grant(row: dict) -> Optional[Grant]:
    """Convert CSV row to Grant object"""
    print(row)
    try:
        grant_id = row.get('opportunity_id') or row.get('opportunity_number', '').strip()
        if not grant_id:
            logger.warning("No grant ID found in row, skipping")
            return None
        
        title = row.get('opportunity_title', '').strip()
        if not title:
            title = "Untitled Grant"
        
        agency = row.get('agency_name', '').strip()
        if not agency:
            agency = row.get('top_level_agency_name', '').strip()
        if not agency:
            agency = "Unknown Agency"
        
        synopsis = row.get('summary_description', '').strip()
        
        # Parse dates
        posted_date = parse_date(row.get('post_date', ''))
        close_date = parse_date(row.get('close_date', ''))
        updated_date = parse_date(row.get('updated_at', ''))
        
        # Use posted_date as fallback for updated_date
        if not updated_date and posted_date:
            updated_date = posted_date
        
        # Use posted_date as fallback for posted_date if not available
        if not posted_date:
            posted_date = datetime.utcnow()
        
        # Build detail URL
        #detail_url = row.get('additional_info_url', '').strip()
        #if not detail_url:
            #detail_url = f"https://simpler.grants.gov/opportunity/{grant_id}"
        detail_url = f"https://simpler.grants.gov/opportunity/{grant_id}"
        
        # Categories from various fields
        categories = []
        for field in ['category', 'funding_categories', 'opportunity_assistance_listings']:
            value = row.get(field, '').strip()
            if value:
                categories.append(value)
        
        # Status
        status = row.get('opportunity_status', '').strip()
        
        grant = Grant(
            grant_id=grant_id,
            title=title,
            agency=agency,
            synopsis=synopsis,
            categories=categories if categories else None,
            detail_url=detail_url,
            posted_date=posted_date,
            updated_date=updated_date,
            close_date=close_date,
            status=status,
        )
        
        return grant
        
    except Exception as e:
        logger.error(f"Error converting CSV row to Grant: {e}", exc_info=True)
        return None


async def import_grants_from_csv(csv_path: str) -> int:
    """Import grants from CSV file"""
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return 0
    
    grants = []
    
    try:
        cnt = 0
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                cnt += 1
                if cnt == 10:
                    break
                grant = csv_row_to_grant(row)
                if grant:
                    grants.append(grant)
                else:
                    logger.warning(f"Skipped row {row_num}")
        
        if not grants:
            logger.warning("No valid grants found in CSV")
            return 0
        
        logger.info(f"Parsed {len(grants)} grants from CSV")
        
        # Insert into DB
        added_ids = await grant_db_service.add_grants(grants)
        logger.info(f"Successfully added {len(added_ids)} grants to database")
        
        return len(added_ids)
        
    except Exception as e:
        logger.error(f"Error importing grants from CSV: {e}", exc_info=True)
        return 0


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Import grants from CSV to database')
    parser.add_argument('csv_path', help='Path to CSV file with grants data')
    args = parser.parse_args()
    
    logger.info(f"Starting import from {args.csv_path}")
    
    count = await import_grants_from_csv(args.csv_path)
    
    logger.info(f"Import completed. Added {count} grants to database")


if __name__ == '__main__':
    asyncio.run(main())