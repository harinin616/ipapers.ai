import os
import logging
import time
import uuid
import json
import aiofiles
from typing import List, Dict, Any, AsyncGenerator, Tuple
from pathlib import Path
from fastapi import UploadFile
import asyncio

from app.services.llm_service import llm_service
from app.services.pdf_service import pdf_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

class ReviewService:
    """
    Service for handling related work generation with multiple sessions support
    Uses shared file system with chat service, but maintains separate session histories
    """
    
    def __init__(self):
        """
        initialize review service
        """
        # review config
        self.max_context_messages = 10
        
        # RWS sessions (similar to chat sessions)
        self.active_rws = {}
        
        # Paper relation graphs (per user)
        self.paper_graphs = {}
        
        # track processing files (shared with chat service)
        self.processing_files = set()
        

        
        logger.info(f"Review Service initialized. Max context: {self.max_context_messages}")
    
    # ============ SESSION MANAGEMENT METHODS ============
    
    def create_session(self, user_id: str, title: str = "Untitled RWS Session") -> str:
        """Create a new RWS session"""
        if user_id not in self.active_rws:
            self.active_rws[user_id] = {"sessions": {}}
        session_id = str(uuid.uuid4())
        self.active_rws[user_id]["sessions"][session_id] = {
            "messages": [],
            "title": title,
            "lastMessageAt": time.time()
        }
        return session_id
    
    def get_sessions(self, user_id: str):
        """Get all RWS sessions for a user"""
        if user_id not in self.active_rws:
            return []
        return [
            {
                "id": sid,
                "title": ctx.get("title", "Untitled RWS Session"),
                "lastMessageAt": ctx.get("lastMessageAt", 0)
            }
            for sid, ctx in self.active_rws[user_id]["sessions"].items()
        ]
    
    def update_session_title(self, user_id: str, session_id: str, title: str) -> bool:
        """Update session title"""
        if user_id not in self.active_rws:
            return False
        sessions = self.active_rws[user_id]["sessions"]
        if session_id not in sessions:
            return False
        sessions[session_id]["title"] = title
        return True
    
    def delete_session(self, user_id: str, session_id: str):
        """Delete a session"""
        if user_id in self.active_rws and session_id in self.active_rws[user_id]["sessions"]:
            del self.active_rws[user_id]["sessions"][session_id]
    
    def add_message(self, user_id: str, session_id: str, role: str, content: str):
        """Add message to a specific session"""
        if user_id not in self.active_rws or session_id not in self.active_rws[user_id]["sessions"]:
            logger.error(f"RWS session not found: {user_id} {session_id}")
            return
        now = time.time()
        self.active_rws[user_id]["sessions"][session_id]["messages"].append({
            "role": role,
            "content": content,
            "timestamp": now
        })
        self.active_rws[user_id]["sessions"][session_id]["lastMessageAt"] = now

    def get_messages(self, user_id: str, session_id: str, limit: int = None):
        """Get messages from a specific session"""
        if user_id not in self.active_rws or session_id not in self.active_rws[user_id]["sessions"]:
            return []
        messages = self.active_rws[user_id]["sessions"][session_id]["messages"]
        if limit:
            return messages[-limit:]
        return messages
    
    # ============ GRAPH MANAGEMENT METHODS ============
    
    def get_paper_graph(self, user_id: str) -> Dict[str, Any]:
        """Get the paper relation graph for a user"""
        if user_id not in self.paper_graphs:
            self.paper_graphs[user_id] = {
                "nodes": [],  # paper metadata
                "edges": []   # directed relationships
            }
        return self.paper_graphs[user_id]
    
    def update_graph_nodes(self, user_id: str, papers: List[Dict[str, Any]]) -> bool:
        """Update graph nodes based on user's papers"""
        try:
            if user_id not in self.paper_graphs:
                self.paper_graphs[user_id] = {"nodes": [], "edges": []}
            
            # Update nodes
            self.paper_graphs[user_id]["nodes"] = papers
            
            # Remove edges that reference non-existent papers
            valid_paper_ids = {paper["paper_id"] for paper in papers}
            self.paper_graphs[user_id]["edges"] = [
                edge for edge in self.paper_graphs[user_id]["edges"]
                if edge["from"] in valid_paper_ids and edge["to"] in valid_paper_ids
            ]
            
            return True
        except Exception as e:
            logger.error(f"Error updating graph nodes for user {user_id}: {str(e)}")
            return False
    
    def add_graph_edge(self, user_id: str, from_paper: str, to_paper: str, relationship_type: str = "relates_to", description: str = "") -> bool:
        """Add a directed edge between two papers"""
        try:
            graph = self.get_paper_graph(user_id)
            
            # Check if papers exist
            paper_ids = {node["paper_id"] for node in graph["nodes"]}
            if from_paper not in paper_ids or to_paper not in paper_ids:
                return False
            
            # Check if edge already exists
            for edge in graph["edges"]:
                if edge["from"] == from_paper and edge["to"] == to_paper:
                    # Update existing edge
                    edge["relationship_type"] = relationship_type
                    edge["description"] = description
                    edge["updated_at"] = time.time()
                    return True
            
            # Add new edge
            edge = {
                "from": from_paper,
                "to": to_paper,
                "relationship_type": relationship_type,
                "description": description,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            graph["edges"].append(edge)
            return True
            
        except Exception as e:
            logger.error(f"Error adding graph edge for user {user_id}: {str(e)}")
            return False
    
    def remove_graph_edge(self, user_id: str, from_paper: str, to_paper: str) -> bool:
        """Remove a directed edge between two papers"""
        try:
            graph = self.get_paper_graph(user_id)
            original_count = len(graph["edges"])
            graph["edges"] = [
                edge for edge in graph["edges"]
                if not (edge["from"] == from_paper and edge["to"] == to_paper)
            ]
            return len(graph["edges"]) < original_count
        except Exception as e:
            logger.error(f"Error removing graph edge for user {user_id}: {str(e)}")
            return False
    
    def get_graph_context(self, user_id: str) -> str:
        """Generate context string about paper relationships for LLM"""
        try:
            graph = self.get_paper_graph(user_id)
            
            if not graph["edges"]:
                return ""
            
            # Build paper name mapping
            paper_names = {node["paper_id"]: node.get("filename", node["paper_id"]) for node in graph["nodes"]}
            
            # Generate relationship descriptions
            relationships = []
            for edge in graph["edges"]:
                from_name = paper_names.get(edge["from"], edge["from"])
                to_name = paper_names.get(edge["to"], edge["to"])
                rel_type = edge.get("relationship_type", "relates_to")
                description = edge.get("description", "")
                
                if description:
                    relationships.append(f"{from_name} {rel_type} {to_name}: {description}")
                else:
                    relationships.append(f"{from_name} {rel_type} {to_name}")
            
            if relationships:
                return f"\n\nPaper Relationships:\n" + "\n".join(f"- {rel}" for rel in relationships)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error generating graph context for user {user_id}: {str(e)}")
            return ""
    
    # ============ LEGACY METHODS (for backward compatibility) ============
    
    def add_rwg_message(self, user_id: str, role: str, content: str):
        """Legacy method - add message to default session"""
        # For backward compatibility, use a default session
        if user_id not in self.active_rws:
            self.active_rws[user_id] = {"sessions": {}}
        
        # Create default session if it doesn't exist
        default_session_id = "default"
        if default_session_id not in self.active_rws[user_id]["sessions"]:
            self.active_rws[user_id]["sessions"][default_session_id] = {
                "messages": [],
                "title": "Default RWS Session",
                "lastMessageAt": time.time()
            }
        
        self.add_message(user_id, default_session_id, role, content)
    
    def get_rwg_messages(self, user_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Legacy method - get messages from default session"""
        default_session_id = "default"
        return self.get_messages(user_id, default_session_id, limit)

    async def format_rwg_messages(self, user_id: str, session_id: str = None) -> List[Dict[str, str]]:
        """
        format related work generation messages for API call (uses shared file system)
        """
        if session_id is None:
            session_id = "default"
            
        from app.services.chat_service import chat_service
        
        # Get file names from shared chat system
        file_names = []
        chat_data = chat_service.active_chats.get(user_id)
        if chat_data and chat_data["files"]:
            for file_data in chat_data["files"]:
                if file_data.get("selected"):
                    file_names.append(file_data.get("filename", "Unknown file"))
        
        # Get graph context
        graph_context = self.get_graph_context(user_id)
        
        system_content = (
            "You are a professional academic writing assistant specialized in generating related work sections. "
            "Your role is to help users create comprehensive related work sections by analyzing existing papers, "
            "identifying key contributions, methodologies, and relationships between different research efforts. "
            "Focus on creating well-structured, coherent narratives that position current work within the broader research landscape. "
            f"There are {len(file_names)} papers available for analysis: {', '.join(file_names)}. "
            "Please synthesize information from these papers to generate related work content with proper citations and flow."
            f"{graph_context}"
        )
        
        api_messages = [{"role": "system", "content": system_content}]
        user_messages = [m for m in self.get_messages(user_id, session_id) if m["role"] in ["user", "assistant"]]
        recent_messages = user_messages[-self.max_context_messages:]
        for msg in recent_messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return api_messages
    
    async def generate_rwg_response(self, user_id: str, query: str, session_id: str = None) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        generate streaming response for related work generation (uses session-specific uploaded files)
        """
        if session_id is None:
            session_id = "default"
            
        self.add_message(user_id, session_id, "user", query)
        
        try:
            relevant_chunks = []
            
            # First try to get chunks from session-specific uploaded files
            session_chunks = await self.query_session_chunks(user_id, session_id, query)
            if session_chunks:
                relevant_chunks.extend(session_chunks)
            
            # Also get chunks from shared chat system files if available
            from app.services.chat_service import chat_service
            chat_data = chat_service.active_chats.get(user_id)
            if chat_data and chat_data["files"]:
                # get relevant chunks from pdf for related work generation using shared system
                shared_chunks = await pdf_service.query_similar_chunks(user_id, query)
                if shared_chunks:
                    relevant_chunks.extend(shared_chunks)
            
            # format messages for related work generation
            api_messages = await self.format_rwg_messages(user_id, session_id)
            
            # add relevant chunks to the latest user message
            if relevant_chunks:
                context_text = "\n\n".join(relevant_chunks[:30])  # Limit to top 30 chunks
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
            api_messages = await self.format_rwg_messages(user_id, session_id)
        
        # generate response from LLM
        assistant_response = ""
        try:
            # stream response from LLM for related work generation
            stream_response = await llm_service.get_conversation_completion(
                messages=api_messages
            )
            
            if not stream_response:
                error_msg = "Sorry, I encountered an error while processing your related work generation request."
                self.add_message(user_id, session_id, "assistant", error_msg)
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
                self.add_message(user_id, session_id, "assistant", assistant_response)
                
            # send end flag
            yield "", True
                
        except Exception as e:
            logger.error(f"Error generating RWG response for {user_id}: {str(e)}")
            error_msg = "Sorry, I encountered an error while processing your related work generation request."
            self.add_message(user_id, session_id, "assistant", error_msg)
            yield error_msg, True

    # ============ FILE PROCESSING METHODS ============
    
    async def process_uploaded_file(self, user_id: str, session_id: str, file: UploadFile, paper_id: str) -> Dict[str, Any]:
        """
        Process uploaded file using existing pdf_service methods
        """
        try:
            # Use pdf_service to process the file
            success = await pdf_service.process_uploaded_file(user_id, session_id, file, paper_id)
            
            if not success:
                logger.error(f"Failed to process uploaded file {file.filename}")
                return None
            
            # Add file to session
            file_info = {
                "paper_id": paper_id,
                "filename": file.filename,
                "file_size": file.size,
                "upload_date": time.time(),
                "content_type": file.content_type,
                "selected": True  # Auto-select uploaded files
            }
            
            # Store in session data
            if user_id not in self.active_rws:
                self.active_rws[user_id] = {"sessions": {}}
            if session_id not in self.active_rws[user_id]["sessions"]:
                self.active_rws[user_id]["sessions"][session_id] = {
                    "messages": [],
                    "title": "Untitled RWS Session",
                    "lastMessageAt": time.time(),
                    "uploaded_files": []
                }
            
            # Add to session's uploaded files
            if "uploaded_files" not in self.active_rws[user_id]["sessions"][session_id]:
                self.active_rws[user_id]["sessions"][session_id]["uploaded_files"] = []
            
            self.active_rws[user_id]["sessions"][session_id]["uploaded_files"].append(file_info)
            
            logger.info(f"Successfully processed uploaded file {file.filename} for user {user_id}, session {session_id}")
            return file_info
            
        except Exception as e:
            logger.error(f"Error processing uploaded file {file.filename}: {str(e)}")
            return None
    
    def get_session_files(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Get uploaded files for a specific session
        """
        if (user_id not in self.active_rws or 
            session_id not in self.active_rws[user_id]["sessions"]):
            return []
        
        session_data = self.active_rws[user_id]["sessions"][session_id]
        return session_data.get("uploaded_files", [])
    
    async def query_session_chunks(self, user_id: str, session_id: str, query: str) -> List[str]:
        """
        Query similar chunks from uploaded files in a specific session using pdf_service
        """
        try:
            session_files = self.get_session_files(user_id, session_id)
            if not session_files:
                return []
            
            # Use pdf_service's existing query method
            return await pdf_service.query_session_chunks(user_id, session_id, query, session_files)
            
        except Exception as e:
            logger.error(f"Error querying session chunks: {str(e)}")
            return []

review_service = ReviewService() 