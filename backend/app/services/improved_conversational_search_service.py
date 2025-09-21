import logging
import asyncio
from typing import Dict, Any, List, Optional
import json

from app.services.pdf_service import pdf_service
from app.models.paper import ConvPaperSearchRequest 
from app.services.conv_db_service import conv_db_service
from app.services.conv_vector_search_service import conv_vector_search_service
from app.services.conv_keyword_search_service import conv_keyword_search_service
from app.services.conv_llm_service import conv_llm_service
from app.services.metadata_filter_service import filter_papers_by_metadata
from app.services.prompt import PROMPT
from app.services.full_paper_service import analyze_full_papers
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
            await conv_db_service.add_search_history(
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
                logger.info(f"DEBUG: full_paper_analysis in intent_result: {intent_result.get('full_paper_analysis')} (type: {type(intent_result.get('full_paper_analysis'))})")
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

                    return {
                    "action": "chat",
                    "message": intent_result["answer"],
                    "papers": [],
                    "count": 0            }

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

            logger.info(f"Conversation history for intent analysis: {conversation_history}")
            for msg in conversation_history[-self.max_context_turns:]:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                context_text += f"{role}: {content}\n"

            # Build analysis prompt via prompt module constant (avoid .format clashing with JSON braces)
            prompt = PROMPT.replace("{context_text}", context_text).replace("{query}", query).replace("{today_date}", datetime.now().strftime("%Y-%m-%d"))

            response = await conv_llm_service.conversation(
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
                return analysis
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}")
                logger.warning(f"Response was: {response}")
                logger.warning(f"Cleaned response was: {cleaned_response}")
                # return self._fallback_intent_analysis(query, conversation_history)

        except Exception as e:
            logger.error(f"Error in intent analysis: {e}")
            # return self._fallback_intent_analysis(query, conversation_history)

    def _fallback_intent_analysis(self, query: str, conversation_history: List[dict]) -> dict:
        """
        Rule-based fallback when LLM analysis fails
        """
        logger.info("Using fallback intent analysis")
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


    def _should_perform_full_paper_analysis(self, papers: List[Dict], intent_result: Dict) -> bool:
        """
        Determine if full paper analysis should be performed.
        
        Args:
            papers: List of final papers
            intent_result: The intent analysis result
            
        Returns:
            True if full paper analysis should be performed
        """
        try:
            # Check if we have papers to analyze
            if not papers or len(papers) == 0:
                return False
            
            # Check if papers have PDF URLs
            papers_with_pdfs = [p for p in papers if p.get("pdf_url")]
            if len(papers_with_pdfs) == 0:
                logger.info("No papers with PDF URLs found, skipping full paper analysis")
                return False
            
            # PRIORITY 1: If this is a comparison query, always perform full paper analysis
            comparison = intent_result.get("comparison", {})
            is_comparison = comparison.get("value", "False") == "True"
            if is_comparison:
                logger.info(f"COMPARISON QUERY DETECTED: Always performing full paper analysis for {len(papers_with_pdfs)} papers with PDFs")
                return True
            
            # PRIORITY 2: Check if LLM explicitly requested full paper analysis
            full_paper_analysis = intent_result.get("full_paper_analysis", "False")
            logger.info(f"DEBUG: full_paper_analysis value: {full_paper_analysis} (type: {type(full_paper_analysis)})")
            if full_paper_analysis in ["True", "true", True]:
                # LLM requested analysis, check reasonable limits to prevent system overload
                logger.info(f"DEBUG: LLM requested analysis, checking limits. Papers with PDFs: {len(papers_with_pdfs)}")
                if 1 <= len(papers_with_pdfs) <= 15:
                    logger.info(f"Full paper analysis enabled (LLM requested): {len(papers_with_pdfs)} papers with PDFs")
                    return True
                elif len(papers_with_pdfs) > 15:
                    # Too many papers for analysis, but analyze top 15 instead of skipping
                    logger.info(f"Full paper analysis requested with {len(papers_with_pdfs)} papers. Will analyze top 15 papers to prevent system overload.")
                    return True
                else:
                    logger.info(f"Full paper analysis skipped (no papers with PDFs available)")
                    return False
            else:
                # LLM did not request analysis, skip
                logger.info("Full paper analysis skipped (LLM did not request)")
                return False
                
        except Exception as e:
            logger.error(f"Error checking full paper analysis condition: {e}")
            return False

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
           
                
                # Check if this is a papers_returned message
                if conv.get("role") == "assistant" and conv.get("content") == "papers_returned" and conv.get("papers"):
                    papers = conv.get("papers", [])
                    logger.info(f"Found papers_returned message with {len(papers)} papers")
                    
                    # Check if any papers are selected
                    selected_papers = [p for p in papers if p.get("selected", False)]
                    logger.info(f"Selected papers: {len(selected_papers)}")
                    
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
            response = await conv_llm_service.conversation(
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
            logger.info(f"Type of intent_result: {intent_result}")

            logger.info(f"Searching papers with refined query: {refined_query}")

            
            # Perform the search directly using the conversational search logic
            query = intent_result.get("refined_query", "")
            fields = intent_result.get("fields", {}) or {}
            num_papers = intent_result.get("num_papers", "")
            full_paper_analysis = intent_result.get("full_paper_analysis", "False")
            comparison = intent_result.get("comparison", {}) or {}
            date_filters = fields.get("date", []) or []
            authors_filters = fields.get("authors", []) or []
            platform_filters = fields.get("platform", []) or []
            author_logic = fields.get("author_logic", "AND")
            
            # Check if this is a comparison query
            is_comparison = comparison.get("value", "False") == "True"
            comparison_query = comparison.get("comparison_query", "")
            comparison_relation = comparison.get("relation", "")
            comparison_aspects = comparison.get("aspects", [])
            
            # Handle case where relation might be a list
            if isinstance(comparison_relation, list):
                comparison_relation = ", ".join(comparison_relation)
            
            # Ensure aspects is always a list
            if not isinstance(comparison_aspects, list):
                comparison_aspects = [comparison_aspects] if comparison_aspects else []
            
            # Determine if full paper analysis is requested
            full_paper_analysis_requested = intent_result.get("full_paper_analysis", "False") in ["True", "true", True]
            logger.info(f"Is comparison query: {is_comparison}")
            logger.info(f"Refined query: {query}")
            logger.info(f"Comparison query: {comparison_query}")
            logger.info(f"Comparison relation: {comparison_relation}")
            logger.info(f"Comparison aspects: {comparison_aspects}")
            
            # Check for effective filters
            has_effective_date = any(date_filters)
            has_effective_filters = bool(authors_filters) or has_effective_date or bool(platform_filters)
            
            # Pre-fetch candidate IDs by metadata if effective
            allow_ids = None
            if has_effective_filters:
                candidates = await conv_db_service.get_candidate_ids_by_metadata(
                    authors=authors_filters,
                    date_tokens=date_filters,
                    platforms=platform_filters,
                    author_logic=author_logic,
                    limit=5000,
                )
                allow_ids = set(candidates)
                if not allow_ids:
                    return {
                        "action": "results",
                        "message": "No papers found matching your criteria.",
                        "papers": [],
                        "count": 0,
                        "refined_query": query,
                        "suggestions": ["Try broader search terms", "Remove date or author filters"]
                    }
            
            if is_comparison and comparison_query:
                # For comparison queries, maintain separate lists for each query
                logger.info(f"Performing comparison search for: '{query}' vs '{comparison_query}'")
                
                # Search for refined query
                vec_task1 = asyncio.create_task(conv_vector_search_service.search(query=query, allow_ids=allow_ids))
                keyword_task1 = asyncio.create_task(conv_keyword_search_service.search(query=query, allow_ids=allow_ids))
                
                # Search for comparison query
                vec_task2 = asyncio.create_task(conv_vector_search_service.search(query=comparison_query, allow_ids=allow_ids))
                keyword_task2 = asyncio.create_task(conv_keyword_search_service.search(query=comparison_query, allow_ids=allow_ids))
                
                try:
                    results1, results2, results3, results4 = await asyncio.gather(vec_task1, keyword_task1, vec_task2, keyword_task2)
                    paper_id_platform_pairs1, keyword_paper_id_platform_pairs1 = results1, results2
                    paper_id_platform_pairs2, keyword_paper_id_platform_pairs2 = results3, results4
                except Exception as e:
                    logger.error(f"Error in comparison vector/keyword search: {e}", exc_info=True)
                    paper_id_platform_pairs1, keyword_paper_id_platform_pairs1 = [], []
                    paper_id_platform_pairs2, keyword_paper_id_platform_pairs2 = [], []
                
                # Combine results from each query separately
                combined_local_ids1 = set(paper_id_platform_pairs1).union(set(keyword_paper_id_platform_pairs1))
                combined_local_ids2 = set(paper_id_platform_pairs2).union(set(keyword_paper_id_platform_pairs2))
                
                logger.info(f"Found {len(combined_local_ids1)} papers for refined query, {len(combined_local_ids2)} papers for comparison query")
                
                # Get papers from database for each query separately
                papers1 = await conv_db_service.get_papers_by_ids(list(combined_local_ids1))
                papers2 = await conv_db_service.get_papers_by_ids(list(combined_local_ids2))
                
                # Apply metadata filtering to each list separately
                papers1 = filter_papers_by_metadata(
                    papers=papers1,
                    authors_filters=authors_filters,
                    date_filters=date_filters,
                    platform_filters=platform_filters,
                    author_logic=author_logic,
                )
                
                papers2 = filter_papers_by_metadata(
                    papers=papers2,
                    authors_filters=authors_filters,
                    date_filters=date_filters,
                    platform_filters=platform_filters,
                    author_logic=author_logic,
                )
                
                # Remove duplicates from each list
                def remove_duplicates(papers_list):
                    unique = []
                    seen_papers = set()
                    for p in papers_list:
                        # Use paper_id + platform for more robust duplicate detection
                        paper_key = (p.paper_id, p.platform)
                        if paper_key not in seen_papers:
                            unique.append(p)
                            seen_papers.add(paper_key)
                    return unique
                
                papers1 = remove_duplicates(papers1)
                papers2 = remove_duplicates(papers2)
                
                # Rerank papers for each list separately
                if papers1:
                    documents1 = [p.title + p.abstract for p in papers1]
                    rerank1 = await conv_llm_service.get_rerank(documents=documents1, query=query)
                    papers1 = [papers1[idx] for idx in rerank1]
                    
                    # Apply num_papers filtering for main query right after reranking
                    main_num_papers = intent_result.get("num_papers", "")
                    if main_num_papers and isinstance(main_num_papers, (int, str)) and str(main_num_papers).isdigit():
                        main_num_papers = int(main_num_papers)
                        papers1 = papers1[:main_num_papers]
                        logger.info(f"Limited main query results to top {main_num_papers} papers after reranking as requested")
                    else:
                        # Apply reasonable limit when num_papers is not specified
                        papers1 = papers1[:25]  # Reasonable limit for good UX
                        logger.info(f"Applied reasonable limit of 25 papers for main query (num_papers not specified)")
                    
                if papers2:
                    documents2 = [p.title + p.abstract for p in papers2]
                    rerank2 = await conv_llm_service.get_rerank(documents=documents2, query=comparison_query)
                    papers2 = [papers2[idx] for idx in rerank2]
                    
                    # Apply num_papers filtering for comparison query right after reranking
                    comparison_num_papers = comparison.get("comparison_num_papers", "")
                    if comparison_num_papers and isinstance(comparison_num_papers, (int, str)) and str(comparison_num_papers).isdigit():
                        comparison_num_papers = int(comparison_num_papers)
                        papers2 = papers2[:comparison_num_papers]
                        logger.info(f"Limited comparison query results to top {comparison_num_papers} papers after reranking as requested")
                    else:
                        # Apply reasonable limit when num_papers is not specified
                        papers2 = papers2[:25]  # Reasonable limit for good UX
                        logger.info(f"Applied reasonable limit of 25 papers for comparison query (num_papers not specified)")
                    
                    # Format results for each list (only the top N papers after reranking)
                formatted_papers1 = []
                for paper in papers1:
                    formatted_papers1.append({
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
                logger.info(f"DEBUGgg: formatted_papers1: {formatted_papers1}")
                formatted_papers2 = []
                for paper in papers2:
                    formatted_papers2.append({
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
                logger.info(f"DEBUG: formatted_papers2: {formatted_papers2}")
                       # Check if full paper analysis should be performed for comparison results
                full_paper_analysis = None

                # Combine results - if no num_papers then trim to 10, otherwise use all
                main_num_papers = intent_result.get("num_papers", "")
                comparison_num_papers = comparison.get("comparison_num_papers", "")
                
                if not main_num_papers and not comparison_num_papers:
                    # No num_papers specified for either - trim to top 10 from each list
                    all_comparison_papers = formatted_papers1[:10] + formatted_papers2[:10]
                    logger.info("No num_papers specified - limiting to top 10 from each list")
                elif not main_num_papers:
                    # Only main query has no num_papers - trim main to 10, use all comparison
                    all_comparison_papers = formatted_papers1[:10] + formatted_papers2
                    logger.info("Main query has no num_papers - limiting main to 10, using all comparison papers")
                elif not comparison_num_papers:
                    # Only comparison query has no num_papers - use all main, trim comparison to 10
                    all_comparison_papers = formatted_papers1 + formatted_papers2[:10]
                    logger.info("Comparison query has no num_papers - using all main papers, limiting comparison to 10")
                else:
                    # Both have num_papers specified - use all papers as they are
                    all_comparison_papers = formatted_papers1 + formatted_papers2
                    logger.info("Both queries have num_papers specified - using all papers without additional limiting")
                    
                # For comparison queries, always perform full paper analysis if papers are available
                should_analyze = self._should_perform_full_paper_analysis(all_comparison_papers, intent_result)
                
                logger.info(f"COMPARISON PATH: should_analyze={should_analyze}")
                
                if should_analyze:
                    try:
                        logger.info("CALLING analyze_full_papers for COMPARISON")
                        analysis_query = f"Analyze papers comparing {query} and {comparison_query}"
                        reasoning = intent_result.get("reasoning", "")
                        full_paper_analysis = await analyze_full_papers(all_comparison_papers, analysis_query, reasoning)
                        logger.info(f"Full paper analysis completed for comparison: {full_paper_analysis.get('success', False)}")
                    except Exception as e:
                        logger.error(f"Error in full paper analysis for comparison: {e}")
                        full_paper_analysis = {
                            "analysis": "",
                            "success": False,
                            "error_message": f"Full paper analysis failed: {str(e)}"
                        }
                logger.info(f"DEBUG: Final rrrrrrresponse full_paper_analysis: {full_paper_analysis} (type: {type(full_paper_analysis)})")
                
                return {
                    "action": "comparison_results",
                    "message": f"Comparison analysis between {refined_query} and {comparison_query}",
                    "papers_query1": formatted_papers1,
                    "papers_query2": formatted_papers2,
                    "count_query1": len(formatted_papers1),
                    "count_query2": len(formatted_papers2),
                    "refined_query": refined_query,
                    "comparison_query": comparison_query,
                    "comparison_relation": comparison_relation,
                    "comparison_aspects": comparison_aspects,
                    "full_paper_analysis": full_paper_analysis,
                    "suggestions": [
                        f"Find more papers comparing {refined_query} and {comparison_query}",
                        f"Show me papers that outperform {comparison_query}",
                        f"Find recent developments in {refined_query}"
                    ]
                }
                
            else:
                # Regular search (non-comparison)
                logger.info(f"Performing regular search for: '{query}'")
                
                # Run vector and keyword search
                vec_task = asyncio.create_task(conv_vector_search_service.search(query=query, allow_ids=allow_ids))
                keyword_task = asyncio.create_task(conv_keyword_search_service.search(query=query, allow_ids=allow_ids))
                
                try:
                    paper_id_platform_pairs, keyword_paper_id_platform_pairs = await asyncio.gather(vec_task, keyword_task)
                except Exception as e:
                    logger.error(f"Error in vector/keyword search: {e}", exc_info=True)
                    paper_id_platform_pairs, keyword_paper_id_platform_pairs = [], []
                
                # Combine results
                combined_local_ids = set(paper_id_platform_pairs).union(set(keyword_paper_id_platform_pairs))
                combined_local_ids = list(combined_local_ids)
                
                if not combined_local_ids:
                    return {
                        "action": "results",
                        "message": "No papers found for your query.",
                        "papers": [],
                        "count": 0,
                        "refined_query": query,
                        "suggestions": ["Try different keywords", "Use more general terms"]
                    }
                
                # Get papers from database
                papers = await conv_db_service.get_papers_by_ids(combined_local_ids)
                
                # Apply metadata filtering
                papers = filter_papers_by_metadata(
                    papers=papers,
                    authors_filters=authors_filters,
                    date_filters=date_filters,
                    platform_filters=platform_filters,
                    author_logic=author_logic,
                )
                
                # Remove duplicates while preserving order
                unique = []
                seen_papers = set()
                for p in papers:
                    # Use paper_id + platform for more robust duplicate detection
                    paper_key = (p.paper_id, p.platform)
                    if paper_key not in seen_papers:
                        unique.append(p)
                        seen_papers.add(paper_key)
                papers = unique
                
                # Rerank papers
                documents = [p.title + p.abstract for p in papers]
                rerank = await conv_llm_service.get_rerank(documents=documents, query=query)
                new_papers = [papers[idx] for idx in rerank]
                
                # Apply num_papers filtering AFTER reranking but before formatting
                num_papers = intent_result.get("num_papers", "")
                if num_papers and isinstance(num_papers, (int, str)) and str(num_papers).isdigit():
                    num_papers = int(num_papers)
                    new_papers = new_papers[:num_papers]
                    logger.info(f"Limited results to top {num_papers} papers after reranking as requested")
                else:
                    # Apply reasonable limit when num_papers is not specified
                    new_papers = new_papers[:25]  # Reasonable limit for good UX
                    logger.info(f"Applied reasonable limit of 25 papers (num_papers not specified)")
                
                # Format results (only the top N papers after reranking)
                papers = []
                for paper in new_papers:
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
                
                # Check if full paper analysis should be performed
                full_paper_analysis = None
                if self._should_perform_full_paper_analysis(papers, intent_result):
                    try:
                        analysis_query = f"Analyze papers about {query}"
                        reasoning = intent_result.get("reasoning", "")
                        # Log the papers being sent for analysis
                        logger.info(f"Papers being sent for analysis: {len(papers)} papers")
                        logger.info(f"Search query was: '{query}'")
                        logger.info(f"Refined query was: '{refined_query}'")
                        for i, paper in enumerate(papers[:5]):  # Log first 5 papers
                            logger.info(f"  Paper {i+1}: {paper.get('title', 'No title')[:100]}...")
                            logger.info(f"    PDF URL: {paper.get('pdf_url', 'No PDF URL')}")
                        # Only pass the filtered papers (after num_papers limit) to analysis
                        full_paper_analysis = await analyze_full_papers(papers, analysis_query, reasoning)
                    except Exception as e:
                        logger.error(f"Error in full paper analysis: {e}")
                        full_paper_analysis = {
                            "analysis": "",
                            "success": False,
                            "error_message": f"Full paper analysis failed: {str(e)}"
                        }
                response = {
                    "action": "results",
                    "message": "Based on your request, I found these related papers:",
                    "papers": papers,
                    "count": len(papers),
                    "refined_query": refined_query,
                    "full_paper_analysis": full_paper_analysis,
                    "suggestions": [
                        f"Find more papers about {refined_query}",
                        "What are the latest developments in this field?",
                        "Show me review papers on this topic"
                    ]
                }
                return response
            
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

    # async def _handle_chat(self, query: str, conversation_history: List[dict]) -> dict:
    #     """
    #     Handle general chat with improved context awareness
    #     """
    #     try:
    #         # Build conversation context
    #         messages = []
            
    #         # Extract recent context for better suggestions
    #         recent_context = ""
    #         for msg in conversation_history[-4:]:
    #             if msg.get('role') == 'user':
    #                 recent_context += msg.get('content', '') + " "
            
    #         # System prompt with context awareness
    #         system_prompt = """You are a friendly academic research assistant. You can explain research concepts, discuss academic topics, and answer general questions. 

    #         When explaining concepts, be clear and concise. If users ask about a specific topic, you can suggest they search for related papers to learn more.

    #         Keep the conversation natural and friendly. If the user has been discussing a specific topic, acknowledge that context in your response."""
                        
    #         messages.append({
    #             "role": "system",
    #             "content": system_prompt
    #         })
            
    #         # Add conversation history
    #         for msg in conversation_history[-6:]:  # Recent 6 turns
    #             messages.append({
    #                 "role": msg.get("role"),
    #                 "content": msg.get("content")
    #             })
            
    #         # Current query
    #         messages.append({
    #             "role": "user",
    #             "content": query
    #         })
            
    #         # Call LLM
    #         response = await conv_llm_service.conversation(messages=messages)
            
    #         # Generate context-aware suggestions
    #         suggestions = self._generate_context_aware_suggestions(recent_context, query)
            
    #         return {
    #             "action": "chat",
    #             "message": response,
    #             "papers": [],
    #             "count": 0,
    #             "suggestions": suggestions
    #         }
            
    #     except Exception as e:
    #         logger.error(f"Error in chat handling: {e}")
    #         return {
    #             "action": "chat",
    #             "message": "I'd be happy to chat with you! What would you like to know?",
    #             "papers": [],
    #             "count": 0,
    #             "suggestions": [
    #                 "Explain a research concept to me",
    #                 "Find papers on a specific topic",
    #                 "What are the current trends in machine learning?"
    #             ]
    #         }

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
            paper_details = await conv_db_service.get_paper_by_id(paper_id, platform)
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
            response = await conv_llm_service.conversation(
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
