#!/usr/bin/env python3
"""
Script to fetch paper information from arXiv and print authors
"""

import arxiv

def get_paper_authors(paper_id):
    """
    Fetch paper from arXiv by ID and return authors information
    
    Args:
        paper_id (str): arXiv paper ID (e.g., '2301.07041' or 'cs.AI/0301001')
        
    Returns:
        dict: Paper information including title, authors, and summary
    """
    try:
        # Create a search query for the specific paper
        search = arxiv.Search(id_list=[paper_id])
        
        # Get the first (and should be only) result
        paper = next(search.results())
        
        return {
            'title': paper.title,
            'authors': [author.name for author in paper.authors],
            'published': paper.published,
            'summary': paper.summary[:200] + '...' if len(paper.summary) > 200 else paper.summary,
            'url': paper.entry_id
        }
        
    except StopIteration:
        return None
    except Exception as e:
        print(f"Error fetching paper: {e}")
        return None

def search_papers_by_query(query, max_results=5):
    """
    Search papers on arXiv by query string
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of paper information dictionaries
    """
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        papers = []
        for paper in search.results():
            papers.append({
                'id': paper.get_short_id(),
                'title': paper.title,
                'authors': [author.name for author in paper.authors],
                'published': paper.published,
                'summary': paper.summary[:200] + '...' if len(paper.summary) > 200 else paper.summary,
                'url': paper.entry_id
            })
            
        return papers
        
    except Exception as e:
        print(f"Error searching papers: {e}")
        return []

def print_paper_info(paper_info):
    """
    Print paper information in a formatted way
    
    Args:
        paper_info (dict): Paper information dictionary
    """
    if not paper_info:
        print("No paper information available")
        return
        
    print("=" * 80)
    print(f"Title: {paper_info['title']}")
    print("-" * 80)
    print(f"Authors: {', '.join(paper_info['authors'])}")
    print("-" * 80)
    print(f"Published: {paper_info['published'].strftime('%Y-%m-%d')}")
    print(f"URL: {paper_info['url']}")
    print("-" * 80)
    print(f"Summary: {paper_info['summary']}")
    print("=" * 80)

def main():
    """
    Main function demonstrating different ways to use the arXiv API
    """
    print("ArXiv Paper Fetcher")
    print("==================")
    
    # Example 1: Get a specific paper by ID
    print("\n1. Fetching specific paper by ID...")
    paper_id = "2304.14743v1"  # Example: GPT-4 technical report
    paper_info = get_paper_authors(paper_id)
    
    if paper_info:
        print_paper_info(paper_info)
        print(f"\nAuthors of paper {paper_id}:")
        for i, author in enumerate(paper_info['authors'], 1):
            print(f"  {i}. {author}")
    else:
        print(f"Could not fetch paper with ID: {paper_id}")
    
    # Example 2: Search for papers by query
    print("\n\n2. Searching papers by query...")
    query = "machine learning transformers"
    papers = search_papers_by_query(query, max_results=3)
    
    if papers:
        print(f"\nFound {len(papers)} papers for query: '{query}'")
        for i, paper in enumerate(papers, 1):
            print(f"\n--- Paper {i} ---")
            print(f"ID: {paper['id']}")
            print(f"Title: {paper['title']}")
            print(f"Authors: {', '.join(paper['authors'])}")
            print(f"Published: {paper['published'].strftime('%Y-%m-%d')}")
    else:
        print(f"No papers found for query: '{query}'")

if __name__ == "__main__":
    main()
