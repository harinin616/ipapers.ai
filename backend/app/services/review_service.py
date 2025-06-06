import os
import logging
import time
from typing import List, Dict, Any, AsyncGenerator, Tuple
import asyncio

from app.services.llm_service import llm_service
from app.services.pdf_service import pdf_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

class ReviewService:
    """
    Service for handling related work generation
    Uses shared file system with chat service, but maintains separate message history
    """
    
    def __init__(self):
        """
        initialize review service
        """
        # review config
        self.max_context_messages = 10
        
        # message storage for RWG (files are shared with chat)
        self.rwg_messages = {}
        
        # track processing files (shared with chat service)
        self.processing_files = set()
        
        logger.info(f"Review Service initialized. Max context: {self.max_context_messages}")
    
    # ============ RWG (RELATED WORK GENERATION) METHODS ============
    
    def add_rwg_message(self, user_id: str, role: str, content: str):
        """
        add message to related work generation conversation
        """
        if user_id not in self.rwg_messages:
            self.rwg_messages[user_id] = []
        
        self.rwg_messages[user_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
    
    def get_rwg_messages(self, user_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """get user's related work generation history messages"""
        if user_id not in self.rwg_messages:
            self.rwg_messages[user_id] = []
        messages = self.rwg_messages[user_id]
        
        if limit:
            return messages[-limit:]
        return messages

    async def format_rwg_messages(self, user_id: str) -> List[Dict[str, str]]:
        """
        format related work generation messages for API call (uses shared file system)
        """
        from app.services.chat_service import chat_service
        
        # Get file names from shared chat system
        file_names = []
        chat_data = chat_service.active_chats.get(user_id)
        if chat_data and chat_data["files"]:
            for file_data in chat_data["files"]:
                if file_data.get("selected"):
                    file_names.append(file_data.get("filename", "Unknown file"))
        
        system_content = (
            "You are a professional academic writing assistant specialized in generating related work sections. "
            "Your role is to help users create comprehensive related work sections by analyzing existing papers, "
            "identifying key contributions, methodologies, and relationships between different research efforts. "
            "Focus on creating well-structured, coherent narratives that position current work within the broader research landscape. "
            f"There are {len(file_names)} papers available for analysis: {', '.join(file_names)}. "
            "Please synthesize information from these papers to generate related work content with proper citations and flow."
        )
        
        api_messages = [{"role": "system", "content": system_content}]
        user_messages = [m for m in self.rwg_messages.get(user_id, []) if m["role"] in ["user", "assistant"]]
        recent_messages = user_messages[-self.max_context_messages:]
        for msg in recent_messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return api_messages
    
    async def generate_rwg_response(self, user_id: str, query: str) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        generate streaming response for related work generation (uses shared file system)
        """
        self.add_rwg_message(user_id, "user", query)
        
        try:
            relevant_chunks = []
            # Use shared chat system for file access
            from app.services.chat_service import chat_service
            chat_data = chat_service.active_chats.get(user_id)
            if chat_data and chat_data["files"]:
                # get relevant chunks from pdf for related work generation using shared system
                relevant_chunks = await pdf_service.query_similar_chunks(user_id, query)
            
            # format messages for related work generation
            api_messages = await self.format_rwg_messages(user_id)
            
            # add relevant chunks to the latest user message
            if relevant_chunks:
                context_text = "\n\n".join(relevant_chunks)
                last_message_idx = len(api_messages) - 1
                
                # create enhanced query with context for RWG
                enhanced_query = f"""
                {query}
                
                Based on the following content from the papers, help generate related work content:
                ---
                {context_text}
                ---
                Please synthesize this information into a coherent related work section with proper flow and citations.
                """
                
                api_messages[last_message_idx]["content"] = enhanced_query
        except Exception as e:
            logger.error(f"Error performing RAG for RWG {user_id}: {str(e)}")
            # if failed, fallback to regular message format
            api_messages = await self.format_rwg_messages(user_id)
        
        # generate response from LLM
        assistant_response = ""
        try:
            # stream response from LLM for related work generation
            stream_response = await llm_service.get_conversation_completion(
                messages=api_messages
            )
            
            if not stream_response:
                error_msg = "Sorry, I encountered an error while processing your related work generation request."
                self.add_rwg_message(user_id, "assistant", error_msg)
                yield error_msg, True
                return
            
            # process each chunk of the stream response
            async for chunk in stream_response:
                if chunk.text:
                    content = chunk.text
                    assistant_response += content
                    # immediately send each token
                    yield content, False
            
            # add to RWG history after completion
            if assistant_response:
                self.add_rwg_message(user_id, "assistant", assistant_response)
                
            # send end flag
            yield "", True
                
        except Exception as e:
            logger.error(f"Error generating RWG response for {user_id}: {str(e)}")
            error_msg = "Sorry, I encountered an error while processing your related work generation request."
            self.add_rwg_message(user_id, "assistant", error_msg)
            yield error_msg, True



# Create singleton instance
review_service = ReviewService() 