import logging
from typing import Dict, Any, List, Optional
import json
from app.services.conv_llm_service import conv_llm_service
from app.services.conv_db_service import conv_db_service
from app.services.pdf_service import pdf_service
from app.models.paper import ConvPaperSearchRequest
from app.api.conv_search import conv_search_papers
from app.services.prompt import PROMPT
from datetime import datetime

logger = logging.getLogger(__name__)

class ConversationalSearchService:
    """
    Conversational search service
    Handles complex conversational queries and context understanding
    """

    def __init__(self):
        self.max_context_turns = 8  # Keep recent 8 conversation turns
        self.session_contexts = {}  # Store session contexts

    async def process_conversation(
        self,
        user_id: str,
        session_id: str,
        query: str,
        conversation_history: List[dict] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing conversations
        """
        try:
            conversation_history = conversation_history or []
            
            # Debug: Log the received conversation history
            logger.info(f"Received conversation history: {conversation_history}")

            # Record to search history
            await conv_db_service.add_search_history(
                session_id=session_id,
                user_id=user_id,
                query=query,
                timestamp=datetime.now()
            )
            
            # Step 1: Intent Recognition
            intent = await self._recognize_intent(query, conversation_history)
            
            if intent == "chat":
                # Handle conversational chat
                return await self._handle_chat(query, conversation_history)
            elif intent == "get_papers":
                # Handle paper search with context
                return await self._handle_paper_search(query, conversation_history)
            else:
                # Default to paper search
                return await self._handle_paper_search(query, conversation_history)
                
        except Exception as e:
            logger.error(f"Error processing conversation: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"Error processing your request: {str(e)}",
                "suggestions": [
                    "Try rephrasing your question",
                    "Ask for papers about a specific topic",
                    "Request help with your research"
                ]
            }

    async def _recognize_intent(self, query: str, history: List[dict]) -> str:
        """
        Recognize user intent: chat vs get papers
        """
        try:
            # Simple keyword-based intent recognition
            # You can make this more sophisticated with ML models
            
            chat_keywords = [
                "hello", "hi", "help", "what", "how", "explain", "tell me",
                "can you", "could you", "would you", "please", "thank you"
            ]
            
            paper_keywords = [
                "papers", "research", "find", "search", "show me", "get me",
                "about", "on", "related to", "similar to", "like"
            ]
            
            query_lower = query.lower()
            
            # Count keyword matches
            chat_score = sum(1 for keyword in chat_keywords if keyword in query_lower)
            paper_score = sum(1 for keyword in paper_keywords if keyword in query_lower)
            
            # If no clear intent, check conversation history
            if chat_score == 0 and paper_score == 0:
                if history:
                    # If there's history, likely continuing a conversation
                    return "chat"
                else:
                    # First interaction, default to paper search
                    return "get_papers"
            
            # Return intent with higher score
            return "chat" if chat_score > paper_score else "get_papers"
            
        except Exception as e:
            logger.error(f"Error recognizing intent: {e}")
            return "get_papers"  # Default to paper search

    async def _handle_chat(self, query: str, history: List[dict]) -> Dict[str, Any]:
        """
        Handle conversational chat
        """
        try:
            # Build context from conversation history
            context = self._build_context(history)
            
            # Generate response using LLM
            messages = [
                {"role": "system", "content": PROMPT.CONVERSATIONAL_ASSISTANT},
                {"role": "user", "content": f"Context: {context}\n\nUser: {query}"}
            ]
            
            response = await conv_llm_service.conversation(messages)
            
            return {
                "type": "chat",
                "message": response,
                "suggestions": [
                    "Find papers about machine learning",
                    "Show me recent research on AI",
                    "Search for papers by specific authors"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error handling chat: {e}")
            return {
                "type": "error",
                "message": "I'm having trouble understanding your request. Could you try rephrasing it?",
                "suggestions": [
                    "Ask for papers about a specific topic",
                    "Request help with your research",
                    "Try a different question"
                ]
            }

    async def _handle_paper_search(self, query: str, history: List[dict]) -> Dict[str, Any]:
        """
        Handle paper search with conversation context
        """
        try:
            # Build context from conversation history
            context = self._build_context(history)
            
            # Enhance query with context
            enhanced_query = await self._enhance_query_with_context(query, context)
            
            # Parse query for metadata extraction
            llm_output = await self._parse_query_for_metadata(enhanced_query)
            
            # Perform search (don't use limit here - we want to search for more papers
            # and filter after reranking in improved_conversational_search_service.py)
            search_request = ConvPaperSearchRequest(
                llm_output=llm_output,
                include_summary=False
            )
            
            search_results = await conv_search_papers(search_request)
            
            # Generate contextual suggestions
            suggestions = await self._generate_contextual_suggestions(
                query, search_results.results, context
            )
            
            return {
                "type": "papers",
                "results": search_results.results,
                "count": search_results.count,
                "query": enhanced_query,
                "suggestions": suggestions,
                "metadata": llm_output
            }
            
        except Exception as e:
            logger.error(f"Error handling paper search: {e}")
            return {
                "type": "error",
                "message": "I couldn't find papers for your request. Try rephrasing your search.",
                "suggestions": [
                    "Try different keywords",
                    "Be more specific about your topic",
                    "Ask for papers from a specific time period"
                ]
            }

    def _build_context(self, history: List[dict]) -> str:
        """
        Build context string from conversation history
        """
        if not history:
            return "No previous conversation context."
        
        # Take last few turns for context
        recent_history = history[-self.max_context_turns:] if len(history) > self.max_context_turns else history
        
        context_parts = []
        for turn in recent_history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            context_parts.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(context_parts)

    async def _enhance_query_with_context(self, query: str, context: str) -> str:
        """
        Enhance search query with conversation context
        """
        try:
            if not context or context == "No previous conversation context.":
                return query
            
            enhanced_query = await conv_llm_service.enhance_search_query(query, context)
            return enhanced_query if enhanced_query else query
            
        except Exception as e:
            logger.error(f"Error enhancing query: {e}")
            return query

    async def _parse_query_for_metadata(self, query: str) -> Dict[str, Any]:
        """
        Parse query to extract metadata (authors, dates, platforms, etc.)
        """
        try:
            # Use LLM to parse query and extract structured information
            prompt = f"""
            Parse this search query and extract structured information:
            Query: "{query}"
            
            Extract:
            1. Refined search query (clean, searchable terms)
            2. Authors mentioned (if any)
            3. Date ranges mentioned (if any)
            4. Platforms mentioned (if any)
            5. Author logic (AND/OR for multiple authors)
            
            Return JSON format:
            {{
                "refined_query": "clean search terms",
                "fields": {{
                    "authors": ["author1", "author2"],
                    "date": ["2023", "recent"],
                    "platform": ["arxiv", "ieee"],
                    "author_logic": "AND"
                }}
            }}
            """
            
            response = await conv_llm_service.conversation([
                {"role": "user", "content": prompt}
            ])
            
            # Try to parse JSON response
            try:
                import json
                parsed = json.loads(response)
                return parsed
            except json.JSONDecodeError:
                # Fallback to simple structure
                return {
                    "refined_query": query,
                    "fields": {
                        "authors": [],
                        "date": [],
                        "platform": [],
                        "author_logic": "AND"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error parsing query metadata: {e}")
            return {
                "refined_query": query,
                "fields": {
                    "authors": [],
                    "date": [],
                    "platform": [],
                    "author_logic": "AND"
                }
            }

    async def _generate_contextual_suggestions(
        self, 
        query: str, 
        results: List[Dict], 
        context: str
    ) -> List[str]:
        """
        Generate contextual follow-up suggestions
        """
        try:
            suggestions = await conv_llm_service.generate_search_suggestions(
                query, results, context
            )
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return [
                "Find more papers on this topic",
                "Show me recent papers",
                "Search for related research",
                "Find papers by specific authors"
            ]

# Create global instance
conversational_search_service = ConversationalSearchService()
