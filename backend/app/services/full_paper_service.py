from google import genai
import io
import httpx
import logging
import os
from typing import List, Dict, Optional
from app.services.conv_db_service import conv_db_service
from app.services.extract_info import paper_info_extractor
from app.services.full_paper_analysis_prompt import FULL_PAPER_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

# Initialize Google AI client with API key
def get_genai_client():
    """Get Google AI client with proper API key configuration"""
    try:
        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            logger.error("GOOGLE_AI_API_KEY environment variable not set")
            return None
        
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Error initializing Google AI client: {e}")
        return None

async def analyze_full_papers(papers: List[Dict], combined_query: str, reasoning: str = "") -> Dict:
    """
    Perform full paper analysis on a list of papers using Gemini.
    
    Args:
        papers: List of paper dictionaries with pdf_url
        combined_query: Combined query string including main query, comparison query, and context
        reasoning: Intent analysis reasoning to provide context for the analysis
    
    Returns:
        Dict with analysis result and success status
    """
    try:
        if not papers:
            return {
                "analysis": "",
                "success": False,
                "error_message": "No papers provided for analysis"
            }
        
        # Get Google AI client
        client = get_genai_client()
        if not client:
            return {
                "analysis": "",
                "success": False,
                "error_message": "Google AI client not available. Please check API key configuration."
            }
        
        # Remove duplicates based on paper_id and platform (more reliable than pdf_url)
        unique_papers = []
        seen_papers = set()
        
        for paper in papers:
            paper_id = paper.get("paper_id")
            platform = paper.get("platform", "arxiv")
            
            # Create a unique key using paper_id and platform
            paper_key = (paper_id, platform)
            
            # Skip if we've already seen this paper
            if paper_key in seen_papers:
                logger.info(f"Skipping duplicate paper: {paper_id} (platform: {platform})")
                continue
                
            seen_papers.add(paper_key)
            unique_papers.append(paper)
        
        logger.info(f"Removed {len(papers) - len(unique_papers)} duplicate papers. Processing {len(unique_papers)} unique papers.")
        
        # Debug: Log all unique papers being processed
        for i, paper in enumerate(unique_papers):
            logger.info(f"Unique paper {i+1}: ID={paper.get('paper_id', 'No ID')}, Title={paper.get('title', 'No Title')[:50]}...")
        
        # Safety check: limit to reasonable number to prevent system overload
        if len(unique_papers) > 15:
            logger.info(f"Found {len(unique_papers)} papers for analysis, selecting top 15 papers to prevent system overload")
            unique_papers = unique_papers[:15]
        
        # Get PDF URLs directly from database using paper IDs
        pdf_urls = []
        paper_titles = []
        
        for paper in unique_papers:
            paper_id = paper.get('paper_id', '')
            platform = paper.get('platform', 'arxiv')
            
            try:
                # Get paper details from database
                paper_details = await conv_db_service.get_paper_by_id(paper_id, platform)
                if paper_details:
                    # Generate PDF URL using the paper_info_extractor
                    pdf_url = paper_info_extractor.get_pdf_url(paper_id)
                    pdf_urls.append(pdf_url)
                    paper_titles.append(paper_details.title)
                    logger.info(f"Found paper: {paper_details.title} -> {pdf_url}")
                else:
                    logger.warning(f"Paper not found in database: {paper_id} (platform: {platform})")
                    
            except Exception as e:
                logger.error(f"Error getting paper details for {paper_id}: {e}")
                continue
        
        if not pdf_urls:
            return {
                "analysis": "",
                "success": False,
                "error_message": "No valid papers found in database for analysis"
            }
        
        logger.info(f"Starting full paper analysis for {len(pdf_urls)} papers")
        logger.info(f"Combined query: {combined_query}")
        logger.info(f"Paper titles: {paper_titles}")
        logger.info(f"PDF URLs being analyzed: {pdf_urls}")
        
        uploaded_files = []
        
        # Loop through URLs, download, and upload
        skipped_files = []
        for i, url in enumerate(pdf_urls):
            try:
                logger.info(f"Processing PDF {i+1}/{len(pdf_urls)}: {url}")
                doc_data = io.BytesIO(httpx.get(url).content)
                uploaded = client.files.upload(
                    file=doc_data,
                    config=dict(mime_type='application/pdf')
                )
                uploaded_files.append(uploaded)
                logger.info(f"Successfully uploaded PDF: {url}")
                
            except Exception as e:
                logger.warning(f"Failed to upload PDF {url}: {e}")
                skipped_files.append(f"{paper_titles[i]} (upload failed)")
                continue
        
        if not uploaded_files:
            skipped_info = f" Skipped files: {', '.join(skipped_files)}" if skipped_files else ""
            return {
                "analysis": "",
                "success": False,
                "error_message": f"Failed to upload any PDFs for analysis.{skipped_info}"
            }
        
        # Log skipped files for transparency
        if skipped_files:
            logger.info(f"Skipped {len(skipped_files)} problematic files: {', '.join(skipped_files)}")
            logger.info(f"Successfully processing {len(uploaded_files)} valid PDFs")
        
        # Create analysis prompt
        reasoning_context = f"Context from intent analysis: {reasoning}" if reasoning else ""
        
        prompt = FULL_PAPER_ANALYSIS_PROMPT.format(
            combined_query=combined_query,
            reasoning_context=reasoning_context
        )
        
        # Pass all uploaded files + prompt into contents
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=uploaded_files + [prompt]
        )
        
        logger.info(f"Full paper analysis completed successfully: {response.text}")
        
        # Prepare response with skipped files info
        result = {
            "analysis": response.text,
            "success": True,
            "error_message": None,
            "papers_analyzed": len(uploaded_files),
            "papers_skipped": len(skipped_files)
        }
        
        # Add skipped files info if any were skipped
        if skipped_files:
            result["skipped_files"] = skipped_files
            result["analysis"] += f"\n\nNote: {len(skipped_files)} papers were skipped due to empty/corrupted PDFs: {', '.join(skipped_files)}"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in full paper analysis: {e}")
        return {
            "analysis": "",
            "success": False,
            "error_message": f"Full paper analysis failed: {str(e)}"
        }
