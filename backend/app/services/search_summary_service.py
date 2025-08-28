#!/usr/bin/env python3
"""
Search Results Summary Generator

This module generates engaging summaries for search results using the same
approach as the DailyFeed summary generator. It creates news-style articles
that highlight the most relevant papers found for a user's search query.
"""

import os
import openai
import re
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from app.models.paper import Paper

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SearchSummaryService:
    def __init__(self):
        """Initialize the SearchSummaryService with Gemini API configuration."""
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("LLM_API_KEY not found in environment variables")
        
        # Configure OpenAI client for Gemini API
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    
    def generate_search_summary(self, query: str, papers: List[Paper]) -> str:
        """Generate a comprehensive summary for search results."""
        try:
            if not papers:
                return f"# Search Results: {query.title()}\n\nNo papers found for your search query."
            
            logger.info(f"Generating summary for {len(papers)} papers matching query: '{query}'")
            
            # Prepare papers information for the prompt
            papers_info = []
            for i, paper in enumerate(papers, 1):
                # Convert datetime to string for display
                pub_date = paper.published_date.strftime('%Y-%m-%d') if paper.published_date else 'Unknown'
                
                paper_info = f"""[{i}] Title: {paper.title}
Authors: {', '.join(paper.authors)}
Abstract: {paper.abstract}
Paper ID: {paper.paper_id}
Platform: {paper.platform}
Published: {pub_date}
Categories: {', '.join(paper.categories) if paper.categories else 'Unknown'}"""
                papers_info.append(paper_info)
            
            papers_text = "\n\n".join(papers_info)
            
            # Create news-style prompt similar to DailyFeed
            prompt = f"""You are a science journalist writing an engaging news article about research findings related to "{query}". 

Write a compelling news-style article that highlights the most relevant and exciting research papers found for this search. Your article should:

**WRITING STYLE:**
- Write like a science journalist for a general audience, not academic researchers
- Make complex concepts understandable and exciting

**ARTICLE STRUCTURE:**
1. **Opening Hook** (1 paragraph with 1-2 sentences): Start with a background introductionabout the research landscape for "{query}", and say the followins papers are the most relevant to the query.
2. **Key Findings** (2-3 paragraphs): Highlight the most significant discoveries and what makes them important
3. **Research Landscape** (1-2 paragraphs): Discuss the breadth of research and emerging trends in this area
4. **Future Implications** (1-2 paragraphs): Explore how these findings will advance the field

**CITATION REQUIREMENTS:**
- Use [1], [2], [3] format for citations corresponding to the papers below
- Reference multiple papers to show the breadth of research
- Cite papers when describing specific findings or innovations
- Group related papers when discussing common themes

**FORMATTING:**
- Start with: # Research Insights: {query.title()}
- Use engaging subheadings if needed
- Keep paragraphs readable and flowing
- Aim for 4-6 substantial paragraphs total

**TONE EXAMPLES:**
- Instead of: "The research demonstrates..."
- Use: "Scientists have discovered..."
- Instead of: "This methodology shows..."
- Use: "This groundbreaking approach reveals..."

Search Query: "{query}"
Found {len(papers)} relevant research papers:
{papers_text}

Write an exciting news article that captures the significance of these research findings and makes readers excited about the current state of research in this area."""

            response = self.client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": f"You are an enthusiastic science journalist specializing in research analysis. Write engaging news articles that make scientific discoveries accessible and exciting for general readers. Focus on the 'wow factor' and real-world impact of research findings."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Convert citations to hyperlinks
            summary_with_links = self.convert_citations_to_links(summary, papers)
            
            return summary_with_links
            
        except Exception as e:
            logger.error(f"Error generating summary for query '{query}': {e}", exc_info=True)
            return f"# Research Insights: {query.title()}\n\nError generating summary: {str(e)}"
    
    def convert_citations_to_links(self, summary: str, papers: List[Paper]) -> str:
        """Convert [1], [2] and [1, 2] citations to hyperlinks."""
        def replace_citation(match):
            citation_text = match.group(1)
            # Split by comma and strip whitespace from each number
            citation_nums = [num.strip() for num in citation_text.split(',')]
            
            links = []
            for num_str in citation_nums:
                try:
                    citation_num = int(num_str)
                    if 1 <= citation_num <= len(papers):
                        paper = papers[citation_num - 1]
                        title = paper.title
                        
                        # Create appropriate link based on platform
                        if paper.platform == "arxiv":
                            # Extract arXiv ID from paper_id for arXiv papers
                            links.append(f"[{title}](https://arxiv.org/abs/{paper.paper_id})")
                        elif paper.pdf_url:
                            # Use PDF URL for other platforms
                            links.append(f"[{title}]({paper.pdf_url})")
                        else:
                            # Fallback to just title
                            links.append(f"[{title}]")
                    else:
                        # Invalid citation number, keep original
                        links.append(f"[{num_str}]")
                except ValueError:
                    # Invalid number format, keep original
                    links.append(f"[{num_str}]")
            
            if len(links) == 1:
                return links[0]
            else:
                # Multiple citations: join with commas
                return f"[{', '.join(links)}]"
        
        # Pattern to match [1], [2], [1, 2], [2, 3, 4], etc.
        citation_pattern = r'\[(\d+(?:,\s*\d+)*)\]'
        return re.sub(citation_pattern, replace_citation, summary)
    
    def generate_quick_summary(self, query: str, papers: List[Paper], max_papers: int = 10) -> str:
        """Generate a shorter summary for quick insights."""
        # Limit papers for quick summary
        limited_papers = papers[:max_papers]
        
        try:
            if not limited_papers:
                return f"No papers found for '{query}'"
            
            # Create a shorter prompt for quick summary
            papers_info = []
            for i, paper in enumerate(limited_papers, 1):
                paper_info = f"[{i}] {paper.title} by {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}"
                papers_info.append(paper_info)
            
            papers_text = "\n".join(papers_info)
            
            prompt = f"""Provide a brief 2-3 sentence summary of the key research themes found for the search query "{query}".

Found papers:
{papers_text}

Focus on the main research directions and highlight what makes these findings interesting. Be concise but engaging."""

            response = self.client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": "You are a research analyst providing quick insights on search results. Be concise and highlight key themes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating quick summary for query '{query}': {e}")
            return f"Error generating summary for '{query}'"

# Create a global instance
search_summary_service = SearchSummaryService()
