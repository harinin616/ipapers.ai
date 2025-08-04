import os
import re
import uuid
from typing import Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PaperInfoExtractor:
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.pdf_base_dir = self.project_root / "data" / "cached_pdfs"
        self.embedding_base_dir = self.project_root / "data" / "cached_embeddings"
        
        # Ensure directories exist
        os.makedirs(self.pdf_base_dir, exist_ok=True)
        os.makedirs(self.embedding_base_dir, exist_ok=True)
    
    def extract_platform(self, paper_id: str) -> str:

        # Check for UUID format first
        try:
            uuid.UUID(paper_id)
            return "upload"
        except (ValueError, TypeError):
            pass

        # biorxiv format: biorxiv_XXX_YYY
        if paper_id.startswith("biorxiv_"):
            return "biorxiv"

        # arXiv format: YYMM.NNNNN[vN] (e.g., 2505.24877v1)
        arxiv_pattern = r"^\d{4}\.\d{4,5}(v\d+)?$"
        # 旧 arXiv 格式 (e.g., hep-th/9901001)
        old_arxiv_pattern = r"^[a-zA-Z\-]+\/\d{7}$"
        
        if re.match(arxiv_pattern, paper_id) or re.match(old_arxiv_pattern, paper_id):
            return "arxiv"

        # Conference paper format: YYYY.venue-track.ID (e.g., 2023.acl-long.123)
        conference_pattern = r"^\d{4}\.([\w\-]+)\.\d+$"
        match = re.match(conference_pattern, paper_id)
        
        if match:
            venue_track = match.group(1)
            
            # 处理带有"findings-"前缀的特殊情况
            if venue_track.startswith("findings-"):
                # 返回主要的会议平台，如"acl"、"naacl"等
                main_venue = venue_track.split("-")[1] 
                return main_venue
            
            # 提取主要的会议平台 (acl, naacl, emnlp, etc.)
            venue = venue_track.split("-")[0]
            return venue
            
        # 尝试从paper_id中提取其他可能的平台
        if "acl" in paper_id.lower():
            return "acl"
        elif "naacl" in paper_id.lower():
            return "naacl"
        elif "emnlp" in paper_id.lower():
            return "emnlp"
        
        # 默认为arxiv
        logger.warning(f"Could not determine platform from paper_id: {paper_id}, defaulting to 'arxiv'")
        return "arxiv"
    
    def extract_arxiv_info(self, paper_id: str) -> Tuple[str, str]:
        """
        Extract year and month information from arXiv paper
        
        Args:
            paper_id: arXiv paper ID like "2505.24877v1"
        
        Returns:
            (year, month) tuple
        """
        arxiv_number = paper_id
        # Remove version number
        if 'v' in arxiv_number:
            arxiv_number = arxiv_number.split('v')[0]
        
        # arXiv ID format: YYMM.NNNNN
        if len(arxiv_number) >= 4:
            year_month = arxiv_number[:4]
            year = year_month[:2]
            month = year_month[2:4]
            return year, month
        else:
            raise ValueError(f"Invalid arXiv ID format: {arxiv_number}")
    
    def extract_conference_info(self, paper_id: str) -> Tuple[str, str, str]:
        """
        Extract year and conference information from conference paper
        
        Args:
            paper_id: Conference paper ID like "2023.acl-long.2"
        
        Returns:
            (year, venue, track) tuple
        """
        # Parse format: year.venue-track.number
        parts = paper_id.split('.')
        if len(parts) >= 3:
            year = parts[0]
            venue_track = parts[1]
            
            # Separate venue and track
            if '-' in venue_track:
                venue, track = venue_track.split('-', 1)
            else:
                venue = venue_track
                track = "main"
            
            return year, venue, track
        else:
            raise ValueError(f"Invalid conference paper ID format: {paper_id}")
    
    def extract_biorxiv_info(self, paper_id: str) -> Tuple[str, str]:
        """
        Extract information from biorxiv paper ID
        
        Args:
            paper_id: biorxiv paper ID like "biorxiv_XXX_YYY"
        
        Returns:
            (year, month) tuple, using current year/month as placeholder
        """
        # For biorxiv, we don't have year/month in the ID
        # We'll use a generic structure with "biorxiv" as the directory
        import datetime
        now = datetime.datetime.now()
        year = str(now.year)[2:] # Last two digits
        month = str(now.month).zfill(2)
        
        return year, month


    def get_pdf_storage_directory(self, paper_id: str) -> Path:

        platform = self.extract_platform(paper_id)
        
        if platform == "arxiv":
            year, month = self.extract_arxiv_info(paper_id)
            directory = self.pdf_base_dir / "arxiv" / year / month
        elif platform == "biorxiv":
            year, month = self.extract_biorxiv_info(paper_id)
            directory = self.pdf_base_dir / "biorxiv" / year / month
        else:
            # For conference papers (acl, naacl, emnlp, etc.)
            year, venue, track = self.extract_conference_info(paper_id)
            directory = self.pdf_base_dir / venue / year
        
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        return directory

    def get_embedding_storage_directory(self, paper_id: str) -> Path:
        """
        Get embedding storage directory based on paper platform and date.
        
        For arxiv papers: embedding_base_dir/arxiv/year/month/
        For conference papers: embedding_base_dir/venue/year/
        """
        platform = self.extract_platform(paper_id)
        
        if platform == "arxiv":
            year, month = self.extract_arxiv_info(paper_id)
            directory = self.embedding_base_dir / "arxiv" / year / month
        elif platform == "biorxiv":
            year, month = self.extract_biorxiv_info(paper_id)
            directory = self.embedding_base_dir / "biorxiv" / year / month
        else:
            # For conference papers (acl, naacl, emnlp, etc.)
            year, venue, track = self.extract_conference_info(paper_id)
            directory = self.embedding_base_dir / venue / year
        
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        return directory
    


    def get_pdf_url(self, paper_id: str) -> str:
        platform = self.extract_platform(paper_id)
        
        if platform == "arxiv":
            # arXiv URL format: https://arxiv.org/pdf/{paper_id}
            return f"https://arxiv.org/pdf/{paper_id}"
        
        elif platform == "biorxiv":
            # Extract DOI from paper_id (format: biorxiv_10.1101_XXXXXX)
            doi_parts = paper_id.split('_')
            if len(doi_parts) >= 3:
                doi_number = doi_parts[2]
                version = "1"  # Default version if not specified
                # Use the standard biorxiv PDF URL format
                return f"https://www.biorxiv.org/content/10.1101/{doi_number}v{version}.full.pdf"
            else:
                raise ValueError(f"Invalid biorxiv paper ID format: {paper_id}")
        
        elif platform in ["acl", "emnlp", "naacl", "eacl", "coling"]:
            # 检查是否是findings论文
            if "findings" in paper_id.lower():
                # ACL Anthology URL format for findings papers: https://aclanthology.org/{paper_id}.pdf
                return f"https://aclanthology.org/{paper_id}.pdf"
            # ACL Anthology URL format: https://aclanthology.org/{paper_id}.pdf
            return f"https://aclanthology.org/{paper_id}.pdf"
        
        elif platform == "iclr":
            # ICLR OpenReview URL format (approximate)
            year, venue, track = self.extract_conference_info(paper_id)
            return f"https://openreview.net/pdf?id={paper_id}"
        
        elif platform in ["nips", "neurips"]:
            # NeurIPS papers URL format (approximate)
            year, venue, track = self.extract_conference_info(paper_id)
            return f"https://papers.nips.cc/paper/{year}/file/{paper_id}.pdf"
        
        elif platform == "icml":
            # ICML proceedings URL format (approximate)
            year, venue, track = self.extract_conference_info(paper_id)
            return f"https://proceedings.mlr.press/{paper_id}.pdf"
        
        else:
            # For unknown platforms, return a generic format
            # 使用ACL Anthology格式作为后备
            if paper_id.startswith("20"):  # 如果ID以年份开始，尝试ACL Anthology格式
                return f"https://aclanthology.org/{paper_id}.pdf"
            raise ValueError(f"PDF URL format not supported for platform: {platform}")


# Create global instance
paper_info_extractor = PaperInfoExtractor()


# Convenience functions
def extract_platform(paper_id: str) -> str:
    """Extract paper platform"""
    return paper_info_extractor.extract_platform(paper_id)


def get_pdf_storage_directory(paper_id: str) -> Path:
    """Get PDF storage directory"""
    return paper_info_extractor.get_pdf_storage_directory(paper_id)


def get_embedding_storage_directory(paper_id: str) -> Path:
    """Get embedding storage directory"""
    return paper_info_extractor.get_embedding_storage_directory(paper_id)


def get_pdf_url(paper_id: str) -> str:
    """Get PDF download URL"""
    return paper_info_extractor.get_pdf_url(paper_id)

paper_info_extractor = PaperInfoExtractor()