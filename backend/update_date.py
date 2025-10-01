#!/usr/bin/env python3
"""
Script to update published_date for papers from wrong_dates.csv
"""

import csv
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.db_models import DBPaper
from app.db.database import DATABASE_URL

def update_paper_dates(csv_file_path):
    """
    Update published_date for papers from CSV file
    
    Args:
        csv_file_path (str): Path to the wrong_dates.csv file
    """
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    
    try:
        # Read CSV file
        updated_count = 0
        not_found_count = 0
        error_count = 0
        
        print(f"Reading CSV file: {csv_file_path}")
        
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                try:
                    paper_id = row['paper_id'].strip()
                    published_date_str = row['published_date'].strip()
                    
                    # Parse the date
                    published_date = datetime.strptime(published_date_str, '%Y-%m-%d')
                    
                    # Check if paper exists in database
                    paper = session.query(DBPaper).filter(DBPaper.paper_id == paper_id).first()
                    
                    if paper:
                        # Update the published_date
                        paper.published_date = published_date
                        updated_count += 1
                        
                        if updated_count % 100 == 0:
                            print(f"Updated {updated_count} papers so far...")
                    else:
                        not_found_count += 1
                        print(f"Paper ID {paper_id} not found in database (row {row_num})")
                        
                except ValueError as e:
                    error_count += 1
                    print(f"Error parsing date for paper {paper_id} (row {row_num}): {e}")
                except Exception as e:
                    error_count += 1
                    print(f"Unexpected error for paper {paper_id} (row {row_num}): {e}")
        
        # Commit all changes
        session.commit()
        
        print(f"\nUpdate completed!")
        print(f"Successfully updated: {updated_count} papers")
        print(f"Papers not found: {not_found_count}")
        print(f"Errors: {error_count}")
        
    except Exception as e:
        session.rollback()
        print(f"Error during update: {e}")
        raise
    finally:
        session.close()

def main():
    """Main function"""
    csv_file_path = "/home/ec2-user/PMo/backend/wrong_dates.csv"
    
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file not found at {csv_file_path}")
        sys.exit(1)
    
    print("Starting paper date update process...")
    print(f"CSV file: {csv_file_path}")
    
    # Ask for confirmation
    print("\nThis will update published_date for papers in the database.")
    print("Make sure you have a backup of your database before proceeding!")
    response = input("Do you want to proceed with updating paper dates? (y/N): ")
    if response.lower() != 'y':
        print("Update cancelled.")
        sys.exit(0)
    
    update_paper_dates(csv_file_path)

if __name__ == "__main__":
    main()
