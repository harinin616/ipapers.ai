import logging
from datetime import datetime, timedelta
from typing import List, Optional

from app.models.paper import Paper

logger = logging.getLogger(__name__)


def _match_authors(paper_authors: Optional[List[str]], filters: List[str], author_logic: str = "AND") -> bool:
    if not filters:
        return True
    pa = [a.lower() for a in (paper_authors or [])]
    
    if author_logic.upper() == "AND" and len(filters) > 1:
        # AND logic: paper must have ALL authors
        for f in filters:
            f_low = (f or "").lower().strip()
            if not f_low:
                continue
                
            # Check if this author exists in the paper
            author_found = False
            for author in pa:
                if ' ' in f_low:
                    # Full name: try exact match first, then check if all words exist as complete words
                    if f_low == author:
                        author_found = True
                        break
                    # Check if all search words exist as complete words in the author name
                    search_words = f_low.split()
                    author_words = author.split()
                    if all(any(search_word == author_word for author_word in author_words) for search_word in search_words):
                        author_found = True
                        break
                else:
                    # Partial name: check if it matches any part of the author name exactly
                    name_parts = author.split()
                    if any(f_low == part for part in name_parts):
                        author_found = True
                        break
            
            if not author_found:
                return False  # This author is missing, so AND condition fails
        return True  # All authors found
    else:
        # OR logic: paper must have ANY of the authors
        for f in filters:
            f_low = (f or "").lower().strip()
            if not f_low:
                continue
                
            # Handle full names and partial names
            for author in pa:
                if ' ' in f_low:
                    # Full name: try exact match first, then check if all words exist as complete words
                    if f_low == author:
                        return True
                    # Check if all search words exist as complete words in the author name
                    search_words = f_low.split()
                    author_words = author.split()
                    if all(any(search_word == author_word for author_word in author_words) for search_word in search_words):
                        return True
                else:
                    # Partial name: check if it matches any part of the author name exactly
                    name_parts = author.split()
                    if any(f_low == part for part in name_parts):
                        return True
        return False


def _parse_date_token(token: str):
    if not token:
        return None
    t = token.strip().lower()
    if t in ("recent", "latest"):
        return ("recent", None)
    try:
        # Handle traditional operators with dates (LLM will convert natural language to these)
        if t.startswith(">="):
            date_str = t[2:]
            return (">=", _parse_date_string(date_str))
        if t.startswith("<="):
            date_str = t[2:]
            return ("<=", _parse_date_string(date_str))
        if t.startswith(">"):
            date_str = t[1:]
            return (">", _parse_date_string(date_str))
        if t.startswith("<"):
            date_str = t[1:]
            return ("<", _parse_date_string(date_str))
        if t.startswith("="):
            date_str = t[1:]
            return ("=", _parse_date_string(date_str))
        
        # Handle "&" for date ranges (e.g., ">=2023 & <=2024")
        if " & " in t:
            parts = t.split(" & ")
            if len(parts) == 2:
                start_cond = _parse_date_token(parts[0].strip())
                end_cond = _parse_date_token(parts[1].strip())
                if start_cond and end_cond:
                    start_op, start_date = start_cond
                    end_op, end_date = end_cond
                    # Return a range - we'll handle this in the matching logic
                    return ("range", (start_date, end_date))
        
        # Handle direct date strings
        parsed_date = _parse_date_string(t)
        if parsed_date:
            return ("=", parsed_date)
    except ValueError:
        return None
    return None


def _parse_date_string(date_str: str):
    """Parse date string in various formats and return datetime object"""
    if not date_str:
        return None
    
    # Clean the input
    date_str = date_str.strip().lower()
    
    # List of date formats to try
    date_formats = [
        # ISO formats
        "%Y-%m-%d",           # 2023-12-25
        "%Y/%m/%d",           # 2023/12/25
        "%Y.%m.%d",           # 2023.12.25
        "%Y_%m_%d",           # 2023_12_25
        "%Y %m %d",           # 2023 12 25
        
        # Month name formats
        "%Y-%B-%d",           # 2023-December-25
        "%Y %B %d",           # 2023 December 25
        "%B %d, %Y",          # December 25, 2023
        "%d %B %Y",           # 25 December 2023
        "%B %Y",              # December 2023
        "%Y %B",              # 2023 December
        
        # Abbreviated month formats
        "%Y-%b-%d",           # 2023-Dec-25
        "%Y %b %d",           # 2023 Dec 25
        "%b %d, %Y",          # Dec 25, 2023
        "%d %b %Y",           # 25 Dec 2023
        "%b %Y",              # Dec 2023
        "%Y %b",              # 2023 Dec
        
        # US formats
        "%m/%d/%Y",           # 12/25/2023
        "%m-%d-%Y",           # 12-25-2023
        "%m.%d.%Y",           # 12.25.2023
        "%m %d %Y",           # 12 25 2023
        
        # European formats
        "%d/%m/%Y",           # 25/12/2023
        "%d-%m-%Y",           # 25-12-2023
        "%d.%m.%Y",           # 25.12.2023
        "%d %m %Y",           # 25 12 2023
        
        # Year only
        "%Y",                 # 2023
        
        # Month and year
        "%Y-%m",              # 2023-09
        "%m/%Y",              # 12/2023
        "%m-%Y",              # 12-2023
        "%m.%Y",              # 12.2023
        "%m %Y",              # 12 2023
        
        # Day and month (assume current year)
        "%m/%d",              # 12/25
        "%m-%d",              # 12-25
        "%m.%d",              # 12.25
        "%m %d",              # 12 25
        "%d/%m",              # 25/12
        "%d-%m",              # 25-12
        "%d.%m",              # 25.12
        "%d %m",              # 25 12
    ]
    
    # Try each format
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            
            # For formats without year, use current year
            if fmt in ["%m/%d", "%m-%d", "%m.%d", "%m %d", "%d/%m", "%d-%m", "%d.%m", "%d %m"]:
                current_year = datetime.now().year
                parsed_date = parsed_date.replace(year=current_year)
            
            # For formats without day, use first day of month
            if fmt in ["%Y-%B", "%Y %B", "%B %Y", "%Y %B", "%Y-%b", "%Y %b", "%b %Y", "%Y %b", 
                      "%Y-%m", "%m/%Y", "%m-%Y", "%m.%Y", "%m %Y"]:
                parsed_date = parsed_date.replace(day=1)
            
            # For year-only format, use January 1st
            if fmt == "%Y":
                parsed_date = parsed_date.replace(month=1, day=1)
            
            return parsed_date
        except ValueError:
            continue
    
    # Try to parse as relative dates
    relative_dates = {
        "today": datetime.now().date(),
        "yesterday": (datetime.now() - timedelta(days=1)).date(),
        "tomorrow": (datetime.now() + timedelta(days=1)).date(),
        "this week": datetime.now().date(),
        "last week": (datetime.now() - timedelta(weeks=1)).date(),
        "next week": (datetime.now() + timedelta(weeks=1)).date(),
        "this month": datetime.now().replace(day=1).date(),
        "last month": (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).date(),
        "next month": (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).date(),
        "this year": datetime.now().replace(month=1, day=1).date(),
        "last year": datetime.now().replace(year=datetime.now().year-1, month=1, day=1).date(),
        "next year": datetime.now().replace(year=datetime.now().year+1, month=1, day=1).date(),
    }
    
    if date_str in relative_dates:
        return datetime.combine(relative_dates[date_str], datetime.min.time())
    
    # Try to extract numbers and create a date
    import re
    numbers = re.findall(r'\d+', date_str)
    if numbers:
        try:
            if len(numbers) == 1:
                # Single number - could be year
                year = int(numbers[0])
                if 1900 <= year <= 2100:
                    return datetime(year, 1, 1)
            elif len(numbers) == 2:
                # Two numbers - could be month/year or day/month
                num1, num2 = int(numbers[0]), int(numbers[1])
                if 1 <= num1 <= 12 and 1900 <= num2 <= 2100:
                    # month/year
                    return datetime(num2, num1, 1)
                elif 1 <= num1 <= 31 and 1 <= num2 <= 12:
                    # day/month (current year)
                    current_year = datetime.now().year
                    return datetime(current_year, num2, num1)
            elif len(numbers) == 3:
                # Three numbers - could be various formats
                num1, num2, num3 = int(numbers[0]), int(numbers[1]), int(numbers[2])
                
                # Try YYYY-MM-DD
                if 1900 <= num1 <= 2100 and 1 <= num2 <= 12 and 1 <= num3 <= 31:
                    return datetime(num1, num2, num3)
                # Try MM-DD-YYYY
                elif 1 <= num1 <= 12 and 1 <= num2 <= 31 and 1900 <= num3 <= 2100:
                    return datetime(num3, num1, num2)
                # Try DD-MM-YYYY
                elif 1 <= num1 <= 31 and 1 <= num2 <= 12 and 1900 <= num3 <= 2100:
                    return datetime(num3, num2, num1)
        except ValueError:
            pass
    
    return None


def _match_date(published: Optional[datetime], tokens: List[str]) -> bool:
    if not tokens:
        return True
    if not isinstance(published, datetime):
        return False
    
    for token in tokens:
        if token and token.lower().strip() in ("recent", "latest"):
            # allow through; ordering is handled upstream by DB query
            return True
        if "&" in token:
            parts = [p.strip() for p in token.split("&") if p.strip()]
            ok = True
            for p in parts:
                cond = _parse_date_token(p)
                if not cond:
                    continue
                op, val = cond
                if op == "recent":
                    continue
                if not _compare_dates(published, op, val):
                    ok = False
            if ok:
                return True
        else:
            cond = _parse_date_token(token)
            if not cond:
                # tokens like "recent" are ignored (non-strict)
                continue
            op, val = cond
            if op == "recent":
                return True
            if _compare_dates(published, op, val):
                return True
    return False


def _compare_dates(published: datetime, op: str, val) -> bool:
    """Compare published date with parsed date value"""
    if val is None:
        return False
    
    if op == ">":
        return published > val
    elif op == ">=":
        return published >= val
    elif op == "<":
        return published < val
    elif op == "<=":
        return published <= val
    elif op == "=":
        # For equality, compare only the date part (ignore time)
        # If the parsed date is the first day of a month, treat it as "any day in that month"
        # If the parsed date is January 1st, treat it as "any day in that year"
        if val.day == 1 and val.month == 1:
            # Year-level match: check if it's the same year
            return published.year == val.year
        elif val.day == 1:
            # Month-level match: check if it's the same year and month
            return published.year == val.year and published.month == val.month
        else:
            # Exact date match - compare only the date part, ignore time
            return published.date() == val.date()
    elif op == "range":
        # Handle date ranges: val is a tuple (start_date, end_date)
        if isinstance(val, tuple) and len(val) == 2:
            start_date, end_date = val
            return start_date <= published <= end_date
    
    return False


def _match_platform(paper_platform: Optional[str], filters: List[str]) -> bool:
    if not filters:
        return True
    if not paper_platform:
        return False
    
    paper_platform_lower = paper_platform.lower()
    for f in filters:
        f_low = (f or "").lower().strip()
        if not f_low:
            continue
        # Check if the filter matches the platform exactly
        if f_low == paper_platform_lower:
            return True
    return False


def filter_papers_by_metadata(
    papers: List[Paper],
    authors_filters: List[str],
    date_filters: List[str],
    platform_filters: List[str],
    author_logic: str = "AND",
) -> List[Paper]:
    if not papers:
        return []
    before_cnt = len(papers)
    filtered = [
        p for p in papers
        if _match_authors(p.authors, authors_filters, author_logic)
        and _match_date(p.published_date, date_filters)
        and _match_platform(p.platform, platform_filters)
    ]
    logger.info(f"Metadata pre-filtered papers: {before_cnt} -> {len(filtered)}")
    return filtered


__all__ = ["filter_papers_by_metadata"]


