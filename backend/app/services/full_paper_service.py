from google import genai
import io
import httpx
import logging
import os
import tempfile
import time

from typing import List, Dict, Optional
from app.services.conv_db_service import conv_db_service
from app.services.extract_info import paper_info_extractor
from app.services.full_paper_analysis_prompt import FULL_PAPER_ANALYSIS_PROMPT
from google import genai
logger = logging.getLogger(__name__)
from typing import List, Dict

# PubMed download dependencies
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from Bio import Entrez

# Set email for NCBI (required by Entrez)
Entrez.email = "your_email@example.com"  # required by NCBI


def get_pmcid_from_pmid(pmid):
    handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid)
    records = Entrez.read(handle)
    handle.close()
    try:
        pmcid = records[0]["LinkSetDb"][0]["Link"][0]["Id"]
        return f"PMC{pmcid}"
    except IndexError:
        return None


def download_pmc_pdf(pmid, download_dir):
    pmcid = get_pmcid_from_pmid(pmid)
    if not pmcid:
        print(f"No PMC PDF found for PMID {pmid}")
        return None
    
    # Ensure download directory exists and use absolute path
    download_dir = os.path.abspath(download_dir)
    os.makedirs(download_dir, exist_ok=True)
    print(f"📁 Download directory set to: {download_dir}")

    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"

    options = Options()
    options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--download-directory={download_dir}")
    options.add_argument("--headless")  # if you don’t need UI
    options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")  # unique profile each run
    prefs = {
        "download.default_directory": download_dir,
        "download.directory_upgrade": True,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
        "plugins.plugins_disabled": ["Chrome PDF Viewer"]
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)  # wait for download
    driver.quit()
    print(f"✅ PDF should be in {download_dir} for PMC ID {pmcid}")
    
    # Return the downloaded file path
    pdf_files = [f for f in os.listdir(download_dir) if f.endswith('.pdf')]
    if pdf_files:
        return os.path.join(download_dir, pdf_files[-1])
    return None


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

async def download_pubmed_papers(papers: List[Dict], output_dir: str) -> List[str]:
    """
    Download PubMed papers using PMC ID lookup and Selenium.
    Saves to the specified output directory and returns list of local file paths.
    """
    downloaded_files = []
    logger.info(f"Starting PubMed download for {len(papers)} papers to {output_dir}")
    
    for paper in papers:
        try:
            paper_id = paper.get("paper_id", "")
            platform = paper.get("platform", "pubmed")
            
            # Get paper details from database
            details = await conv_db_service.get_paper_by_id(paper_id, platform)
            if not details:
                logger.warning(f"No database entry found for PubMed paper {paper_id}")
                continue
            
            # Try PMC download first using the exact logic provided
            logger.info(f"Attempting PMC download for PMID {paper_id}")
            try:
                pdf_path = download_pmc_pdf(pmid=paper_id, download_dir=output_dir)
                if pdf_path and os.path.exists(pdf_path):
                    downloaded_files.append(pdf_path)
                    logger.info(f"Successfully downloaded PubMed paper {paper_id} via PMC")
                    continue
                else:
                    logger.warning(f"PMC download failed for {paper_id} - file not created")
            except Exception as e:
                logger.warning(f"PMC download failed for {paper_id}: {e}")
            
            # Skip fallback - only use PMC downloads to avoid 0-byte files
            logger.warning(f"No fallback attempted for PubMed paper {paper_id} - PMC download only")
                    
        except Exception as e:
            logger.error(f"Failed to download PubMed paper {paper_id}: {e}")
            continue
    
    logger.info(f"PubMed download completed. Successfully downloaded {len(downloaded_files)} files")
    return downloaded_files

async def analyze_full_papers(papers: List[Dict], combined_query: str, reasoning: str = "") -> Dict:
    """
    Perform full paper analysis on a list of papers using Gemini.
    Uses a temporary folder for PDFs (auto-cleanup).
    """
    try:
        if not papers:
            return {
                "analysis": "No paper found to analyze",
                "success": True,
                "error_message": "No papers provided for analysis"
            }

        # Get Google AI client
        client = get_genai_client()
        if not client:
            return {
                "analysis": "No paper found to analyze",
                "success": True,
                "error_message": "Google AI client not available. Please check API key configuration."
            }

        # Deduplicate by (paper_id, platform)
        unique_papers = []
        seen = set()
        for paper in papers:
            key = (paper.get("paper_id"), paper.get("platform", "arxiv"))
            if key not in seen:
                seen.add(key)
                unique_papers.append(paper)

        logger.info(f"Processing {len(unique_papers)} unique papers")

        # Safety cap
        if len(unique_papers) > 15:
            logger.info(f"Too many papers ({len(unique_papers)}), trimming to top 15")
            unique_papers = unique_papers[:15]

        # Separate papers by platform for different download methods
        arxiv_papers = []
        pubmed_papers = []
        other_papers = []
        
        for paper in unique_papers:
            platform = paper.get("platform", "arxiv")
            if platform == "pubmed":
                pubmed_papers.append(paper)
            elif platform == "arxiv":
                arxiv_papers.append(paper)
            else:
                other_papers.append(paper)

        uploaded_files, skipped_files = [], []
        all_downloaded_files = []

        # Create fixed directory for PDFs - download all papers first
        tmpdir = "files_to_analyze"
        
        # Ensure directory is empty before use
        import shutil
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.makedirs(tmpdir)
        logger.info(f"Created empty directory: {tmpdir}")
        
        try:
            # Download arXiv and other papers
            pdf_urls, paper_titles = [], []
            for paper in arxiv_papers + other_papers:
                try:
                    paper_id = paper.get("paper_id", "")
                    platform = paper.get("platform", "arxiv")
                    details = await conv_db_service.get_paper_by_id(paper_id, platform)
                    if details:
                        url = paper_info_extractor.get_pdf_url(paper_id)
                        pdf_urls.append(url)
                        paper_titles.append(details.title)
                    else:
                        logger.warning(f"No DB entry for {paper_id} ({platform})")
                except Exception as e:
                    logger.error(f"Error fetching paper {paper}: {e}")

            # Download arXiv and other papers to common folder
            for i, url in enumerate(pdf_urls):
                try:
                    logger.info(f"Downloading PDF {i+1}/{len(pdf_urls)}: {url}")
                    resp = httpx.get(url, timeout=30)
                    resp.raise_for_status()
                    pdf_path = f"{tmpdir}/arxiv_paper_{i+1}.pdf"
                    with open(pdf_path, "wb") as f:
                        f.write(resp.content)
                    all_downloaded_files.append(pdf_path)
                    logger.info(f"Downloaded {url} to {pdf_path}")

                except Exception as e:
                    logger.warning(f"Failed to download {url}: {e}")
                    skipped_files.append(f"{paper_titles[i]} (download failed)")

            # Download PubMed papers using special method
            if pubmed_papers:
                logger.info(f"Downloading {len(pubmed_papers)} PubMed papers using PMC method")
                pubmed_files = await download_pubmed_papers(pubmed_papers, tmpdir)
                all_downloaded_files.extend(pubmed_files)

            # Check if any files were actually downloaded
            if not all_downloaded_files:
                logger.warning("No files were downloaded successfully")
                return {
                    "analysis": "No paper found to analyze",
                    "success": True,
                    "error_message": "No files were downloaded successfully for analysis"
                }

            # List all files in the directory for debugging
            logger.info(f"Files in {tmpdir}: {os.listdir(tmpdir) if os.path.exists(tmpdir) else 'Directory does not exist'}")
            logger.info(f"Total files to analyze: {len(all_downloaded_files)}")

            # Now upload all downloaded files to Google AI for analysis
            logger.info(f"Uploading {len(all_downloaded_files)} papers to Google AI for analysis")
            for i, file_path in enumerate(all_downloaded_files):
                try:
                    uploaded = client.files.upload(
                        file=open(file_path, "rb"),
                        config=dict(mime_type="application/pdf")
                    )
                    uploaded_files.append(uploaded)
                    logger.info(f"Uploaded paper {i+1}/{len(all_downloaded_files)} successfully")

                except Exception as e:
                    logger.warning(f"Failed to upload paper {i+1}: {e}")
                    skipped_files.append(f"Paper {i+1} (upload failed)")

            if not uploaded_files:
                return {
                    "analysis": "No paper found to analyze",
                    "success": True,
                    "error_message": f"Failed to upload any PDFs for analysis. Skipped: {', '.join(skipped_files)}"
                }

            # Build prompt
            reasoning_context = f"Context from intent analysis: {reasoning}" if reasoning else ""
            prompt = FULL_PAPER_ANALYSIS_PROMPT.format(
                combined_query=combined_query,
                reasoning_context=reasoning_context
            )

            # Run Gemini
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=uploaded_files + [prompt]
            )

            result = {
                "analysis": response.text,
                "success": True,
                "error_message": None,
                "papers_analyzed": len(uploaded_files),
                "papers_skipped": len(skipped_files)
            }
            if skipped_files:
                result["skipped_files"] = skipped_files
                result["analysis"] += f"\n\nNote: Skipped {len(skipped_files)} papers due to errors: {', '.join(skipped_files)}"

            return result
            
        finally:
            # Manually delete the directory after analysis
            try:
                # shutil.rmtree(tmpdir)
                logger.info(f"Cleaned up directory: {tmpdir}")
            except Exception as e:
                logger.warning(f"Failed to clean up directory {tmpdir}: {e}")

    except Exception as e:
        logger.error(f"Error in full paper analysis: {e}")
        return {
            "analysis": "",
            "success": False,
            "error_message": f"Full paper analysis failed: {str(e)}"
        }
