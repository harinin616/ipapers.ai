import asyncio
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List
from app.models.paper import Paper
from app.services.db_service import db_service
from app.services.vector_search_service import vector_search_service
import re
from bs4 import BeautifulSoup
import json

class ArxivSearchService:
    """
    handle search request from arxiv website 
    if the paper is not in database, add it to the database and faiss index
    """
    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"
        self.queue = asyncio.Queue()
        self.consumer_task = asyncio.create_task(self.consumer())

    async def consumer(self):
        """
        background consumer to add searched papers to database and faiss index
        """
        while True:
            paper_list = await self.queue.get()
            try:
                await db_service.add_papers(paper_list)
                await vector_search_service.add_papers(paper_list)
            except Exception as e:
                print(f"Error processing papers: {str(e)}")
            finally:
                self.queue.task_done()
                
    def parse_submitted_date(self, submitted_line):
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
        
    def access_arxiv_search(self, url):
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
                                submitted_date_parsed = self.parse_submitted_date(line)
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
                        'platform': 'arxiv',
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

    async def search(self, query: str, max_results: int = 20) -> List[str]:
        """
        search papers from arxiv website and add to async queue
        """
        try:
            url_query = query.replace(" ", "+")
            arxiv_url = f"https://arxiv.org/search/advanced?advanced=&terms-0-operator=AND&terms-0-term={query}&terms-0-field=all&classification-physics_archives=all&classification-include_cross_list=include&date-filter_by=all_dates&date-year=&date-from_date=&date-to_date=&date-date_type=submitted_date&abstracts=show&size=50&order="
            
            preliminary_papers = self.access_arxiv_search(arxiv_url)
            
            paper_list = []
            
            for pre_paper in preliminary_papers[:max_results]:
                paper = Paper(
                    paper_id=pre_paper['arxiv_id'],
                    platform="arxiv",
                    title=pre_paper['title'],
                    authors=pre_paper['authors'],
                    abstract=pre_paper['abstract'],
                    categories=pre_paper['categories'],
                    pdf_url=f"https://www.arxiv.org/pdf/{pre_paper['arxiv_id']}",
                    published_date=pre_paper['submitted_date_parsed'],
                    updated_date=pre_paper['submitted_date_parsed']
                )
                
                paper_list.append(paper)
            await self.queue.put(paper_list)
            
            return paper_list
        except Exception as e:
            print(f"Error searching arXiv: {str(e)}")
            return []

arxivsearch_service = ArxivSearchService()