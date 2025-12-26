import asyncio
import csv
from sqlalchemy import select, extract
from app.db.database import get_async_db
from app.models.db_models import DBPaper

async def get_1900_pubmed_papers(output_csv="pubmed_1900_papers.csv"):
    platform = "pubmed"
    year_filter = 1900
    papers_data = []

    async for db in get_async_db():
        query = select(DBPaper).where(
            DBPaper.platform == platform,
            extract('year', DBPaper.published_date) == year_filter
        )
        result = await db.execute(query)
        papers = result.scalars().all()

        if papers:
            print(f"Found {len(papers)} papers with platform='{platform}' and published_date in {year_filter}")
            for p in papers:
                papers_data.append({
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "published_date": p.published_date.isoformat() if p.published_date else "",
                    "platform": p.platform,
                    "pdf_url": getattr(p, 'pdf_url', ""),
                })

            # Write to CSV
            try:
                with open(output_csv, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["paper_id", "title", "published_date", "platform", "pdf_url"])
                    writer.writeheader()
                    for row in papers_data:
                        writer.writerow(row)
                print(f"✅ Saved {len(papers_data)} papers to CSV: {output_csv}")
            except Exception as e:
                print(f"❌ Failed to save CSV: {e}")

        else:
            print(f"No papers found with platform='{platform}' and published_date in {year_filter}")

if __name__ == "__main__":
    asyncio.run(get_1900_pubmed_papers())
