import arxiv
import logging
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.models.paper import Paper
import requests
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


def parse_submitted_date(submitted_line):
    """Extract date from submitted line and convert to datetime"""
    try:
        # Extract date between "Submitted" and semicolon
        date_match = re.search(r'Submitted\s+(.+?);', submitted_line)
        if date_match:
            date_str = date_match.group(1).strip()
            # Try to parse common date formats
            try:
                # Try format like "17 June, 2025"
                parsed_date = datetime.strptime(date_str, "%d %B, %Y")
                return parsed_date
            except ValueError:
                return None
    except:
        return None
    

def access_arxiv_search(url):
    """Access arXiv search results and extract paper information"""
    try:
        # Add headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Save the HTML content to a file
        with open('arxiv_search_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract paper information
        papers = []
        
        # Find all paper entries (they typically have specific patterns)
        paper_entries = soup.find_all('li', class_='arxiv-result')
        
        for i, entry in enumerate(paper_entries):
            try:
                # Get all text lines
                text = entry.get_text()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # Initialize fields
                arxiv_id, categories, title, authors, abstract, date_raw, submitted_date_parsed = "Not found", [], "Not found", [], "Not found", "Not found", None
                
                # State tracking
                current_section = None
                collecting_categories, collecting_authors, collecting_abstract, collecting_comments, collecting_date = False, False, False, False, False
                abstract_lines = []
                date_lines = []
                
                # Parse through lines to extract information
                for j, line in enumerate(lines):
                    
                    # Handle Comments section
                    if line == 'Comments:':
                        # If we were collecting date info, stop now
                        if collecting_date:
                            collecting_date = False
                            if date_lines:
                                date_raw = '\n'.join(date_lines)
                        collecting_comments = True
                        continue
                    elif collecting_comments:
                        continue  # Skip all comment lines
                    
                    # Extract arXiv ID
                    elif line.startswith('arXiv:'):
                        # Extract everything after 'arXiv:' (handles both new format like 2506.13726 and old format like cs/0503039)
                        arxiv_match = re.search(r'arXiv:(.+)', line)
                        if arxiv_match:
                            arxiv_id = arxiv_match.group(1).strip()
                            collecting_categories = True
                            continue
                    
                    # Skip format indicators like [pdf, ps, other]
                    elif line.startswith('[') and line.endswith(']'):
                        continue
                    
                    # Collect categories and title
                    elif collecting_categories:
                        # Check if this is "Authors:"
                        if line == 'Authors:':
                            collecting_categories = False
                            collecting_authors = True
                            continue
                        else:
                            # Check if next line is "Authors:" to determine if current line is title
                            is_title = False
                            if j + 1 < len(lines) and lines[j + 1] == 'Authors:':
                                is_title = True
                            if is_title:
                                title = line.replace('\\', '')  # Clean up LaTeX
                                continue
                            else:
                                # Check if this is a category: not "doi" and doesn't contain numbers
                                if line.lower() != 'doi' and not any(char.isdigit() for char in line):
                                    categories.append(line)
                    
                    elif collecting_authors:
                        if line == 'Abstract:':
                            collecting_authors = False
                            collecting_abstract = True
                            continue
                        else:
                            # Clean up author name and add to list
                            author = line.replace(',', '').strip()
                            if author:
                                authors.append(author)
                            continue
                    
                    # Extract abstract (after "Abstract:" line)
                    elif collecting_abstract:
                        if line.startswith('Submitted'):
                            collecting_abstract = False
                            collecting_date = True
                            date_lines.append(line)
                            submitted_date_parsed = parse_submitted_date(line)
                            continue
                        elif line == '▽ More':
                            continue  # Skip the "More" indicator
                        elif line == '△ Less':
                            continue  # Skip the "Less" indicator
                        else:
                            # Collect abstract lines
                            abstract_lines.append(line)
                            continue
                    
                    # Collect date information from "Submitted" until "Comments"
                    elif collecting_date:
                        date_lines.append(line)
                        continue
                
                # Join abstract lines
                if abstract_lines:
                    abstract = abstract_lines[-1]
                
                # Join date lines if we have any
                if date_lines:
                    date_raw = ' '.join(date_lines).strip()
                
                paper_data = {
                    'arxiv_id': arxiv_id,
                    'categories': categories,
                    'title': title,
                    'authors': authors,
                    'abstract': abstract,
                    'date_raw': date_raw,
                    'submitted_date_parsed': submitted_date_parsed.isoformat() if submitted_date_parsed else None,
                    'raw_html': str(entry),  # Store raw HTML for debugging
                    'raw_text_lines': lines  # Store parsed text lines for debugging
                }
                
                papers.append(paper_data)
                
            except Exception as e:
                print(f"   Error parsing paper {i+1}: {e}")
        
        return papers
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing arXiv search: {e}")
        return None
    
    
async def fetch_papers_from_arxiv(date, to_date):
    """Fetch papers from arXiv using the existing scraping method"""
    print("🔬 Accessing arXiv Search Results")
    print("=" * 40)
    print(f"📅 Fetching papers from {date} to {to_date}")
    
    # Base arXiv search URL without start parameter
    base_arxiv_url = f"https://arxiv.org/search/advanced?advanced=&terms-0-operator=AND&terms-0-term=&terms-0-field=title&classification-physics_archives=all&classification-include_cross_list=include&date-year=&date-filter_by=date_range&date-from_date={date}&date-to_date={to_date}&date-date_type=submitted_date&abstracts=show&size=50&order=-submitted_date"
    print(base_arxiv_url)
    
    all_papers = []
    start = 0
    page_number = 1
    
    while True:
        # Build URL with current start parameter
        if start == 0:
            arxiv_url = base_arxiv_url
        else:
            arxiv_url = f"{base_arxiv_url}&start={start}"
        
        print(f"\n📄 Fetching page {page_number} (starting from result {start + 1})")
        
        # Access the arXiv search and parse results
        papers = access_arxiv_search(arxiv_url)
        
        # If no papers found or error occurred, break the loop
        if not papers or len(papers) == 0:
            break
        
        # Add papers to our collection
        all_papers.extend(papers)
        
        # Increment for next page
        start += 50
        page_number += 1
    
    if all_papers:
        print(f"\n🎉 Successfully extracted {len(all_papers)} total papers from {page_number - 1} pages")
        
        # Show detailed statistics for all papers
        total_papers = len(all_papers)
        papers_with_arxiv_id = len([p for p in all_papers if p['arxiv_id'] != "Not found"])
        papers_with_categories = len([p for p in all_papers if len(p['categories']) > 0])
        papers_with_titles = len([p for p in all_papers if p['title'] != "Not found"])
        papers_with_authors = len([p for p in all_papers if len(p['authors']) > 0])
        papers_with_abstracts = len([p for p in all_papers if p['abstract'] != "Not found"])
        papers_with_dates = len([p for p in all_papers if p['date_raw'] != "Not found"])
        papers_with_parsed_dates = len([p for p in all_papers if p['submitted_date_parsed'] is not None])
        
        print(f"\n📈 Final Extraction Statistics:")
        print(f"   Total papers processed: {total_papers}")
        print(f"   Papers with arXiv IDs: {papers_with_arxiv_id}")
        print(f"   Papers with categories: {papers_with_categories}")
        print(f"   Papers with titles: {papers_with_titles}")
        print(f"   Papers with authors: {papers_with_authors}")
        print(f"   Papers with abstracts: {papers_with_abstracts}")
        print(f"   Papers with submission dates: {papers_with_dates}")
        print(f"   Papers with parsed dates: {papers_with_parsed_dates}")
        
    else:
        print("\n❌ No papers were extracted from any pages.")
    
    return all_papers


class ArxivService:
    """fetching papers from arXiv"""

    def __init__(self):
        self.client = arxiv.Client(
            page_size=1000,
            delay_seconds=3,
            num_retries=3
        )

    def remove_timezone(self,dt):
        if dt and dt.tzinfo:
            return dt.replace(tzinfo=None)
        return dt
    
    async def fetch_papers(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 10000
    ) -> List[Paper]:
        """
        Fetch papers from arXiv within a date range
        """
        try:
            # Build query string for date range
            query_parts = []
            
            if start_date:
                start_str = start_date.strftime("%Y%m%d")
                query_parts.append(f"submittedDate:[{start_str}0000 TO ")
                
            if end_date:
                end_str = end_date.strftime("%Y%m%d")
                if start_date:
                    query_parts[-1] += f"{end_str}2359]"
                else:
                    query_parts.append(f"submittedDate:[* TO {end_str}2359]")
            else:
                if start_date:
                    query_parts[-1] += "*]"
            
            query = " AND ".join(query_parts)
            
            client = self.client
            
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            # Fetch all results
            results = list(client.results(search))
            
            
            # Convert to Paper objects
            papers = []
            for result in results:
                # Process datetime, remove timezone information
                published_date = self.remove_timezone(result.published)
                updated_date = self.remove_timezone(result.updated)
                
                paper = Paper(
                    paper_id=result.get_short_id(),
                    title=result.title,
                    authors=[author.name for author in result.authors],
                    abstract=result.summary,
                    categories=result.categories,
                    pdf_url=result.pdf_url,
                    published_date=published_date,
                    updated_date=updated_date
                )
                papers.append(paper)
            if len(papers) == 0:
                # TODO: resolve the keys
                print("fetching papers from arxiv using html")
                if end_date == start_date:
                    end_date = (start_date + timedelta(days=1)).strftime('%Y-%m-%d')
                html_results = await fetch_papers_from_arxiv(start_date, end_date)
                for html_paper in html_results:
                    paper = Paper(
                        paper_id=html_paper['arxiv_id'],
                        title=html_paper['title'],
                        authors=html_paper['authors'],
                        abstract=html_paper['abstract'],
                        categories=html_paper['categories'],
                        pdf_url="arxiv.org/pdf/"+html_paper['arxiv_id'],
                        published_date=html_paper['submitted_date_parsed'],
                        updated_date=html_paper['submitted_date_parsed']
                    )
                    papers.append(paper)
            return papers
            
        except Exception as e:
            logger.error(f"Error fetching papers from arXiv: {e}")
            raise
        
arxiv_service = ArxivService()