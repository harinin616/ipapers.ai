import os
import re
from typing import Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PaperInfoExtractor:
    """Extract paper information including platform, PDF and embedding storage directories"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.pdf_base_dir = self.project_root / "data" / "cached_pdfs"
        self.embedding_base_dir = self.project_root / "data" / "cached_embeddings"
        
        # Ensure directories exist
        os.makedirs(self.pdf_base_dir, exist_ok=True)
        os.makedirs(self.embedding_base_dir, exist_ok=True)
    
    def extract_platform(self, paper_id: str) -> str:
        """
        Extract platform information from paper_id based on ID format
        
        Args:
            paper_id: Paper ID in formats like:
                - 2505.24877v1 (arXiv)
                - 2023.acl-long.2 (ACL)
                - 2024.emnlp-main.1 (EMNLP)
                - 2024.naacl-long.1 (NAACL)
        
        Returns:
            Platform name (arxiv, acl, emnlp, naacl, etc.)
        """
        # arXiv format: YYMM.NNNNN[vN] (e.g., 2505.24877v1)
        if re.match(r'^\d{4}\.\d+v?\d*$', paper_id):
            return "arxiv"
        
        # Conference format: YYYY.venue-track.N (e.g., 2023.acl-long.2)
        if '.' in paper_id:
            parts = paper_id.split('.')
            if len(parts) >= 3:
                venue_track = parts[1]
                if '-' in venue_track:
                    venue = venue_track.split('-')[0].lower()
                    return venue
                else:
                    return venue_track.lower()
        
        # If no pattern matches, try to extract from filename-like patterns
        if '_' in paper_id:
            return paper_id.split('_')[0].lower()
        
        raise ValueError(f"Cannot determine platform from paper_id format: {paper_id}")
    
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
    
    def get_pdf_storage_path(self, paper_id: str) -> Path:
        """
        Get the local storage path for PDF file
        
        Args:
            paper_id: Paper ID
        
        Returns:
            Complete path to PDF file
        """
        platform = self.extract_platform(paper_id)
        
        if platform == "arxiv":
            year, month = self.extract_arxiv_info(paper_id)
            # Create directory structure: arxiv/year/month/
            pdf_dir = self.pdf_base_dir / "arxiv" / year / month
            filename = f"{paper_id}.pdf"
        
        elif platform in ["acl", "emnlp", "naacl", "iclr", "nips", "icml"]:
            year, venue, track = self.extract_conference_info(paper_id)
            # Create directory structure: platform/year/venue-track/
            pdf_dir = self.pdf_base_dir / platform / year / f"{venue}-{track}"
            # Use paper_id as filename (replace dots with underscores for safety)
            filename = f"{paper_id.replace('.', '_')}.pdf"
        
        else:
            # Other platforms use generic structure
            pdf_dir = self.pdf_base_dir / platform
            filename = f"{paper_id.replace('.', '_')}.pdf"
        
        # Ensure directory exists
        os.makedirs(pdf_dir, exist_ok=True)
        
        return pdf_dir / filename
    
    def get_embedding_storage_path(self, paper_id: str) -> Path:
        """
        Get the local storage path for embedding file
        
        Args:
            paper_id: Paper ID
        
        Returns:
            Complete path to embedding file
        """
        platform = self.extract_platform(paper_id)
        
        if platform == "arxiv":
            year, month = self.extract_arxiv_info(paper_id)
            # Create directory structure: arxiv/year/month/
            embedding_dir = self.embedding_base_dir / "arxiv" / year / month
            filename = f"{paper_id}.pkl"
        
        elif platform in ["acl", "emnlp", "naacl", "iclr", "nips", "icml"]:
            year, venue, track = self.extract_conference_info(paper_id)
            # Create directory structure: platform/year/venue-track/
            embedding_dir = self.embedding_base_dir / platform / year / f"{venue}-{track}"
            # Use paper_id as filename (replace dots with underscores for safety)
            filename = f"{paper_id.replace('.', '_')}.pkl"
        
        else:
            # Other platforms use generic structure
            embedding_dir = self.embedding_base_dir / platform
            filename = f"{paper_id.replace('.', '_')}.pkl"
        
        # Ensure directory exists
        os.makedirs(embedding_dir, exist_ok=True)
        
        return embedding_dir / filename
    
    def get_pdf_storage_directory(self, paper_id: str) -> Path:
        """
        Get PDF file storage directory (without filename)
        
        Args:
            paper_id: Paper ID
        
        Returns:
            PDF file storage directory path
        """
        return self.get_pdf_storage_path(paper_id).parent
    
    def get_embedding_storage_directory(self, paper_id: str) -> Path:
        """
        Get embedding file storage directory (without filename)
        
        Args:
            paper_id: Paper ID
        
        Returns:
            Embedding file storage directory path
        """
        return self.get_embedding_storage_path(paper_id).parent


# Create global instance
paper_info_extractor = PaperInfoExtractor()


# Convenience functions
def extract_platform(paper_id: str) -> str:
    """Extract paper platform"""
    return paper_info_extractor.extract_platform(paper_id)


def get_pdf_storage_path(paper_id: str) -> Path:
    """Get PDF storage path"""
    return paper_info_extractor.get_pdf_storage_path(paper_id)


def get_embedding_storage_path(paper_id: str) -> Path:
    """Get embedding storage path"""
    return paper_info_extractor.get_embedding_storage_path(paper_id)


def get_pdf_storage_directory(paper_id: str) -> Path:
    """Get PDF storage directory"""
    return paper_info_extractor.get_pdf_storage_directory(paper_id)


def get_embedding_storage_directory(paper_id: str) -> Path:
    """Get embedding storage directory"""
    return paper_info_extractor.get_embedding_storage_directory(paper_id)


if __name__ == "__main__":
    # Test examples
    test_ids = [
        "2505.24877v1",
        "2023.acl-long.2",
        "2024.emnlp-main.1",
        "2024.naacl-long.1"
    ]
    
    for paper_id in test_ids:
        print(f"\nPaper ID: {paper_id}")
        print(f"Platform: {extract_platform(paper_id)}")
        print(f"PDF Path: {get_pdf_storage_path(paper_id)}")
        print(f"PDF Directory: {get_pdf_storage_directory(paper_id)}")
        print(f"Embedding Path: {get_embedding_storage_path(paper_id)}")
        print(f"Embedding Directory: {get_embedding_storage_directory(paper_id)}") 