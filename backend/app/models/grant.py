from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Grant(BaseModel):
    """Grant opportunity model"""
    grant_id: str
    title: str
    agency: str
    synopsis: str = ""
    categories: Optional[List[str]] = None
    detail_url: str
    posted_date: datetime
    updated_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    status: Optional[str] = None
