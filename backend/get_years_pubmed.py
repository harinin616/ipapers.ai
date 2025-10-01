#!/usr/bin/env python3
"""
Script to list unique publication years and counts for papers with platform = 'pubmed'
"""

import sys
import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.db_models import DBPaper   # adjust if your model file is named differently
from app.db.database import DATABASE_URL   # must be defined in your project


def get_pubmed_year_counts():
    """
    Get unique years and counts of papers with platform='pubmed'
    """
    # Create database connection
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # Query: group by year and count
        results = (
            session.query(
                func.extract("year", DBPaper.published_date).label("year"),
                func.count(DBPaper.paper_id).label("count")
            )
            .filter(DBPaper.platform == "pubmed")
            .group_by("year")
            .order_by("year")
            .all()
        )

        # Print nicely
        print("Publication counts by year for platform='pubmed':\n")
        for year, count in results:
            if year is not None:
                print(f"{int(year)}: {count} papers")

        return results

    except Exception as e:
        print(f"Error while fetching years and counts: {e}")
        raise
    finally:
        session.close()


def main():
    """Main function"""
    print("Fetching publication year counts for platform = 'pubmed'...")
    get_pubmed_year_counts()


if __name__ == "__main__":
    main()
