import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import re
import csv
import os

# --- Helpers ---

def _parse_month(month_str):
    if not month_str:
        return 1
    s = month_str.strip()
    if re.fullmatch(r'\d+', s):
        m = int(s)
        if 1 <= m <= 12:
            return m
    try:
        return datetime.strptime(s[:3], '%b').month
    except Exception:
        pass
    try:
        return datetime.strptime(s, '%B').month
    except Exception:
        pass
    return 1

def _parse_pubmed_date(elem):
    """Parse Year/Month/Day or MedlineDate into a datetime object."""
    if elem is None:
        return None

    year = elem.findtext('Year')
    month = elem.findtext('Month')
    day = elem.findtext('Day')

    # --- Case 1: Normal structured Year/Month/Day ---
    try:
        y = int(year) 
        m = _parse_month(month)
        d = int(day) if day else 1
        return datetime(y, m, d)
    except Exception:
        pass

    # --- Case 2: MedlineDate like "2024 Jan-Dec" or "2024 Spring" ---
    medline_date = elem.findtext('MedlineDate')
    if medline_date:
        match = re.search(r'(\d{4})', medline_date)
        if match:
            y = int(match.group(1))
            # Try to extract first month in the range (e.g., "Jan" from "Jan-Dec")
            month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', medline_date, re.IGNORECASE)
            if month_match:
                m = _parse_month(month_match.group(1))
                return datetime(y, m, 1)
            else:
                # Only year available, no month
                return datetime(y, 1, 1)
    return None

def _authors_to_str(authors):
    """Serialize authors as list with single quotes only."""
    safe = [a.replace("'", "\\'") for a in authors]
    return "[" + ", ".join(f"'{a}'" for a in safe) + "]"


def _clean_text(s: str) -> str:
    """Clean text fields to avoid quotes and embedded line breaks in CSV."""
    if not s:
        return ""
    return re.sub(r'[\r\n\t]+', ' ', s.replace('"', "'")).strip()


# --- Main Parser ---
def parse_pubmed_xml(xml_file, output_csv, default_category="medical"):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    records = []
    base_url = "https://pubmed.ncbi.nlm.nih.gov/"
    today = datetime.today().date()  # Today's date for comparison

    for article in root.findall("PubmedArticle"):
        missing = []

        # PMID
        pmid = article.findtext(".//PMID")
        if not pmid:
            missing.append("PMID")

        # Title with fallback to VernacularTitle
        title_elem = article.find(".//ArticleTitle")
        title = "".join(title_elem.itertext()).strip() if title_elem is not None else None
        if not title:
            vern_title_elem = article.find(".//VernacularTitle")
            title = "".join(vern_title_elem.itertext()).strip() if vern_title_elem is not None else None
        if not title:
            missing.append("Title")

        # Authors
        authors = []
        for author in article.findall(".//Article/AuthorList/Author"):
            collective = author.findtext("CollectiveName")
            if collective:
                authors.append(_clean_text(collective))
                continue
            fore = author.findtext("ForeName")
            last = author.findtext("LastName")
            initials = author.findtext("Initials")
            if fore and last:
                authors.append(f"{fore.strip()} {last.strip()}")
            elif last and initials:
                authors.append(f"{last.strip()} {initials.strip()}")
            elif last:
                authors.append(last.strip())
        if not authors:
            missing.append("Authors")

        # Published date
        pub_date = _parse_pubmed_date(article.find(".//ArticleDate[@DateType='Electronic']"))
        if pub_date is None:
            pub_date = _parse_pubmed_date(article.find(".//JournalIssue/PubDate"))
        if pub_date is None:
            missing.append("Published Date")
            pub_date_obj = None
        else:
            pub_date_obj = pub_date.date()

        # Skip if published_date is in the future
        if pub_date_obj and pub_date_obj > today:
            print(f"⚠️ Skipping PMID {pmid} because published_date {pub_date_obj} is in the future")
            continue

        # Revised/updated date
        updated_date = _parse_pubmed_date(article.find(".//DateRevised"))

        # PDF URL
        pdf_url = f"{base_url}{pmid}/" if pmid else None

        # Categories
        categories = [default_category]

        # Abstract
        abstract_texts = article.findall(".//AbstractText")
        if abstract_texts:
            parts = ["".join(a.itertext()).strip() for a in abstract_texts]
            abstract = " ".join([p for p in parts if p])
        else:
            abstract_elem = article.find(".//Abstract")
            abstract = "".join(abstract_elem.itertext()).strip() if abstract_elem is not None else None
        if not abstract:
            missing.append("Abstract")

        if missing:
            uniq_missing = ", ".join(sorted(set(missing)))
            print(f"⚠️ Missing fields for PMID {pmid}: {uniq_missing}")

        records.append({
            "paper_id": pmid or "",
            "published_date": pub_date,
            "updated_date": updated_date,
            "platform": "pubmed",
            "pdf_url": pdf_url or "",
            "authors": _authors_to_str(authors),  # ✅ single quotes fix
            "title": _clean_text(title or ""),    # ✅ clean quotes
            "abstract": _clean_text(abstract or ""),  # ✅ clean quotes
            "categories": str(categories)         # keep as string
        })

    # DataFrame
    df = pd.DataFrame(records)

    # Convert dates to ISO strings
    for col in ("published_date", "updated_date"):
        df[col] = df[col].apply(lambda d: d.date().isoformat() if isinstance(d, datetime) else "")

    # Column order
    col_order = [
        "paper_id", "published_date", "updated_date", "platform",
        "pdf_url", "authors", "title", "abstract", "categories"
    ]
    df = df[col_order]

    # Save CSV
    df.to_csv(output_csv, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"✅ CSV saved at: {output_csv}")
    print("Note: 'authors' now always single-quoted, abstracts/titles cleaned of double quotes.")

# --- Run ---
import argparse

# --- Run ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse PubMed XML to CSV")
    parser.add_argument("xml_file", help="Path to the PubMed XML file")
    parser.add_argument(
        "-o", "--output_folder", default="pubmed_parsed_csv",
        help="Folder to save the output CSV (default: pubmed_parsed_csv)"
    )
    parser.add_argument(
        "-c", "--category", default="medical",
        help="Default category for the papers (default: 'medical')"
    )

    args = parser.parse_args()

    os.makedirs(args.output_folder, exist_ok=True)
    xml_filename = os.path.basename(args.xml_file)
    csv_filename = os.path.splitext(xml_filename)[0] + ".csv"
    csv_path = os.path.join(args.output_folder, csv_filename)

    parse_pubmed_xml(args.xml_file, csv_path, default_category=args.category)
