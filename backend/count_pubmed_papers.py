#!/usr/bin/env python3
"""
Script to count number of papers with platform = 'pubmed'
"""

import sys
import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.db_models import DBPaper   # adjust if your model file is named differently
from app.db.database import DATABASE_URL   # must be defined in your project


def count_pubmed_papers():
    """
    Count all papers where platform = 'pubmed'
    """
    # Create database connection
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        count = session.query(func.count(DBPaper.paper_id)).filter(DBPaper.platform == "pubmed").scalar()
        print(f"Total records with platform='pubmed': {count}")
    except Exception as e:
        print(f"Error during count: {e}")
        raise
    finally:
        session.close()


def main():
    """Main function"""
    print("Counting papers with platform = 'pubmed'...")
    count_pubmed_papers()


if __name__ == "__main__":
    main()
