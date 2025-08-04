#!/usr/bin/env python3
import os
import sys
import logging
import re
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import database connection
from app.db.database import SessionLocal
# Import models
from app.models.db_models import DBPaper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def is_uuid_format(paper_id: str) -> bool:
    """
    Check if the paper_id is in UUID format
    UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """
    try:
        # Try to parse as UUID to validate format
        uuid.UUID(paper_id)
        return True
    except (ValueError, TypeError):
        return False


def update_platform_for_paper(paper_id: str, old_platform: str, new_platform: str = "upload") -> bool:
    """
    Update platform for a single paper and its associated records
    Use raw SQL to execute updates with temporarily disabled foreign key constraints
    """
    db = SessionLocal()
    try:
        # Begin transaction
        db.begin()
        
        # Temporarily disable foreign key constraints
        db.execute(text("SET session_replication_role = 'replica';"))
        
        # 1. Update papers table
        result = db.execute(
            text("""
            UPDATE papers
            SET platform = :new_platform
            WHERE paper_id = :paper_id AND platform = :old_platform
            """),
            {"paper_id": paper_id, "old_platform": old_platform, "new_platform": new_platform}
        )
        rows_updated_papers = result.rowcount
        
        # 2. Update paper_categories table
        db.execute(
            text("""
            UPDATE paper_categories
            SET platform = :new_platform
            WHERE paper_id = :paper_id AND platform = :old_platform
            """),
            {"paper_id": paper_id, "old_platform": old_platform, "new_platform": new_platform}
        )

        # 3. Update paper_authors table
        db.execute(
            text("""
            UPDATE paper_authors
            SET platform = :new_platform
            WHERE paper_id = :paper_id AND platform = :old_platform
            """),
            {"paper_id": paper_id, "old_platform": old_platform, "new_platform": new_platform}
        )

        # 4. Update user_files table
        db.execute(
            text("""
            UPDATE user_files
            SET platform = :new_platform
            WHERE paper_id = :paper_id AND platform = :old_platform
            """),
            {"paper_id": paper_id, "old_platform": old_platform, "new_platform": new_platform}
        )

        # Re-enable foreign key constraints
        db.execute(text("SET session_replication_role = 'origin';"))
        
        # Commit transaction
        db.commit()
        
        if rows_updated_papers > 0:
            logger.info(f"Successfully updated paper {paper_id} from '{old_platform}' to '{new_platform}'")
            return True
        else:
            logger.warning(f"No rows updated for paper {paper_id} (may have already been updated)")
            return True
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating paper {paper_id}: {str(e)}")
        return False
    finally:
        # Ensure foreign key constraints are re-enabled in any case
        try:
            db.execute(text("SET session_replication_role = 'origin';"))
            db.commit()
        except:
            pass
        db.close()


def update_uuid_platforms():
    """
    Update platform values to 'upload' for all papers with UUID format paper_id.
    Also update related foreign key tables.
    """
    db = SessionLocal()
    try:
        # Get all papers' ID and current platform
        papers_data = db.query(DBPaper.paper_id, DBPaper.platform).all()
        logger.info(f"Found {len(papers_data)} papers to process")

        # Close main session, each paper will be processed with independent transaction
        db.close()

        # Statistics
        total_checked = 0
        total_uuid_found = 0
        total_updated = 0
        total_errors = 0
        total_already_upload = 0
        
        # Process each paper
        for paper_id, current_platform in papers_data:
            total_checked += 1
            
            try:
                # Check if paper_id is in UUID format
                if is_uuid_format(paper_id):
                    total_uuid_found += 1
                    
                    # If platform is already 'upload', skip
                    if current_platform == "upload":
                        total_already_upload += 1
                        logger.debug(f"Paper {paper_id}: Already has platform 'upload', skipping")
                    else:
                        logger.info(f"Paper {paper_id}: Changing platform from '{current_platform}' to 'upload'")
                        
                        # Update paper and its associated records using independent transaction
                        if update_platform_for_paper(paper_id, current_platform, "upload"):
                            total_updated += 1
                        else:
                            total_errors += 1
                
                # Print progress every 100 papers
                if total_checked % 100 == 0:
                    logger.info(f"Progress: {total_checked}/{len(papers_data)} papers processed")
                
            except Exception as e:
                logger.error(f"Error processing paper {paper_id}: {str(e)}")
                total_errors += 1
        
        logger.info(f"""
Summary:
- Total papers checked: {total_checked}
- UUID format papers found: {total_uuid_found}
- Papers already with 'upload' platform: {total_already_upload}
- Papers updated to 'upload' platform: {total_updated}
- Errors encountered: {total_errors}
        """.strip())
        
    except Exception as e:
        logger.error(f"Transaction failed: {str(e)}")


if __name__ == "__main__":
    logger.info("Starting UUID papers platform update process...")
    logger.info("This script will update all UUID format paper_id platforms to 'upload'")
    
    # Confirmation prompt
    response = input("Are you sure you want to proceed? (y/N): ")
    if response.lower() in ['y', 'yes']:
        update_uuid_platforms()
        logger.info("UUID papers platform update process completed")
    else:
        logger.info("Operation cancelled by user") 