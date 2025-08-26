import logging
import asyncio
from typing import Dict, Any, List, Optional
import json
from app.services.llm_service import llm_service
from app.services.db_service import db_service
from app.models.paper import PaperSearchRequest
from app.api.search import search_papers
from datetime import datetime

logger = logging.getLogger(__name__)

class ImprovedConversationalSearchService:
    """
    Improved conversational search service
    Focuses on two core functions:
    1. Intent recognition: chat vs get papers
    2. Context understanding: extract and refine queries from conversation history
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
            
            # Record to search history
            await db_service.add_search_history(
                session_id=session_id,
                user_id=user_id,
                query=query,
                timestamp=datetime.now()
            )

            # Analyze user intent
            intent_result = await self._analyze_intent_with_context(
                query, conversation_history
            )

            if intent_result["intent"] == "get_papers":
                # User wants to get papers
                return await self._handle_paper_request(
                    intent_result, session_id, conversation_history
                )
            elif intent_result["intent"] == "clarify":
                # Need clarification
                return self._handle_clarification(intent_result)
            else:
                # General chat
                return await self._handle_chat(query, conversation_history)

        except Exception as e:
            logger.error(f"Error in conversational search: {e}")
            return {
                "action": "chat",
                "message": "Sorry, I encountered some technical issues. Please describe your needs again.",
                "papers": [],
                "count": 0,
                "suggestions": []
            }

    async def _analyze_intent_with_context(
        self, 
        query: str, 
        conversation_history: List[dict]
    ) -> dict:
        """
        Use LLM to analyze user intent, considering context
        """
        try:
            # Build conversation context
            context_text = ""
            for msg in conversation_history[-self.max_context_turns:]:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                context_text += f"{role}: {content}\n"

            # Build analysis prompt
            prompt = f"""
You are an intent analyzer for an academic paper search assistant. Analyze user's query intent, with only three possibilities:

1. **get_papers**: User wants to get/search/find papers
2. **clarify**: Query is too broad, needs clarification of specific requirements
3. **chat**: General chat, greetings, concept explanations, etc.

Conversation history:
{context_text}

Current user input: {query}

Analysis rules:
- If user explicitly mentions "find papers", "search", "papers", "research", "literature", etc., and query is specific enough → get_papers
- If user mentions getting papers but query is too broad (like "latest developments", "review") → clarify  
- If it's greetings, concept explanations, general questions → chat
- Consider conversation context: if previously discussing a topic and now says "find related papers" → get_papers

Return JSON format:

For get_papers:
{{
    "intent": "get_papers",
    "refined_query": "extracted specific search terms",
    "reasoning": "analysis reason"
}}

For clarify:
{{
    "intent": "clarify", 
    "clarification_question": "specific clarification question",
    "suggestions": ["suggestion1", "suggestion2", "suggestion3"],
    "reasoning": "reason for needing clarification"
}}

For chat:
{{
    "intent": "chat",
    "reasoning": "reason for judging as general chat"
}}

Examples:
- "find some papers about transformer" → get_papers (refined_query: "transformer")
- "latest machine learning developments" → clarify (too broad)
- "what is deep learning?" → chat (concept explanation)
- Context discussing BERT, user says "find related papers" → get_papers (combining context)

Return only JSON, no other content.
"""

            response = await llm_service.conversation(
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            try:
                analysis = json.loads(response)
                logger.info(f"Intent analysis: {analysis}")
                return analysis
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse intent analysis JSON: {response}")
                return self._fallback_intent_analysis(query, conversation_history)

        except Exception as e:
            logger.error(f"Error in intent analysis: {e}")
            return self._fallback_intent_analysis(query, conversation_history)

    def _fallback_intent_analysis(self, query: str, conversation_history: List[dict]) -> dict:
        """
        Rule-based fallback when LLM analysis fails
        """
        query_lower = query.lower()
        
        # Clear paper search keywords
        paper_keywords = [
            "paper", "papers", "literature", "research", "study", "find", "search",
            "article", "publication", "related research"
        ]
        
        # Broad query keywords
        broad_keywords = [
            "latest", "recent", "new developments", "developments", "trends", "review",
            "overview", "comprehensive", "all"
        ]
        
        # Chat keywords
        chat_keywords = [
            "what is", "what", "how", "why", "explain", "tell me", "introduce", 
            "hello", "hi", "thank", "thanks"
        ]
        
        has_paper_intent = any(keyword in query_lower for keyword in paper_keywords)
        has_broad_terms = any(keyword in query_lower for keyword in broad_keywords)
        has_chat_intent = any(keyword in query_lower for keyword in chat_keywords)
        
        # Check context: if previously discussing technical topics, now asking for "related papers"
        context_topic = self._extract_context_topic(conversation_history)
        
        if has_paper_intent:
            if has_broad_terms and not context_topic:
                # Too broad and no context
                return {
                    "intent": "clarify",
                    "clarification_question": f"Your query '{query}' is quite broad. Could you specify which aspect you want to learn about?",
                    "suggestions": [
                        "Search for specific algorithms or methods",
                        "Find papers in particular application domains",
                        "Show me theoretical research papers",
                        "Find practical application papers"
                    ]
                }
            else:
                # Has clear intent or context support
                search_query = self._extract_search_keywords(query, context_topic)
                return {
                    "intent": "get_papers",
                    "refined_query": search_query,
                    "reasoning": "User explicitly requests to get papers"
                }
        elif has_chat_intent or not has_paper_intent:
            return {
                "intent": "chat",
                "reasoning": "Judged as general chat or concept explanation"
            }
        else:
            return {
                "intent": "clarify",
                "clarification_question": "What would you like me to help you with?",
                "suggestions": [
                    "Find papers on this topic", 
                    "Explain the concept to me", 
                    "What are the main research areas in this field?"
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
        
        # Extract technical keywords
        tech_keywords = [
            "transformer", "bert", "gpt", "lstm", "cnn", "gan", "vae",
            "machine learning", "deep learning", "neural network", 
            "computer vision", "nlp", "natural language"
        ]
        
        content_lower = recent_content.lower()
        for keyword in tech_keywords:
            if keyword in content_lower:
                return keyword
        
        return ""

    def _extract_search_keywords(self, query: str, context_topic: str = "") -> str:
        """
        Extract search keywords
        """
        # Remove stop words
        stop_words = [
            "find", "search", "papers", "about", "on", "for", "i", "want", "to",
            "the", "a", "an", "is", "are", "some", "get", "show", "me"
        ]
        
        words = query.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # If there's context topic, use it first
        if context_topic:
            keywords = [context_topic] + keywords
        
        return " ".join(keywords[:4])  # Maximum 4 keywords

    async def _handle_paper_request(
        self,
        intent_result: dict,
        session_id: str, 
        conversation_history: List[dict]
    ) -> dict:
        """
        Handle paper search requests, directly call search.py API
        """
        try:
            refined_query = intent_result["refined_query"]
            logger.info(f"Searching papers with refined query: {refined_query}")
            
            # Create search request object
            search_request = PaperSearchRequest(query=refined_query)
            
            # Directly call search_papers function from search.py
            search_response = await search_papers(search_request)
            
            # Format paper results
            papers = []
            for paper in search_response.results:
                papers.append({
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "categories": paper.categories,
                    "pdf_url": paper.pdf_url,
                    "published_date": paper.published_date,
                    "updated_date": paper.updated_date,
                    "platform": paper.platform
                })
            
            return {
                "action": "results",
                "message": f"Based on your request, I found {len(papers)} related papers:",
                "papers": papers,
                "count": len(papers),
                "refined_query": refined_query,
                "suggestions": [
                    f"Find more papers about {refined_query}",
                    "What are the latest developments in this field?",
                    "Show me review papers on this topic"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error handling paper request: {e}")
            return {
                "action": "error",
                "message": "Encountered an error while searching papers, please describe your needs again.",
                "papers": [],
                "count": 0,
                "suggestions": []
            }

    def _handle_clarification(self, intent_result: dict) -> dict:
        """
        Handle clarification requests
        """
        return {
            "action": "clarification",
            "message": intent_result["clarification_question"],
            "papers": [],
            "count": 0,
            "suggestions": intent_result.get("suggestions", [])
        }

    async def _handle_chat(self, query: str, conversation_history: List[dict]) -> dict:
        """
        Handle general chat
        """
        try:
            # Build conversation context
            messages = []
            
            # System prompt
            messages.append({
                "role": "system",
                "content": "You are a friendly academic research assistant. You can explain research concepts, discuss academic topics, and answer general questions. If users want to search for specific papers, you can suggest they clarify their search needs. Keep the conversation natural and friendly."
            })
            
            # Add conversation history
            for msg in conversation_history[-6:]:  # Recent 6 turns
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content")
                })
            
            # Current query
            messages.append({
                "role": "user",
                "content": query
            })
            
            # Call LLM
            response = await llm_service.conversation(messages=messages)
            
            return {
                "action": "chat",
                "message": response,
                "papers": [],
                "count": 0,
                "suggestions": [
                    "Find papers on this topic",
                    "Tell me more about recent advances",
                    "What are the main challenges in this area?"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in chat handling: {e}")
            return {
                "action": "chat",
                "message": "I'd be happy to chat with you! What would you like to know?",
                "papers": [],
                "count": 0,
                "suggestions": [
                    "Explain a research concept to me",
                    "Find papers on a specific topic",
                    "What are the current trends in machine learning?"
                ]
            }

# Create service instance
improved_conversational_search_service = ImprovedConversationalSearchService()
