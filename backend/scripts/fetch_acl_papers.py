#!/usr/bin/env python3
"""
Script to fetch ACL Anthology conference papers metadata for a given year.
Supports ACL, NAACL, and EMNLP conferences.
Usage: python fetch_acl_papers.py --conference acl --year 2024
"""

import argparse
import json
import os
import sys
import logging
import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fetch_acl_papers")

def get_session() -> requests.Session:
    """Get a requests session with appropriate headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

def get_conference_venue_ids(conference: str, year: int) -> List[str]:
    """Get possible venue IDs for a given conference and year."""
    venue_ids = []
    conference = conference.lower()
    
    if conference == "acl":
        # ACL tracks
        venue_ids.append(f"{year}.acl-long")
        venue_ids.append(f"{year}.acl-short")
        venue_ids.append(f"{year}.findings-acl")
        venue_ids.append(f"{year}.acl-demo")
        venue_ids.append(f"{year}.acl-industry")
        venue_ids.append(f"{year}.acl-srw")
        
        # Older format (for years before 2020)
        if year < 2020:
            venue_ids.append(f"P{year % 100:02d}")
            
    elif conference == "naacl":
        # NAACL tracks
        venue_ids.append(f"{year}.naacl-long")
        venue_ids.append(f"{year}.naacl-short")
        venue_ids.append(f"{year}.findings-naacl")
        venue_ids.append(f"{year}.naacl-demo")
        venue_ids.append(f"{year}.naacl-industry")
        venue_ids.append(f"{year}.naacl-srw")
        
        # Older format (for years before 2020)
        if year < 2020:
            venue_ids.append(f"N{year % 100:02d}")
            
    elif conference == "emnlp":
        # EMNLP tracks (keep existing logic)
        venue_ids.append(f"{year}.emnlp-main")
        venue_ids.append(f"{year}.findings-emnlp")
        venue_ids.append(f"{year}.emnlp-demo")
        venue_ids.append(f"{year}.emnlp-industry")
        venue_ids.append(f"{year}.emnlp-srw")
        
        # Older format (for years before 2020)
        if year < 2020:
            venue_ids.append(f"D{year % 100:02d}")
    else:
        raise ValueError(f"Unsupported conference: {conference}. Supported conferences: acl, naacl, emnlp")
    
    return venue_ids

def extract_paper_metadata_from_page(paper_url: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    """Extract metadata from a single paper page."""
    try:
        response = session.get(paper_url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {paper_url}, status code: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract basic metadata according to Paper model
        metadata = {}
        
        # Paper ID (from URL)
        paper_id = paper_url.rstrip('/').split('/')[-1]
        metadata['paper_id'] = paper_id
        
        # Title
        title_elem = soup.find('h2', id='title')
        if title_elem:
            metadata['title'] = title_elem.get_text(strip=True)
        else:
            metadata['title'] = ""
        
        # Authors
        authors = []
        author_elements = soup.find_all('a', href=lambda x: x and '/people/' in x)
        for author_elem in author_elements:
            author_name = author_elem.get_text(strip=True)
            if author_name and author_name not in authors:
                authors.append(author_name)
        metadata['authors'] = authors
        
        # Abstract - try multiple methods
        abstract = None
        
        # Method 1: Look for acl-abstract class structure
        abstract_div = soup.find('div', class_='card-body acl-abstract')
        if abstract_div:
            abstract_span = abstract_div.find('span')
            if abstract_span:
                abstract = abstract_span.get_text(strip=True)
        
        # Method 2: Look for "Abstract" heading
        if not abstract:
            abstract_heading = soup.find('h5', string=re.compile(r'Abstract', re.IGNORECASE))
            if abstract_heading:
                # Find the next div or span after the heading
                next_elem = abstract_heading.find_next_sibling()
                if next_elem:
                    abstract = next_elem.get_text(strip=True)
        
        # Method 3: Look for content that looks like an abstract
        if not abstract:
            # Look for divs that contain abstract-like content
            potential_abstracts = soup.find_all('div', class_='card-body')
            for div in potential_abstracts:
                text = div.get_text(strip=True)
                if len(text) > 100 and not text.startswith('@'):  # Abstracts are usually longer and don't start with citation
                    abstract = text
                    break
        
        metadata['abstract'] = abstract or ""
        
        # Categories (extract from venue and conference info)
        categories = []
        venue_elem = soup.find('span', class_='badge badge-secondary')
        if venue_elem:
            venue_text = venue_elem.get_text(strip=True)
            categories.append(venue_text)
        
        # Add more categories from anthology ID (track info)
        if 'long' in paper_id:
            categories.append('Long Paper')
        elif 'short' in paper_id:
            categories.append('Short Paper')
        elif 'demo' in paper_id:
            categories.append('Demo Paper')
        elif 'industry' in paper_id:
            categories.append('Industry Paper')
        elif 'srw' in paper_id:
            categories.append('Student Research Workshop')
        elif 'findings' in paper_id:
            categories.append('Findings')
        
        metadata['categories'] = categories
        
        # PDF URL
        pdf_elem = soup.find('a', href=lambda x: x and x.endswith('.pdf'))
        if pdf_elem:
            metadata['pdf_url'] = urljoin(paper_url, pdf_elem.get('href'))
        else:
            metadata['pdf_url'] = ""
        
        # Published date (construct from year and month if available)
        published_date = None
        year_elem = soup.find('span', class_='badge badge-info')
        month_text = None
        
        # Try to extract month from venue details
        venue_details = soup.find('dl', class_='acl-paper-details')
        if venue_details:
            dt_elements = venue_details.find_all('dt')
            for dt in dt_elements:
                key = dt.get_text(strip=True).lower()
                dd = dt.find_next_sibling('dd')
                if dd and 'month' in key:
                    month_text = dd.get_text(strip=True)
                    break
        
        # Construct published_date
        if year_elem:
            year_str = year_elem.get_text(strip=True)
            try:
                year_int = int(year_str)
                if month_text:
                    # Try to parse month
                    month_mapping = {
                        'january': 1, 'february': 2, 'march': 3, 'april': 4,
                        'may': 5, 'june': 6, 'july': 7, 'august': 8,
                        'september': 9, 'october': 10, 'november': 11, 'december': 12
                    }
                    month_lower = month_text.lower()
                    month_int = month_mapping.get(month_lower, 1)
                    published_date = datetime(year_int, month_int, 1).isoformat()
                else:
                    # Default to January if no month specified
                    published_date = datetime(year_int, 1, 1).isoformat()
            except ValueError:
                published_date = datetime(2024, 1, 1).isoformat()  # Default fallback
        else:
            published_date = datetime(2024, 1, 1).isoformat()  # Default fallback
        
        metadata['published_date'] = published_date
        
        # Updated date (set to None as requested)
        metadata['updated_date'] = None
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata from {paper_url}: {str(e)}")
        return None

def get_conference_paper_urls(conference: str, year: int, session: requests.Session) -> List[str]:
    """Get all paper URLs for a given conference and year."""
    paper_urls = []
    venue_ids = get_conference_venue_ids(conference, year)
    
    for venue_id in venue_ids:
        logger.info(f"Checking venue: {venue_id}")
        
        # Try to get the main conference page
        venue_url = f"https://aclanthology.org/volumes/{venue_id}/"
        try:
            response = session.get(venue_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all paper links - only HTML pages, not PDF/BIB files
                paper_links = soup.find_all('a', href=re.compile(rf'{venue_id}\.\d+/$'))
                for link in paper_links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(venue_url, href)
                        # Filter out non-HTML pages (PDF, BIB, attachments, etc.)
                        if not any(ext in full_url.lower() for ext in ['.pdf', '.bib', '.zip', 'attachment', 'software']):
                            if full_url not in paper_urls:
                                paper_urls.append(full_url)
                
                logger.info(f"Found {len(paper_links)} paper pages in {venue_id}")
            else:
                logger.warning(f"Could not access {venue_url}, status code: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching {venue_url}: {str(e)}")
        
        # Add a small delay to be respectful to the server
        time.sleep(0.5)
    
    # If no papers found using volume pages, try direct search
    if not paper_urls:
        logger.info("No papers found via volume pages, trying direct search...")
        paper_urls = search_papers_directly(conference, year, session)
    
    return paper_urls

def search_papers_directly(conference: str, year: int, session: requests.Session) -> List[str]:
    """Search for papers directly using anthology IDs."""
    paper_urls = []
    venue_ids = get_conference_venue_ids(conference, year)
    
    for venue_id in venue_ids:
        logger.info(f"Directly searching for papers in {venue_id}")
        
        # Try different paper numbers (usually 1-1000+ for main conferences)
        for paper_num in range(1, 1001):
            paper_id = f"{venue_id}.{paper_num}"
            paper_url = f"https://aclanthology.org/{paper_id}/"
            
            try:
                response = session.get(paper_url, timeout=5)
                if response.status_code == 200:
                    paper_urls.append(paper_url)
                    if len(paper_urls) % 10 == 0:
                        logger.info(f"Found {len(paper_urls)} papers so far...")
                elif response.status_code == 404:
                    # If we get 404, the paper doesn't exist
                    continue
                else:
                    # For other status codes, we might want to continue
                    continue
                    
            except Exception as e:
                logger.warning(f"Error checking {paper_url}: {str(e)}")
                continue
            
            # Add a small delay
            time.sleep(0.1)
            
            # Stop if we haven't found papers in a while (likely reached the end)
            if paper_num > 100 and len(paper_urls) == 0:
                break
    
    return paper_urls

def fetch_conference_papers_via_web_scraping(conference: str, year: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch conference papers metadata using web scraping."""
    session = get_session()
    
    try:
        # Get all paper URLs
        paper_urls = get_conference_paper_urls(conference, year, session)
        
        if not paper_urls:
            logger.warning(f"No papers found for {conference.upper()} {year}")
            return []
        
        logger.info(f"Found {len(paper_urls)} paper URLs for {conference.upper()} {year}")
        
        # Apply limit if specified
        if limit:
            paper_urls = paper_urls[:limit]
            logger.info(f"Limited to {len(paper_urls)} papers for testing")
        
        # Extract metadata from each paper
        papers_metadata = []
        for i, paper_url in enumerate(paper_urls, 1):
            logger.info(f"Processing paper {i}/{len(paper_urls)}: {paper_url}")
            
            metadata = extract_paper_metadata_from_page(paper_url, session)
            if metadata:
                papers_metadata.append(metadata)
            else:
                logger.warning(f"Failed to extract metadata from: {paper_url}")
            
            # Add a small delay to be respectful to the server
            time.sleep(0.5)
        
        return papers_metadata
        
    except Exception as e:
        logger.error(f"Error during web scraping: {str(e)}")
        return []

def save_to_json(papers_metadata: List[Dict[str, Any]], output_file: str, conference: str, year: int):
    """Save papers metadata to a JSON file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Prepare the output data
        output_data = {
            "metadata": {
                "conference": conference.upper(),
                "year": year,
                "total_papers": len(papers_metadata),
                "extraction_date": datetime.now().isoformat(),
                "source": "ACL Anthology Web Scraping"
            },
            "papers": papers_metadata
        }
        
        # Save to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully saved {len(papers_metadata)} papers to {output_file}")
        
    except Exception as e:
        logger.error(f"Error saving to JSON: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Fetch ACL Anthology conference papers metadata for a given year')
    parser.add_argument('--conference', type=str, required=True, 
                       choices=['acl', 'naacl', 'emnlp'],
                       help='Conference type: acl, naacl, or emnlp')
    parser.add_argument('--year', type=int, required=True, 
                       help='Year of the conference (e.g., 2024)')
    parser.add_argument('--output', type=str, 
                       help='Output JSON file path (default: data/{conference}_papers_YYYY.json)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit the number of papers to process (for testing)')
    
    args = parser.parse_args()
    
    # Set default output file if not provided
    if not args.output:
        # Get the parent directory of the script (backend)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
        data_dir = os.path.join(backend_dir, "data")
        args.output = os.path.join(data_dir, f"{args.conference}_papers_{args.year}.json")
    
    conference = args.conference
    year = args.year
    output_file = args.output
    
    logger.info(f"Starting to fetch {conference.upper()} papers for year {year}")
    logger.info(f"Output file: {output_file}")
    
    # Fetch papers using web scraping
    papers_metadata = fetch_conference_papers_via_web_scraping(conference, year, args.limit)
    
    if not papers_metadata:
        logger.error("No papers found or extracted successfully")
        return
    
    # Save to JSON file
    save_to_json(papers_metadata, output_file, conference, year)
    
    logger.info(f"Successfully fetched {len(papers_metadata)} papers for {conference.upper()} {year}")
    logger.info(f"Data saved to: {output_file}")

if __name__ == "__main__":
    main() 