import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import uuid

from app.services.db_service import db_service
from app.services.vector_search_service import vector_search_service
from app.services.llm_service import llm_service
from app.models.paper import Paper

logger = logging.getLogger(__name__)

class RecommendationService:
    """
    Service for generating paper recommendations based on user's file list
    """
    
    def __init__(self):
        self.max_recommendations = 50
        self.similarity_threshold = 0.1
        
    async def get_user_paper_recommendations(
        self, 
        user_id: str, 
        limit: int = 20,
        exclude_existing: bool = True
    ) -> List[Paper]:
        """
        Generate paper recommendations based on user's existing papers in all folders
        
        Args:
            user_id: User UUID string
            limit: Maximum number of recommendations to return
            exclude_existing: Whether to exclude papers already in user's folders
            
        Returns:
            List of recommended Paper objects
        """
        try:
            logger.info(f"Generating recommendations for user {user_id}")
            
            # Convert user_id to UUID if it's a string
            if isinstance(user_id, str):
                if user_id.isdigit():
                    user_uuid = await db_service.get_uuid_by_user_id(int(user_id))
                else:
                    user_uuid = uuid.UUID(user_id)
            else:
                user_uuid = user_id
                
            if not user_uuid:
                logger.warning(f"Could not find UUID for user {user_id}")
                return []
            
            # Get all user's papers from all folders
            user_papers = await self._get_user_papers(user_uuid)
            
            if not user_papers:
                logger.info(f"No papers found for user {user_id}")
                return []
                
            logger.info(f"Found {len(user_papers)} papers for user {user_id}")
            
            # Generate recommendations based on user's papers
            recommendations = await self._generate_recommendations_from_papers(
                user_papers, limit * 3  # Get more candidates for better filtering
            )
            
            # Filter out existing papers if requested
            if exclude_existing:
                existing_paper_keys = {(p['paper_id'], p['platform']) for p in user_papers}
                recommendations = [
                    rec for rec in recommendations 
                    if (rec.paper_id, rec.platform) not in existing_paper_keys
                ]
            
            # Limit results
            recommendations = recommendations[:limit]
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {e}", exc_info=True)
            return []
    
    async def get_folder_based_recommendations(
        self, 
        folder_id: int, 
        limit: int = 20,
        exclude_existing: bool = True
    ) -> List[Paper]:
        """
        Generate paper recommendations based on papers in a specific folder
        
        Args:
            folder_id: Folder ID to base recommendations on
            limit: Maximum number of recommendations to return
            exclude_existing: Whether to exclude papers already in the folder
            
        Returns:
            List of recommended Paper objects
        """
        try:
            logger.info(f"Generating recommendations for folder {folder_id}")
            
            # Get papers from the specific folder
            folder_papers = await db_service.get_files_by_folder_id(folder_id)
            
            if not folder_papers:
                logger.info(f"No papers found in folder {folder_id}")
                return []
                
            logger.info(f"Found {len(folder_papers)} papers in folder {folder_id}")
            
            # Generate recommendations based on folder's papers
            recommendations = await self._generate_recommendations_from_papers(
                folder_papers, limit * 3
            )
            
            # Filter out existing papers if requested
            if exclude_existing:
                existing_paper_keys = {(p['paper_id'], p['platform']) for p in folder_papers}
                recommendations = [
                    rec for rec in recommendations 
                    if (rec.paper_id, rec.platform) not in existing_paper_keys
                ]
            
            # Limit results
            recommendations = recommendations[:limit]
            
            logger.info(f"Generated {len(recommendations)} recommendations for folder {folder_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for folder {folder_id}: {e}", exc_info=True)
            return []

    async def _get_user_papers(self, user_uuid: uuid.UUID) -> List[Dict]:
        """
        Get all papers from all user's folders

        Args:
            user_uuid: User UUID

        Returns:
            List of paper dictionaries with paper_id, platform, title, abstract
        """
        try:
            folders = await db_service.get_folders_with_files(user_uuid)
            all_papers = []

            for folder in folders:
                for file_info in folder.get('files', []):
                    all_papers.append({
                        'paper_id': file_info['paper_id'],
                        'platform': file_info['platform'],
                        'title': file_info.get('title', ''),
                        'abstract': file_info.get('abstract', '')
                    })

            # Remove duplicates based on paper_id and platform
            seen = set()
            unique_papers = []
            for paper in all_papers:
                key = (paper['paper_id'], paper['platform'])
                if key not in seen:
                    seen.add(key)
                    unique_papers.append(paper)

            return unique_papers

        except Exception as e:
            logger.error(f"Error getting user papers: {e}", exc_info=True)
            return []

    async def _generate_recommendations_from_papers(
        self,
        source_papers: List[Dict],
        limit: int = 50
    ) -> List[Paper]:
        """
        Generate recommendations based on a list of source papers

        Args:
            source_papers: List of paper dictionaries to base recommendations on
            limit: Maximum number of recommendations to generate

        Returns:
            List of recommended Paper objects
        """
        try:
            if not source_papers:
                return []

            # Collect all recommendation candidates
            all_candidates = []
            candidate_scores = defaultdict(float)

            # For each source paper, find similar papers
            for paper in source_papers:
                # Create search query from title and abstract
                search_query = self._create_search_query(paper)

                # Use vector search to find similar papers
                similar_paper_tuples = await vector_search_service.vector_search(
                    search_query, k=20
                )

                # Get paper objects for the similar papers
                if similar_paper_tuples:
                    similar_papers = await db_service.get_papers_by_ids(similar_paper_tuples)

                    # Score papers based on position in results (higher score for earlier results)
                    for i, similar_paper in enumerate(similar_papers):
                        paper_key = (similar_paper.paper_id, similar_paper.platform)
                        # Score decreases with position, max score is 1.0
                        score = max(0.1, 1.0 - (i * 0.05))
                        candidate_scores[paper_key] += score

                        # Add to candidates if not already there
                        if not any(
                            (p.paper_id, p.platform) == paper_key
                            for p in all_candidates
                        ):
                            all_candidates.append(similar_paper)

            # Sort candidates by aggregated score
            scored_candidates = [
                (paper, candidate_scores[(paper.paper_id, paper.platform)])
                for paper in all_candidates
            ]
            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            # Return top candidates
            recommendations = [paper for paper, score in scored_candidates[:limit]]

            logger.info(f"Generated {len(recommendations)} recommendations from {len(source_papers)} source papers")
            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations from papers: {e}", exc_info=True)
            return []

    def _create_search_query(self, paper: Dict) -> str:
        """
        Create a search query from paper title and abstract

        Args:
            paper: Paper dictionary with title and abstract

        Returns:
            Search query string
        """
        title = paper.get('title', '').strip()
        abstract = paper.get('abstract', '').strip()

        # Combine title and first part of abstract for search
        query_parts = []
        if title:
            query_parts.append(title)

        if abstract:
            # Use first 200 characters of abstract
            abstract_snippet = abstract[:200]
            query_parts.append(abstract_snippet)

        return ' '.join(query_parts)

# Create singleton instance
recommendation_service = RecommendationService()
