# from fastapi import APIRouter, HTTPException, Depends
# from sqlalchemy.orm import Session
# import logging
# import asyncio
# from fastapi.concurrency import run_in_threadpool
# from app.models.paper import ConvPaperSearchRequest, ConvPaperSearchResponse, Paper
# from app.services.conv_db_service import conv_db_service
# from app.services.conv_vector_search_service import conv_vector_search_service

# from app.services.conv_keyword_search_service import conv_keyword_search_service 
# from app.services.conv_llm_service import conv_llm_service
# from app.services import search_log_service
# from app.services.metadata_filter_service import filter_papers_by_metadata
# from datetime import datetime
# logger = logging.getLogger(__name__)

# router = APIRouter()

# @router.post("/", response_model=PaperSearchResponse)
# async def conv_search_papers(search_request: ConvPaperSearchRequest):
#     """
#     get results from local vector search
#     then rerank the results by LLM
#     """
#     try:
#         logger.info(f"Received search request: {search_request.llm_output}")
#         query = search_request.llm_output.get("refined_query", "")

#         fields = search_request.llm_output.get("fields", {}) or {}
#         date_filters = fields.get("date", []) or []
#         authors_filters = fields.get("authors", []) or []
#         platform_filters = fields.get("platform", []) or []
#         author_logic = fields.get("author_logic", "AND")  # Default to AND for multiple authors
#         logger.info(f"Fieldsssss: {fields}")
#         logger.info(f"Date filters: {date_filters}")
#         logger.info(f"Authors filters: {authors_filters}")
#         logger.info(f"Platform filters: {platform_filters}")
#         logger.info(f"Author logic: {author_logic}")
#         # Determine whether date filters are actually parseable/effective
#         def _is_parseable_date_token(token: str) -> bool:
#             if not token:
#                 return False
#             t = token.strip().lower()
#             if "&" in t:
#                 parts = [p for p in t.split("&") if p]
#                 return any(_is_parseable_date_token(p) for p in parts)
            
#             # Extract the date part after traditional operators (LLM will convert natural language to these)
#             if t.startswith(">=") or t.startswith("<=") or t.startswith(">") or t.startswith("<") or t.startswith("="):
#                 date_part = t.lstrip(">=<")
#             else:
#                 date_part = t
            
#             # Check if it's a valid date format
#             return _is_valid_date_format(date_part)
        
#         def _is_valid_date_format(date_str: str) -> bool:
#             """Check if date string is in a valid format"""
#             if not date_str:
#                 return False
            
#             # Clean the input
#             date_str = date_str.strip().lower()
            
#             # List of date formats to try
#             date_formats = [
#                 # ISO formats
#                 "%Y-%m-%d",           # 2023-12-25
#                 "%Y/%m/%d",           # 2023/12/25
#                 "%Y.%m.%d",           # 2023.12.25
#                 "%Y_%m_%d",           # 2023_12_25
#                 "%Y %m %d",           # 2023 12 25
                
#                 # Month name formats
#                 "%Y-%B-%d",           # 2023-December-25
#                 "%Y %B %d",           # 2023 December 25
#                 "%B %d, %Y",          # December 25, 2023
#                 "%d %B %Y",           # 25 December 2023
#                 "%B %Y",              # December 2023
#                 "%Y %B",              # 2023 December
                
#                 # Abbreviated month formats
#                 "%Y-%b-%d",           # 2023-Dec-25
#                 "%Y %b %d",           # 2023 Dec 25
#                 "%b %d, %Y",          # Dec 25, 2023
#                 "%d %b %Y",           # 25 Dec 2023
#                 "%b %Y",              # Dec 2023
#                 "%Y %b",              # 2023 Dec
                
#                 # US formats
#                 "%m/%d/%Y",           # 12/25/2023
#                 "%m-%d-%Y",           # 12-25-2023
#                 "%m.%d.%Y",           # 12.25.2023
#                 "%m %d %Y",           # 12 25 2023
                
#                 # European formats
#                 "%d/%m/%Y",           # 25/12/2023
#                 "%d-%m-%Y",           # 25-12-2023
#                 "%d.%m.%Y",           # 25.12.2023
#                 "%d %m %Y",           # 25 12 2023
                
#                 # Year only
#                 "%Y",                 # 2023
                
#                 # Month and year
#                 "%Y-%m",              # 2023-09
#                 "%m/%Y",              # 12/2023
#                 "%m-%Y",              # 12-2023
#                 "%m.%Y",              # 12.2023
#                 "%m %Y",              # 12 2023
                
#                 # Day and month (assume current year)
#                 "%m/%d",              # 12/25
#                 "%m-%d",              # 12-25
#                 "%m.%d",              # 12.25
#                 "%m %d",              # 12 25
#                 "%d/%m",              # 25/12
#                 "%d-%m",              # 25-12
#                 "%d.%m",              # 25.12
#                 "%d %m",              # 25 12
#             ]
            
#             # Try each format
#             for fmt in date_formats:
#                 try:
#                     datetime.strptime(date_str, fmt)
#                     return True
#                 except ValueError:
#                     continue
            
#             # Check for relative dates
#             relative_dates = [
#                 "today", "yesterday", "tomorrow", "this week", "last week", "next week",
#                 "this month", "last month", "next month", "this year", "last year", "next year"
#             ]
#             if date_str in relative_dates:
#                 return True
            
#             # Check for numeric patterns
#             import re
#             numbers = re.findall(r'\d+', date_str)
#             if numbers and 1 <= len(numbers) <= 3:
#                 return True
            
#             return False

#         has_effective_date = any(_is_parseable_date_token(tok) for tok in (date_filters or []))
#         has_effective_filters = bool(authors_filters) or has_effective_date or bool(platform_filters)

#         # 1) Pre-fetch candidate IDs by metadata (authors/date) only if effective
#         if has_effective_filters:
#             candidates = await conv_db_service.get_candidate_ids_by_metadata(
#                 authors=authors_filters,
#                 date_tokens=date_filters,
#                 platforms=platform_filters,
#                 author_logic=author_logic,
#                 limit=5000,
#             )
#             allow_ids = set(candidates)
#             logger.info(f"Metadata filtering returned {len(allow_ids)} candidate IDs")
#             logger.info(f"Sample allow_ids: {list(allow_ids)[:5] if allow_ids else 'None'}")
#             if not allow_ids:
#                 logger.warning("No candidates found from metadata filtering, returning empty results")
#                 return PaperSearchResponse(results=[], count=0)
#         else:
#             allow_ids = None
#             logger.info("No effective metadata filters, allowing all papers for search")

#         # 2) Run retrieval constrained by allowlist (if any)
#         logger.info(f"Starting vector search with query: '{query}' and allow_ids: {len(allow_ids) if allow_ids else 'None'}")
#         logger.info(f"Starting keyword search with query: '{query}' and allow_ids: {len(allow_ids) if allow_ids else 'None'}")
#         vec_task   = asyncio.create_task(conv_vector_search_service.search(query=query, allow_ids=allow_ids))
#         keyword_task= asyncio.create_task(conv_keyword_search_service.search(query=query, allow_ids=allow_ids))


#         try:
#             paper_id_platform_pairs, keyword_paper_id_platform_pairs = await asyncio.gather(vec_task, keyword_task)
#         except Exception as e:
#             logger.error(f"Error in vector/keyword search: {e}", exc_info=True)
#             paper_id_platform_pairs, keyword_paper_id_platform_pairs = [], []

#         logger.info(f"Vector search returned {len(paper_id_platform_pairs)} paper IDs")
#         logger.info(f"Keyword search returned {len(keyword_paper_id_platform_pairs)} paper IDs")
        
#         combined_local_ids = set(paper_id_platform_pairs).union(set(keyword_paper_id_platform_pairs))
#         combined_local_ids = list(combined_local_ids)

#         if not combined_local_ids:
#             logger.warning("No results from vector or keyword search")
#             # If we had metadata filters but got no results, try without metadata filters as fallback
#             if has_effective_filters:
#                 logger.info("Attempting fallback search without metadata filters")
#                 try:
#                     vec_task_fallback = asyncio.create_task(conv_vector_search_service.search(query=query, allow_ids=None))
#                     keyword_task_fallback = asyncio.create_task(conv_keyword_search_service.search(query=query, allow_ids=None))
#                     paper_id_platform_pairs_fallback, keyword_paper_id_platform_pairs_fallback = await asyncio.gather(vec_task_fallback, keyword_task_fallback)
                    
#                     combined_local_ids = set(paper_id_platform_pairs_fallback).union(set(keyword_paper_id_platform_pairs_fallback))
#                     combined_local_ids = list(combined_local_ids)
                    
#                     logger.info(f"Fallback search returned {len(combined_local_ids)} paper IDs")
                    
#                     if not combined_local_ids:
#                         logger.warning("Fallback search also returned no results")
#                         return PaperSearchResponse(results=[], count=0)
#                 except Exception as e:
#                     logger.error(f"Error in fallback search: {e}", exc_info=True)
#                     return PaperSearchResponse(results=[], count=0)
#             else:
#                 return PaperSearchResponse(results=[], count=0)
        
#         logger.info(f"Total unique local IDs to fetch: {len(combined_local_ids)}")
#         #logger.info(f"Found {len(arxiv_papers)} papers from arXiv search")

#         papers = await conv_db_service.get_papers_by_ids(combined_local_ids)

#         # ---- Metadata pre-filtering (authors/date/platform) before rerank ----
#         papers = filter_papers_by_metadata(
#             papers=papers,
#             authors_filters=authors_filters,
#             date_filters=date_filters,
#             platform_filters=platform_filters,
#             author_logic=author_logic,
#         )

#         # 去重
#         unique = []
#         seen_titles = set()

#         for p in papers:
#             if p.title not in seen_titles:
#                 unique.append(p)
#                 seen_titles.add(p.title)

#     #    for p in arxiv_papers:
#      #       if p.title not in seen_titles:
#       #          unique.append(p)
#        #         seen_titles.add(p.title)

#         papers = unique
        

#         documents=[p.title+p.abstract for p in papers]
#         rerank = await conv_llm_service.get_rerank(documents=documents,query=query)

#         new_papers=[papers[idx] for idx in rerank]
#         logger.info(f"Reranked papers: {[p.pdf_url for p in new_papers]}")
#         paper_responses = [
#             Paper(
#                 paper_id=p.paper_id,
#                 title=p.title,
#                 authors=p.authors,
#                 abstract=p.abstract,
#                 categories=p.categories,
#                 pdf_url=p.pdf_url.replace("http://", "https://"),
#                 published_date=p.published_date,
#                 updated_date=p.updated_date,
#                 platform=p.platform  # 直接使用返回的platform属性
#             ) for p in new_papers
#         ]
        
#         # Always return papers immediately, no summary generation in main search
#         await search_log_service.append_record(
#             query=query,
#             results=[r.model_dump() for r in paper_responses]
#         )
#         return PaperSearchResponse(
#             results=paper_responses,
#             count=len(paper_responses),
#             summary=None  # Summary will be generated separately
#         )
        
#     except Exception as e:
#         logger.error(f"Error searching papers: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error searching papers: {str(e)}"
#         ) 