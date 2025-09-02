import logging
import asyncio
from typing import Dict, Any, List, Optional
import json
from app.services.llm_service import llm_service
from app.services.db_service import db_service
from app.services.pdf_service import pdf_service
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
            
            # Debug: Log the received conversation history
            logger.info(f"Received conversation history: {conversation_history}")
            logger.info(f"Conversation history type: {type(conversation_history)}")
            logger.info(f"Conversation history length: {len(conversation_history)}")
            
            # Record to search history
            await db_service.add_search_history(
                session_id=session_id,
                user_id=user_id,
                query=query,
                timestamp=datetime.now()
            )

            # First, check if this should be treated as "paper analysis" intent
            # This is NOT determined by LLM, but by checking if:
            # 1. Previous round returned papers
            # 2. User selected some of those papers
            logger.info(f"Starting paper analysis intent check for query: '{query}'")
            selected_papers = self._check_paper_analysis_intent(conversation_history)
            
            if selected_papers:
                # This is "paper analysis" intent - user is asking about selected papers
                logger.info(f"Paper analysis intent detected: {len(selected_papers)} selected papers from previous round")
                return await self._handle_paper_analysis_intent(
                    query, selected_papers, session_id, conversation_history
                )
            else:
                # Not paper analysis intent, proceed with normal LLM-based intent analysis
                # This will determine if it's: chat, get_papers, or clarify
                logger.info("No paper analysis intent detected, proceeding with LLM intent analysis")
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
- **IMPORTANT**: Consider conversation context carefully. If user says "this topic", "related papers", "papers on this", etc., extract the main topic from the conversation history
- When extracting search terms, combine context with current query intelligently

**CRITICAL**: You must respond with ONLY valid JSON. No explanations, no markdown formatting, no additional text.

Return exactly one of these JSON formats:

For get_papers:
{{
    "intent": "get_papers",
    "refined_query": "extracted specific search terms (combine context + current query)",
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
- "find some papers about transformer" → {{"intent": "get_papers", "refined_query": "transformer", "reasoning": "User explicitly requests papers about transformer"}}
- "latest machine learning developments" → {{"intent": "clarify", "clarification_question": "Your query is quite broad. Could you specify which aspect of machine learning you want to learn about?", "suggestions": ["Search for specific algorithms", "Find papers in particular domains", "Show me theoretical research"], "reasoning": "Query too broad without specific focus"}}
- "what is deep learning?" → {{"intent": "chat", "reasoning": "User asks for concept explanation"}}
- Context: "what is random walk?" → "show me papers on this topic" → {{"intent": "get_papers", "refined_query": "random walk", "reasoning": "User refers to previously discussed topic"}}
- Context: discussing BERT → "find related papers" → {{"intent": "get_papers", "refined_query": "BERT", "reasoning": "User requests papers related to context topic"}}

**IMPORTANT INSTRUCTIONS**:
1. Return ONLY the JSON object, no other text
2. Do not use markdown formatting (no ```json or ```)
3. Ensure all strings are properly quoted
4. When user refers to "this topic", extract the main subject from conversation history
5. For get_papers, refined_query should be the actual search terms, not the full user query
"""

            response = await llm_service.conversation(
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response - simplified with better prompt
            try:
                # Clean response - remove any potential markdown formatting
                import re
                cleaned_response = re.sub(r'```json\s*', '', response)
                cleaned_response = re.sub(r'```\s*', '', cleaned_response)
                cleaned_response = cleaned_response.strip()
                
                # Try to parse JSON
                analysis = json.loads(cleaned_response)
                logger.info(f"Intent analysis: {analysis}")
                return analysis
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}")
                logger.warning(f"Response was: {response}")
                logger.warning(f"Cleaned response was: {cleaned_response}")
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
            "article", "publication", "related research", "show me", "this topic",
            "help me find", "please help", "can you find", "could you find"
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
                search_query = self._extract_search_keywords_improved(query, context_topic)
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
        
        # Extract technical keywords - expanded list
        tech_keywords = [
            "transformer", "bert", "gpt", "lstm", "cnn", "gan", "vae",
            "machine learning", "deep learning", "neural network", 
            "computer vision", "nlp", "natural language", "random walk",
            "attention", "reinforcement learning", "federated learning",
            "graph neural network", "graph neural networks", "gnn",
            "convolutional", "recurrent", "autoencoder", "variational",
            "bayesian", "optimization", "gradient", "backpropagation",
            "clustering", "classification", "regression", "supervised",
            "unsupervised", "semi-supervised", "transfer learning",
            "meta learning", "few shot", "zero shot", "multimodal",
            "vision transformer", "swin transformer", "efficientnet",
            "resnet", "vgg", "alexnet", "inception", "mobilenet",
            "yolo", "faster r-cnn", "mask r-cnn", "detr", "vit",
            "word2vec", "glove", "fasttext", "elmo", "ulmfit",
            "roberta", "albert", "distilbert", "xlnet", "t5", "bart",
            "gpt-2", "gpt-3", "gpt-4", "chatgpt", "llama", "palm",
            "stable diffusion", "dall-e", "midjourney", "clip",
            "contrastive learning", "self-supervised", "pre-training",
            "fine-tuning", "prompt engineering", "chain of thought",
            "retrieval augmented generation", "rag", "vector database",
            "embedding", "similarity", "cosine", "euclidean", "manhattan"
        ]
        
        content_lower = recent_content.lower()
        for keyword in tech_keywords:
            if keyword in content_lower:
                return keyword
        
        # If no specific keyword found, try to extract any meaningful phrase
        # Look for patterns like "what is X" or "explain X"
        import re
        patterns = [
            r'what is ([a-zA-Z\s]+?)\?',
            r'explain ([a-zA-Z\s]+?)\?',
            r'tell me about ([a-zA-Z\s]+?)\?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content_lower)
            if match:
                topic = match.group(1).strip()
                if len(topic) > 2:  # Avoid very short topics
                    return topic
        
        return ""

    def _extract_search_keywords_improved(self, query: str, context_topic: str = "") -> str:
        """
        Improved search keyword extraction with better pattern matching
        """
        # Remove common polite phrases and stop words
        polite_phrases = [
            "would you please", "please help me", "can you help me", "could you help me",
            "i would like", "i want", "i need", "help me find", "please find",
            "show me", "get me", "find me"
        ]
        
        stop_words = [
            "find", "search", "papers", "about", "on", "for", "i", "want", "to",
            "the", "a", "an", "is", "are", "some", "get", "show", "me", "this",
            "topic", "related", "related to", "concerning", "regarding", "please",
            "help", "can", "could", "would", "like", "need"
        ]
        
        # Clean the query
        cleaned_query = query.lower()
        for phrase in polite_phrases:
            cleaned_query = cleaned_query.replace(phrase, "")
        
        # Remove stop words
        words = cleaned_query.split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # If there's context topic, use it first
        if context_topic:
            keywords = [context_topic] + keywords
        
        # If no keywords found, try to extract from the original query
        if not keywords:
            # Look for patterns like "about X" or "on X"
            import re
            patterns = [
                r'about ([a-zA-Z\s]+?)(?:\?|$|\.)',
                r'on ([a-zA-Z\s]+?)(?:\?|$|\.)',
                r'for ([a-zA-Z\s]+?)(?:\?|$|\.)',
                r'regarding ([a-zA-Z\s]+?)(?:\?|$|\.)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, query.lower())
                if match:
                    topic = match.group(1).strip()
                    # Clean the topic
                    topic_words = [word for word in topic.split() if word not in stop_words and len(word) > 2]
                    if topic_words:
                        keywords = topic_words
                        break
        
        return " ".join(keywords[:4])  # Maximum 4 keywords

    def _check_paper_analysis_intent(self, conversation_history: List[dict]) -> List[dict]:
        """
        Check if current query should be treated as "paper analysis" intent
        This is determined by two conditions:
        1. Previous round returned papers
        2. User selected some of those papers
        
        Returns list of selected papers if conditions are met, empty list otherwise
        """
        try:
            logger.info(f"Checking paper analysis intent. Conversation history length: {len(conversation_history)}")
            
            # Look for the most recent conversation that returned papers
            for i, conv in enumerate(reversed(conversation_history)):
                logger.info(f"Checking conversation {i}: role={conv.get('role')}, content={conv.get('content')}, has_papers={conv.get('papers') is not None}")
                logger.info(f"Conversation {i} full data: {conv}")
                
                # Check if this is a papers_returned message
                if conv.get("role") == "assistant" and conv.get("content") == "papers_returned" and conv.get("papers"):
                    papers = conv.get("papers", [])
                    logger.info(f"Found papers_returned message with {len(papers)} papers")
                    logger.info(f"Papers data: {papers}")
                    
                    # Check if any papers are selected
                    selected_papers = [p for p in papers if p.get("selected", False)]
                    logger.info(f"Selected papers: {len(selected_papers)}")
                    logger.info(f"Selected papers details: {selected_papers}")
                    
                    if selected_papers:
                        logger.info(f"Paper analysis intent detected: {len(selected_papers)} selected papers from previous round")
                        return selected_papers
                    else:
                        logger.info("No papers are selected in this conversation")
                else:
                    logger.info(f"Conversation {i} is not a papers_returned message")
            
            logger.info("No paper analysis intent detected - no selected papers found")
            return []
        except Exception as e:
            logger.error(f"Error checking paper analysis intent: {e}")
            return []

    async def _handle_paper_analysis_intent(
        self,
        query: str,
        selected_papers: List[dict],
        session_id: str,
        conversation_history: List[dict]
    ) -> Dict[str, Any]:
        """
        Handle "paper analysis" intent - user is asking about selected papers
        Uses pdf_service to get full text content from local PDF files
        """
        try:
            logger.info(f"Handling question about {len(selected_papers)} selected papers: {query}")
            
            # Get full text content from selected papers using pdf_service
            papers_content = []
            for paper in selected_papers:
                try:
                    logger.info(f"Getting content for paper: {paper['paper_id']} (platform: {paper.get('platform', 'arxiv')})")
                    
                    # Get PDF file path using pdf_service
                    pdf_path = await pdf_service.get_pdf(paper["paper_id"], paper.get("platform", "arxiv"))
                    if pdf_path:
                        logger.info(f"PDF path obtained: {pdf_path}")
                        
                        # Extract text from PDF using pdf_service
                        text_content = await pdf_service.extract_text_from_pdf(pdf_path)
                        if text_content:
                            logger.info(f"Text extracted, length: {len(text_content)} characters")
                            
                            # Limit text content to avoid token limits (keep first 6000 characters for better analysis)
                            if len(text_content) > 6000:
                                text_content = text_content[:6000] + "..."
                                logger.info(f"Text truncated to 6000 characters")
                            
                            papers_content.append({
                                "title": paper["title"],
                                "authors": paper["authors"],
                                "paper_id": paper["paper_id"],
                                "platform": paper.get("platform", "arxiv"),
                                "content": text_content
                            })
                        else:
                            logger.warning(f"No text content extracted from PDF for paper {paper['paper_id']}")
                    else:
                        logger.warning(f"No PDF path returned for paper {paper['paper_id']}")
                        
                except Exception as e:
                    logger.error(f"Failed to get content for paper {paper['paper_id']}: {e}")
                    continue
            
            if not papers_content:
                logger.warning("No papers content could be extracted")
                return {
                    "action": "error",
                    "message": "Unable to access the selected papers. Please try again.",
                    "papers": [],
                    "count": 0,
                    "suggestions": ["Try selecting different papers", "Ask a general question instead"]
                }
            
            logger.info(f"Successfully extracted content from {len(papers_content)} papers")
            
            # Create analysis prompt for multiple papers
            papers_summary = "\n\n".join([
                f"Paper ID: {p['paper_id']}\nTitle: {p['title']}\nAuthors: {p['authors']}\nPlatform: {p['platform']}\n\nContent:\n{p['content']}"
                for p in papers_content
            ])
            
            analysis_prompt = f"""
You are an expert academic researcher. The user has selected {len(selected_papers)} papers and is asking a question about them.

User's Question: {query}

Selected Papers:
{papers_summary}

Please provide a comprehensive answer to the user's question based on the content of these selected papers. Your response should:

1. Directly address the user's question
2. Reference specific content from the selected papers (mention paper titles when relevant)
3. Provide insights and connections between the papers if relevant
4. Be clear, academic, and helpful
5. If the user asks for a summary, provide a structured summary of the key points

Focus on answering the user's specific question using the information available in these papers.
"""

            logger.info("Sending analysis prompt to LLM")
            
            # Get LLM response
            response = await llm_service.conversation(
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            logger.info(f"LLM response received, length: {len(response)} characters")
            
            return {
                "action": "chat",
                "message": response,
                "papers": selected_papers,
                "count": len(selected_papers),
                "suggestions": [
                    "Ask another question about these papers",
                    "Select different papers to analyze",
                    "Search for new papers on a topic"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error handling selected papers question: {e}")
            return {
                "action": "error",
                "message": "Sorry, I encountered an error while analyzing the selected papers. Please try again.",
                "papers": [],
                "count": 0,
                "suggestions": ["Try selecting different papers", "Ask a general question instead"]
            }

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
                "message": "Based on your request, I found these related papers:",
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
        Handle general chat with improved context awareness
        """
        try:
            # Build conversation context
            messages = []
            
            # Extract recent context for better suggestions
            recent_context = ""
            for msg in conversation_history[-4:]:
                if msg.get('role') == 'user':
                    recent_context += msg.get('content', '') + " "
            
            # System prompt with context awareness
            system_prompt = """You are a friendly academic research assistant. You can explain research concepts, discuss academic topics, and answer general questions. 

When explaining concepts, be clear and concise. If users ask about a specific topic, you can suggest they search for related papers to learn more.

Keep the conversation natural and friendly. If the user has been discussing a specific topic, acknowledge that context in your response."""
            
            messages.append({
                "role": "system",
                "content": system_prompt
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
            
            # Generate context-aware suggestions
            suggestions = self._generate_context_aware_suggestions(recent_context, query)
            
            return {
                "action": "chat",
                "message": response,
                "papers": [],
                "count": 0,
                "suggestions": suggestions
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

    def _generate_context_aware_suggestions(self, recent_context: str, current_query: str) -> List[str]:
        """
        Generate context-aware suggestions based on conversation history
        """
        context_lower = recent_context.lower()
        query_lower = current_query.lower()
        
        # Extract potential topics from context
        topics = []
        
        # Look for technical terms in context
        tech_terms = [
            "random walk", "transformer", "bert", "gpt", "lstm", "cnn", "gan", "vae",
            "machine learning", "deep learning", "neural network", "attention",
            "reinforcement learning", "federated learning", "graph neural network"
        ]
        
        for term in tech_terms:
            if term in context_lower:
                topics.append(term)
                break  # Use the first found topic
        
        # If no specific topic found, look for patterns
        if not topics:
            import re
            patterns = [
                r'what is ([a-zA-Z\s]+?)\?',
                r'explain ([a-zA-Z\s]+?)\?',
                r'tell me about ([a-zA-Z\s]+?)\?'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, context_lower)
                if match:
                    topic = match.group(1).strip()
                    if len(topic) > 2:
                        topics.append(topic)
                        break
        
        # Generate suggestions based on context
        if topics:
            topic = topics[0]
            return [
                f"Find papers about {topic}",
                f"What are the latest developments in {topic}?",
                f"Show me review papers on {topic}",
                "Explain another research concept to me"
            ]
        else:
            # Default suggestions
            return [
                "Find papers on a specific topic",
                "Explain a research concept to me",
                "What are the current trends in machine learning?",
                "Show me recent papers in computer vision"
            ]

    async def analyze_paper(
        self,
        user_id: str,
        paper_id: str,
        platform: str = "arxiv"
    ) -> Dict[str, Any]:
        """
        Analyze a paper by extracting its full text and using LLM to provide insights
        """
        try:
            logger.info(f"Starting paper analysis for {paper_id} (platform: {platform})")
            
            # Get paper details from database
            paper_details = await db_service.get_paper_by_id(paper_id, platform)
            if not paper_details:
                return {
                    "analysis": "",
                    "success": False,
                    "error_message": "Paper not found in database"
                }
            
            # Get PDF file path
            pdf_path = await pdf_service.get_pdf(paper_id, platform)
            if not pdf_path:
                return {
                    "analysis": "",
                    "success": False,
                    "error_message": "PDF file not available"
                }
            
            # Extract text from PDF
            text_content = await pdf_service.extract_text_from_pdf(pdf_path)
            if not text_content:
                return {
                    "analysis": "",
                    "success": False,
                    "error_message": "Failed to extract text from PDF"
                }
            
            # Limit text content to avoid token limits (keep first 8000 characters)
            if len(text_content) > 8000:
                text_content = text_content[:8000] + "..."
            
            # Create analysis prompt
            analysis_prompt = f"""
You are an expert academic paper analyst. Please provide a comprehensive analysis of the following research paper.

Paper Title: {paper_details.title}
Authors: {paper_details.authors}
Platform: {platform}

Paper Content:
{text_content}

Please provide a structured analysis including:
1. **Main Research Question/Objective**: What is the primary research question or objective?
2. **Key Contributions**: What are the main contributions of this paper?
3. **Methodology**: What methods or approaches are used?
4. **Key Findings**: What are the main results or findings?
5. **Significance**: Why is this research important?
6. **Limitations**: What are the potential limitations or areas for improvement?

Please be concise but comprehensive. Focus on the most important aspects and provide clear, academic-level insights.
"""

            # Get LLM analysis
            response = await llm_service.conversation(
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            return {
                "analysis": response,
                "success": True,
                "error_message": None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing paper {paper_id}: {e}")
            return {
                "analysis": "",
                "success": False,
                "error_message": f"Analysis failed: {str(e)}"
            }

# Create service instance
improved_conversational_search_service = ImprovedConversationalSearchService()
