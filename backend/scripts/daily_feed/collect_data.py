import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import argparse


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


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Fetch arXiv papers for a specific date range')
    parser.add_argument('--date', type=str, 
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                       help='Start date in YYYY-MM-DD format (default: yesterday)')
    
    args = parser.parse_args()
    
    # Parse the input date and calculate to_date
    try:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d')
        to_date_obj = date_obj + timedelta(days=1)
        
        date = date_obj.strftime('%Y-%m-%d')
        to_date = to_date_obj.strftime('%Y-%m-%d')
    except ValueError:
        print("❌ Error: Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    print("🔬 Accessing arXiv Search Results")
    print("=" * 40)
    print(f"📅 Fetching papers from {date} to {to_date}")
    
    # Base arXiv search URL without start parameter
    base_arxiv_url = f"https://arxiv.org/search/advanced?advanced=&terms-0-operator=AND&terms-0-term=&terms-0-field=title&classification-physics_archives=all&classification-include_cross_list=include&date-year=&date-filter_by=date_range&date-from_date={date}&date-to_date={to_date}&date-date_type=submitted_date&abstracts=show&size=50&order=-submitted_date"
    
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
        
    # Save all papers to a JSON file
    import os
    os.makedirs("./data", exist_ok=True)
    
    save_path = f"./data/{date}-{to_date}.json"
    with open(save_path, 'w') as f:
        json.dump(all_papers, f, indent=4)
    
    print(f"\n💾 Successfully saved {len(all_papers)} papers to {save_path}")


if __name__ == "__main__":
    main()
