from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import glob
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Define the category mapping
DISCIPLINE_GROUPS = {
    'Computer Science (cs.)': 'computer_science',
    'Economics (econ.)': 'economics',
    'Electrical Engineering & Systems Science (eess.)': 'electrical_engineering',
    'Mathematics (math.)': 'mathematics',
    'Statistics (stat.)': 'statistics',
    'Quantitative Biology (q-bio.)': 'quantitative_biology',
    'Quantitative Finance (q-fin.)': 'quantitative_finance',
    'Physics': 'physics'
}

# Pydantic models
class CategoryData(BaseModel):
    category: str
    display_name: str
    word_cloud_url: Optional[str] = None
    summaries: List[str] = []

class DailyFeedResponse(BaseModel):
    categories: List[CategoryData]
    last_updated: Optional[str] = None

# Helper function to get data path
def get_daily_feed_path():
    return Path(__file__).parent.parent.parent / "data" / "daily_feed"

@router.get(
    "/",
    response_model=DailyFeedResponse,
    summary="Get daily feed data for all categories",
)
async def get_daily_feed():
    """
    Get daily feed data including word clouds and summaries for all categories.
    """
    try:
        base_path = get_daily_feed_path()
        categories = []
        
        for display_name, folder_name in DISCIPLINE_GROUPS.items():
            category_path = base_path / folder_name
            
            # Initialize category data
            category_data = CategoryData(
                category=folder_name,
                display_name=display_name,
                summaries=[]
            )
            
            # Check for word cloud image
            images_path = category_path / "images"
            if images_path.exists():
                # Look for image files (png, jpg, jpeg)
                image_files = []
                for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif']:
                    image_files.extend(glob.glob(str(images_path / ext)))
                
                if image_files:
                    # Use the first image found
                    image_file = Path(image_files[0])
                    category_data.word_cloud_url = f"/api/daily_feed/image/{folder_name}/{image_file.name}"
            
            # Read summary files
            summaries_path = category_path / "summaries"
            if summaries_path.exists():
                # Look for markdown files
                md_files = glob.glob(str(summaries_path / "*.md"))
                for md_file in sorted(md_files):
                    try:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if content:
                                category_data.summaries.append(content)
                    except Exception as e:
                        logger.warning(f"Error reading summary file {md_file}: {e}")
            
            categories.append(category_data)
        
        return DailyFeedResponse(categories=categories)
        
    except Exception as e:
        logger.error(f"Error getting daily feed data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve daily feed data"
        )

@router.get(
    "/image/{category}/{filename}",
    summary="Get word cloud image for a specific category",
)
async def get_category_image(category: str, filename: str):
    """
    Serve word cloud images for categories.
    """
    try:
        # Validate category
        if category not in DISCIPLINE_GROUPS.values():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        base_path = get_daily_feed_path()
        image_path = base_path / category / "images" / filename
        
        if not image_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {category}/{filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to serve image"
        ) 