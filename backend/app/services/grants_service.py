import asyncio
import logging
from datetime import date, datetime
from typing import List, Optional

import httpx

from app.models.grant import Grant

logger = logging.getLogger(__name__)


class GrantsService:
    """Fetch and normalize grant opportunities into Grant objects."""

    def __init__(self):
        # Public Grants.gov search API (JSON). This endpoint is commonly used by the site.
        # We use a conservative timeout and small concurrency.
        self.search_url = "https://www.grants.gov/grantsws/rest/opportunities/search/"
        self.detail_url = "https://www.grants.gov/grantsws/rest/opportunities/{}"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(20.0, connect=10.0),
                follow_redirects=True,
                headers={
                    "User-Agent": "PMo-grants-fetcher/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        # Grants.gov dates are ISO-like; try a few common formats
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value, fmt)
                # Strip tzinfo to match our DB expectations
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return dt
            except Exception:
                continue
        return None

    def _map_opportunity(self, opp: dict) -> Optional[Grant]:
        try:
            grant_id = (
                opp.get("opportunityNumber")
                or opp.get("number")
                or opp.get("id")
            )
            if not grant_id:
                return None

            title = opp.get("opportunityTitle") or opp.get("title") or "Untitled Opportunity"
            synopsis = (
                opp.get("synopsis")
                or opp.get("description")
                or opp.get("summary")
                or ""
            )
            agency = opp.get("agency") or opp.get("agencyName") or opp.get("agencyCode") or "Unknown Agency"

            # Dates
            posted_date = (
                self._parse_date(opp.get("postedDate"))
                or self._parse_date(opp.get("openDate"))
                or self._parse_date(opp.get("publishDate"))
                or datetime.utcnow()
            )
            updated_date = (
                self._parse_date(opp.get("lastUpdatedDate"))
                or self._parse_date(opp.get("closeDate"))
                or posted_date
            )
            close_date = self._parse_date(opp.get("closeDate"))

            # URL
            detail_url = (
                opp.get("opportunityUrl")
                or opp.get("url")
                or f"https://simpler.grants.gov/opportunity/{grant_id}"
            )

            # Categories (CFDA, category)
            categories = []
            cfda = opp.get("cfdaList") or opp.get("cfdaNumbers") or opp.get("cfda")
            if isinstance(cfda, list):
                categories.extend([str(x) for x in cfda if x])
            elif isinstance(cfda, str) and cfda:
                categories.append(cfda)
            main_cat = opp.get("category") or opp.get("categoryName")
            if isinstance(main_cat, str) and main_cat:
                categories.append(main_cat)

            status = opp.get("opportunityStatus") or opp.get("status")

            grant = Grant(
                grant_id=str(grant_id),
                title=title,
                agency=agency,
                synopsis=synopsis,
                categories=categories or None,
                detail_url=detail_url,
                posted_date=posted_date,
                updated_date=updated_date,
                close_date=close_date,
                status=status,
            )
            return grant
        except Exception as e:
            logger.error(f"Failed to map opportunity to Grant: {e}", exc_info=True)
            return None

    async def fetch_grants(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 500
    ) -> List[Grant]:
        try:
            client = await self._get_client()

            # Build search payload. Grants.gov expects POST with JSON filters.
            # See public patterns; we filter by postedDate range when provided.
            filters: dict = {
                "startRecordNum": 0,
                "oppStatuses": ["posted", "forecast"],
                "sortBy": "postedDate|desc",
                "rows": max_results,
            }

            if start_date or end_date:
                # Format as YYYY-MM-DD
                if start_date:
                    filters["postedFrom"] = start_date.strftime("%Y-%m-%d")
                if end_date:
                    filters["postedTo"] = end_date.strftime("%Y-%m-%d")

            resp = await client.post(self.search_url, json=filters)

            # Some environments may still see a 3xx; explicitly handle and retry
            if 300 <= resp.status_code < 400:
                redirect_to = resp.headers.get("Location")
                if redirect_to:
                    logger.info(f"Redirecting grants search to {redirect_to}")
                    resp = await client.post(redirect_to, json=filters)

            resp.raise_for_status()
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

            opportunities = (
                data.get("opportunities")
                or data.get("searchResults")
                or data.get("items")
                or []
            )

            grants: List[Grant] = []
            for opp in opportunities:
                grant = self._map_opportunity(opp)
                if grant:
                    grants.append(grant)

            logger.info(f"Fetched {len(grants)} grant opportunities")
            return grants
        except httpx.HTTPStatusError as e:
            logger.error(f"Grants search HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching grants: {e}", exc_info=True)
            return []

    async def aclose(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None


grants_service = GrantsService()
