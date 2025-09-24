import logging
import asyncio
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from app.services.grant_db_service import grant_db_service
from app.services.grant_vector_search_service import grant_vector_search_service
from app.services.conv_llm_service import conv_llm_service

logger = logging.getLogger(__name__)

class ImprovedGrantSearchService:
    """
    Improved grant search service
    Focuses on grant-specific search and analysis
    """

    def __init__(self):
        self.max_context_turns = 8
        self.session_contexts = {}

    async def process_grant_search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        conversation_history: List[dict] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for grant search
        """
        try:
            conversation_history = conversation_history or []
            
            logger.info(f"Processing grant search for query: '{query}'")
            
            # Analyze intent for grant search
            intent_result = await self._analyze_grant_intent_with_context(
                query, conversation_history
            )
            
            if intent_result["intent"] == "search_grants":
                # User wants to search grants
                return await self._handle_grant_search(
                    intent_result, session_id, conversation_history
                )
            elif intent_result["intent"] == "clarify":
                # Need clarification
                return self._handle_clarification(intent_result)
            else:
                # General chat about grants
                return {
                    "action": "chat",
                    "message": intent_result["answer"],
                    "grants": [],
                    "count": 0
                }

        except Exception as e:
            logger.error(f"Error in grant search: {e}")
            return {
                "action": "chat",
                "message": "Sorry, I encountered some technical issues. Please describe your grant search needs again.",
                "grants": [],
                "count": 0
            }

    async def _analyze_grant_intent_with_context(
        self, query: str, conversation_history: List[dict]
    ) -> Dict[str, Any]:
        """Analyze user intent for grant search"""
        # Always use fallback for now to ensure consistent behavior
        logger.info(f"Using fallback intent analysis for query: '{query}'")
        return self._fallback_intent_analysis(query, conversation_history)
        
        try:
            # Build context from conversation history
            context = self._build_context(conversation_history)
            
            # Create prompt for grant-specific intent analysis
            prompt = f"""
You are a grant search assistant. Analyze the user's intent and provide a response.

Context from conversation:
{context}

Current query: "{query}"

Determine the user's intent:
1. "search_grants" - User wants to find grants (be generous - if they mention grants, funding, awards, or money, treat as search_grants)
2. "clarify" - Only if the query is completely unclear or unrelated to grants
3. "chat" - General conversation about grants

IMPORTANT: If the user mentions "grants", "funding", "awards", "money", or similar terms, always return "search_grants" intent, even for broad queries.

Respond in JSON format:
{{
    "intent": "search_grants|clarify|chat",
    "refined_query": "refined search query if intent is search_grants",
    "answer": "response message",
    "search_criteria": {{
        "keywords": ["keyword1", "keyword2"],
        "agency": "specific agency if mentioned",
        "category": "specific category if mentioned",
        "date_range": "date range if mentioned"
    }}
}}
"""
            
            response = await conv_llm_service.conversation(
                messages=[{"role": "user", "content": prompt}]
            )
            
            try:
                # Clean response - remove any potential markdown formatting
                import re
                cleaned_response = re.sub(r'```json\s*', '', response)
                cleaned_response = re.sub(r'```\s*', '', cleaned_response)
                cleaned_response = cleaned_response.strip()
                
                result = json.loads(cleaned_response)
                logger.info(f"LLM intent analysis result: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}")
                logger.warning(f"Response was: {response}")
                logger.warning(f"Cleaned response was: {cleaned_response}")
                return self._fallback_intent_analysis(query, conversation_history)
                
        except Exception as e:
            logger.error(f"Error analyzing grant intent: {e}")
            return self._fallback_intent_analysis(query, conversation_history)

    def _fallback_intent_analysis(self, query: str, conversation_history: List[dict]) -> dict:
        """
        Rule-based fallback when LLM analysis fails
        """
        logger.info(f"FALLBACK CALLED for query: '{query}'")
        query_lower = query.lower()
        logger.info(f"Query lower: '{query_lower}'")
        
        # Grant search keywords
        grant_keywords = [
            "grant", "grants", "funding", "fund", "award", "awards", "opportunity", 
            "opportunities", "rfa", "rfi", "rfp", "solicitation", "program", "find",
            "search", "show me", "help me find", "please help", "can you find", 
            "could you find", "available", "open", "deadline", "money", "financial",
            "support", "assistance", "sponsor", "sponsorship", "scholarship", "fellowship"
        ]
        
        # Broad query keywords
        broad_keywords = [
            "latest", "recent", "new", "current", "open", "available", "all",
            "any", "everything", "comprehensive", "overview"
        ]
        
        # Chat keywords
        chat_keywords = [
            "what is", "what", "how", "why", "explain", "tell me", "introduce", 
            "hello", "hi", "thank", "thanks", "help", "assist"
        ]
        
        has_grant_intent = any(keyword in query_lower for keyword in grant_keywords)
        has_broad_terms = any(keyword in query_lower for keyword in broad_keywords)
        has_chat_intent = any(keyword in query_lower for keyword in chat_keywords)
        
        # Check context: if previously discussing grants, now asking for "related grants"
        context_topic = self._extract_context_topic(conversation_history)
        
        if has_grant_intent:
            # Always search for grants if grant keywords are present
            search_query = self._extract_search_keywords_improved(query, context_topic)
            logger.info(f"Fallback: Grant intent detected, search_query: {search_query}")
            return {
                "intent": "search_grants",
                "refined_query": search_query,
                "answer": "I'll help you search for grants.",
                "search_criteria": {"keywords": [search_query]}
            }
        elif has_chat_intent:
            return {
                "intent": "chat",
                "answer": "I can help you search for grants or answer questions about funding opportunities. What would you like to know?",
                "suggestions": [
                    "Find grants in my field",
                    "What types of grants are available?",
                    "How do I apply for grants?",
                    "Show me recent grant opportunities"
                ]
            }
        else:
            return {
                "intent": "clarify",
                "clarification_question": "What would you like me to help you with?",
                "suggestions": [
                    "Find grants on this topic", 
                    "Explain grant opportunities to me", 
                    "What are the main funding areas available?"
                ]
            }

    def _extract_context_topic(self, conversation_history: List[dict]) -> str:
        """
        Extract topic keywords from conversation history
        """
        recent_content = ""
        for msg in conversation_history[-4:]:  # Recent 4 turns
            if msg.get('role') == 'user':
                recent_content += msg.get('content', '') + " "
        
        # Extract grant-related keywords
        grant_tech_keywords = [
            "research", "education", "healthcare", "technology", "science", 
            "engineering", "medicine", "biology", "chemistry", "physics",
            "computer science", "artificial intelligence", "machine learning",
            "data science", "cybersecurity", "renewable energy", "environment",
            "climate", "sustainability", "innovation", "startup", "small business",
            "nonprofit", "community", "social", "economic", "development"
        ]
        
        # Find matching keywords
        found_keywords = []
        for keyword in grant_tech_keywords:
            if keyword in recent_content.lower():
                found_keywords.append(keyword)
        
        return " ".join(found_keywords[:3])  # Return top 3 keywords

    def _extract_search_keywords_improved(self, query: str, context_topic: str = "") -> str:
        """
        Extract search keywords from query, enhanced with context
        """
        # Combine query with context
        if context_topic:
            enhanced_query = f"{query} {context_topic}"
        else:
            enhanced_query = query
            
        # Remove common stop words but keep important grant terms
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = enhanced_query.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return " ".join(keywords[:10])  # Limit to 10 keywords

    def _build_context(self, conversation_history: List[dict]) -> str:
        """Build context string from conversation history"""
        if not conversation_history:
            return "No previous conversation."
        
        context_parts = []
        for turn in conversation_history[-self.max_context_turns:]:
            role = turn.get("role", "")
            content = turn.get("content", "")
            if role and content:
                context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)

    async def _handle_grant_search(
        self, intent_result: Dict[str, Any], session_id: str, conversation_history: List[dict]
    ) -> Dict[str, Any]:
        """Handle grant search request"""
        try:
            refined_query = intent_result.get("refined_query", "")
            search_criteria = intent_result.get("search_criteria", {})
            
            # Try vector search first, fallback to keyword search if no results
            vector_results = await grant_vector_search_service.vector_search(refined_query, k=20)
            if vector_results:
                # Get grant details from database
                grant_ids = [grant_id for grant_id, _ in vector_results]
                grants = await self._get_grants_by_ids(grant_ids)
                if not grants:
                    # Fallback to simple keyword search if vector search returns no results
                    grants = await self._simple_keyword_search(refined_query)
            else:
                # Fallback to simple keyword search if vector search fails
                grants = await self._simple_keyword_search(refined_query)
            
            if not grants:
                return {
                    "action": "chat",
                    "message": "I couldn't find any grants matching your search. Try different keywords or be more specific about what you're looking for.",
                    "grants": [],
                    "count": 0
                }
            
            # Format grants for response
            formatted_grants = []
            for grant in grants:
                formatted_grants.append({
                    "grant_id": grant.grant_id,
                    "title": grant.title,
                    "agency": getattr(grant, "agency", None),
                    "synopsis": getattr(grant, "synopsis", None),
                    #"detail_url": getattr(grant, "detail_url", None),
                    "detail_url": f"https://simpler.grants.gov/opportunity/{grant.grant_id}",
                    "posted_date": grant.posted_date.isoformat() if getattr(grant, "posted_date", None) else None,
                    "close_date": grant.close_date.isoformat() if getattr(grant, "close_date", None) else None,
                    "status": getattr(grant, "status", None),
                })
            
            # Generate summary
            summary = await self._generate_grant_summary(formatted_grants, refined_query)
            
            return {
                "action": "results",
                "message": summary,
                "grants": formatted_grants,
                "count": len(formatted_grants),
                "refined_query": refined_query
            }
            
        except Exception as e:
            logger.error(f"Error handling grant search: {e}")
            return {
                "action": "chat",
                "message": "Sorry, I encountered an error while searching for grants. Please try again.",
                "grants": [],
                "count": 0
            }

    async def _simple_keyword_search(self, query: str) -> List:
        """Simple keyword-based search backed by the database"""
        try:
            grants = await grant_db_service.search_grants_by_keywords(query, limit=20)
            return grants
        except Exception as e:
            logger.error(f"Error in simple keyword search (db): {e}")
            return []

    async def _get_grants_by_ids(self, grant_ids: List[str]) -> List:
        """Get grant details from database by IDs"""
        try:
            return await grant_db_service.get_grants_by_ids(grant_ids)
        except Exception as e:
            logger.error(f"Error getting grants by IDs: {e}")
            return []

    async def _generate_grant_summary(self, grants: List[dict], query: str) -> str:
        """Generate summary of grant search results"""
        try:
            if not grants:
                return "No grants found matching your search."
            
            # Create summary prompt
            grants_text = "\n\n".join([
                f"Title: {g['title']}\nAgency: {g['agency']}\nDescription: {g['synopsis'][:200]}..."
                for g in grants[:5]  # Limit to first 5 for summary
            ])
            
            prompt = f"""
Based on the following grant search results for query "{query}", provide a helpful summary:

{grants_text}

Provide a concise summary (2-3 sentences) highlighting the most relevant grants and key information.
"""
            
            summary = await conv_llm_service.conversation(
                messages=[{"role": "user", "content": prompt}]
            )
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error generating grant summary: {e}")
            return f"Found {len(grants)} grants matching your search for '{query}'."

    def _handle_clarification(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle clarification requests"""
        return {
            "action": "clarification",
            "message": intent_result.get("answer", "Could you please provide more details about what you're looking for?"),
            "grants": [],
            "count": 0
        }


improved_grant_search_service = ImprovedGrantSearchService()
