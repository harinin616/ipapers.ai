import os
import logging
import time
import uuid
import json
import shutil
import aiofiles
import aiofiles.os
from typing import List, Dict, Any, AsyncGenerator, Tuple
from pathlib import Path
from fastapi import UploadFile
import asyncio
from pydantic import BaseModel, Field
from enum import Enum

from app.services.llm_service import llm_service
from app.services.pdf_service import pdf_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


class RelationshipType(str, Enum):
    """Enumeration of valid relationship types between papers"""
    RELATES_TO = "relates_to"
    BUILDS_ON = "builds_on"
    COMPARES_TO = "compares_to"
    CONTRADICTS = "contradicts"


class SuggestedRelationship(BaseModel):
    """Model for a single suggested relationship between papers"""
    from_paper: int = Field(..., alias="from", description="Source paper ID (1-based index)", ge=1)
    to_paper: int = Field(..., alias="to", description="Target paper ID (1-based index)", ge=1)
    relationship_type: RelationshipType = Field(..., description="Type of relationship between papers")
    description: str = Field(..., min_length=10, max_length=500, description="Brief explanation of the relationship")
    
    class Config:
        populate_by_name = True


class GraphCompletionResponse(BaseModel):
    """Model for the complete LLM response for graph completion"""
    suggested_relationships: List[SuggestedRelationship] = Field(
        default=[], 
        description="List of suggested relationships between papers"
    )

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
        
        # Paper relation graphs (per user per session)
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
    
    def add_message(self, user_id: str, session_id: str, role: str, content: str, display_content: str = None):
        """Add message to a specific session"""
        if user_id not in self.active_rws or session_id not in self.active_rws[user_id]["sessions"]:
            logger.error(f"RWS session not found: {user_id} {session_id}")
            return
        now = time.time()
        message = {
            "role": role,
            "content": content,
            "timestamp": now
        }
        # If display_content is provided, store it separately for UI display
        if display_content is not None:
            message["display_content"] = display_content
            
        self.active_rws[user_id]["sessions"][session_id]["messages"].append(message)
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
    
    def get_paper_graph(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """Get the paper relation graph for a user session"""
        if session_id is None:
            session_id = "default"
            
        graph_key = f"{user_id}:{session_id}"
        if graph_key not in self.paper_graphs:
            self.paper_graphs[graph_key] = {
                "nodes": [],  # paper metadata
                "edges": []   # directed relationships
            }
        return self.paper_graphs[graph_key]
    
    def update_graph_nodes(self, user_id: str, papers: List[Dict[str, Any]], session_id: str = None) -> bool:
        """Update graph nodes based on user's papers in a specific session"""
        try:
            if session_id is None:
                session_id = "default"
                
            graph = self.get_paper_graph(user_id, session_id)
            
            # Update nodes
            graph["nodes"] = papers
            
            # Remove edges that reference non-existent papers
            valid_paper_ids = {paper["paper_id"] for paper in papers}
            graph["edges"] = [
                edge for edge in graph["edges"]
                if edge["from"] in valid_paper_ids and edge["to"] in valid_paper_ids
            ]
            
            return True
        except Exception as e:
            logger.error(f"Error updating graph nodes for user {user_id}, session {session_id}: {str(e)}")
            return False
    
    def add_graph_edge(self, user_id: str, from_paper: str, to_paper: str, relationship_type: str = "relates_to", description: str = "", session_id: str = None) -> bool:
        """Add a directed edge between two papers in a specific session"""
        try:
            if session_id is None:
                session_id = "default"
                
            graph = self.get_paper_graph(user_id, session_id)
            
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
            logger.error(f"Error adding graph edge for user {user_id}, session {session_id}: {str(e)}")
            return False
    
    def remove_graph_edge(self, user_id: str, from_paper: str, to_paper: str, session_id: str = None) -> bool:
        """Remove a directed edge between two papers in a specific session"""
        try:
            if session_id is None:
                session_id = "default"
                
            graph = self.get_paper_graph(user_id, session_id)
            original_count = len(graph["edges"])
            graph["edges"] = [
                edge for edge in graph["edges"]
                if not (edge["from"] == from_paper and edge["to"] == to_paper)
            ]
            return len(graph["edges"]) < original_count
        except Exception as e:
            logger.error(f"Error removing graph edge for user {user_id}, session {session_id}: {str(e)}")
            return False
    
    def get_graph_context(self, user_id: str, session_id: str = None) -> str:
        """Generate context string about paper relationships for LLM in a specific session"""
        try:
            if session_id is None:
                session_id = "default"
                
            graph = self.get_paper_graph(user_id, session_id)
            
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
            logger.error(f"Error generating graph context for user {user_id}, session {session_id}: {str(e)}")
            return ""

    async def complete_graph_with_llm(self, user_id: str, session_id: str) -> dict:
        """Use LLM to analyze papers and suggest missing relationships to complete the graph"""
        try:
            from .llm_service import llm_service
            from .pdf_service import pdf_service
            
            # Get current graph and session files
            graph = self.get_paper_graph(user_id, session_id)
            session_files = self.get_session_files(user_id, session_id)
            
            if len(session_files) < 2:
                return {"success": False, "error": "Need at least 2 papers to complete graph"}
            
            # Generate summaries for all session files if not already done
            await self.summarize_session_files(user_id, session_id)
            
            # Use summaries instead of full texts for graph completion
            paper_summaries = {}
            for file_info in session_files:
                if file_info.get("selected", True):  # Only include selected files
                    paper_id = file_info["paper_id"]
                    filename = file_info.get("filename", f"{paper_id}.pdf")
                    summary = file_info.get("summary")
                    
                    if summary:
                        paper_summaries[paper_id] = {
                            "filename": filename,
                            "summary": summary
                        }
                    else:
                        logger.warning(f"No summary available for paper {paper_id}")
            
            # Ensure we have at least 2 papers with summaries
            if len(paper_summaries) < 2:
                return {"success": False, "error": "Need at least 2 papers with summaries to complete graph"}
            
            # Build existing relationships set for comparison
            existing_relationships = set()
            for edge in graph["edges"]:
                existing_relationships.add((edge["from"], edge["to"]))
                # Also add reverse to avoid suggesting opposite direction unnecessarily
                existing_relationships.add((edge["to"], edge["from"]))
            
            # Create prompt for LLM to analyze relationships using summaries
            paper_list = []
            for i, (paper_id, info) in enumerate(paper_summaries.items()):
                paper_section = f"Paper ID: {i+1}\nTitle/Filename: {info['filename']}\nSummary:\n{info['summary']}"
                paper_list.append(paper_section)
            
            existing_edges_desc = []
            if graph["edges"]:
                for edge in graph["edges"]:
                    from_name = paper_summaries.get(edge["from"], {}).get("filename", edge["from"])
                    to_name = paper_summaries.get(edge["to"], {}).get("filename", edge["to"])
                    existing_edges_desc.append(f"{edge['from']} -> {edge['to']} ({from_name} {edge['relationship_type']} {to_name})")
            
            prompt = f"""
You are an expert academic researcher analyzing relationships between research papers. 

I have {len(paper_summaries)} papers with their summaries:

{chr(10).join(['='*50 + chr(10) + paper + chr(10) + '='*50 for paper in paper_list])}

Current existing relationships:
{chr(10).join(existing_edges_desc) if existing_edges_desc else "None"}

Please analyze the summaries of these papers and suggest additional relationships that would complete the graph. The graph will be used to generate a related work section. Therefore, consider "builds_on", "compares_to" and "contradicts" relationships more than "relates_to". Consider the following relationship types:
- relates_to: General topical relationship or shared research area
- builds_on: One paper builds upon, extends, or improves another's work/methodology  
- compares_to: Papers that compare methodologies, results, or approaches
- contradicts: Papers with conflicting findings, approaches, or conclusions

For each suggested relationship, provide:
1. From paper ID (use the 1-based index from the paper list above)
2. To paper ID (use the 1-based index from the paper list above)
3. Relationship type
4. Brief description of why this relationship exists based on the paper summaries

Please respond in the following JSON format:
{{
  "suggested_relationships": [
    {{
      "from": 1,
      "to": 2, 
      "relationship_type": "builds_on",
      "description": "Brief explanation of the relationship based on paper summaries"
    }}
  ]
}}

Focus on meaningful relationships that would help understand the research landscape. Use the paper summaries to make accurate assessments of how papers relate to each other. Avoid redundant or trivial connections.
"""

            # Call LLM
            messages = [{"role": "user", "content": prompt}]
            response = await llm_service.get_conversation_completion(messages, stream=False)
            
            if not response:
                return {"success": False, "error": "Failed to get LLM response"}
            
            # Extract response text
            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'content'):
                response_text = response.content
            else:
                # Handle streaming response by collecting all chunks
                full_text = ""
                async for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        full_text += chunk.text
                response_text = full_text
            
            if not response_text:
                return {"success": False, "error": "Empty response from LLM"}
            
            # Parse and validate JSON response using Pydantic
            try:
                import re
                
                # Extract JSON from response (it might have extra text)
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    # Parse and validate using Pydantic model
                    llm_result = GraphCompletionResponse.parse_raw(json_str)
                    suggested_relationships = llm_result.suggested_relationships
                else:
                    logger.error(f"Could not extract JSON from LLM response: {response_text}")
                    return {"success": False, "error": "Invalid LLM response format"}
                
            except Exception as e:
                logger.error(f"Failed to parse and validate LLM JSON response: {str(e)}")
                logger.error(f"Response text: {response_text}")
                return {"success": False, "error": f"Failed to parse LLM response: {str(e)}"}
            
            # Convert 1-based indices to actual paper IDs and add suggested relationships to graph
            added_relationships = []
            paper_id_list = list(paper_summaries.keys())  # Get ordered list of paper IDs
            
            for rel in suggested_relationships:
                try:
                    # Convert 1-based indices to paper IDs
                    from_paper_idx = rel.from_paper - 1  # Convert to 0-based
                    to_paper_idx = rel.to_paper - 1      # Convert to 0-based
                    
                    if (0 <= from_paper_idx < len(paper_id_list) and 
                        0 <= to_paper_idx < len(paper_id_list) and 
                        from_paper_idx != to_paper_idx):
                        
                        from_paper = paper_id_list[from_paper_idx]
                        to_paper = paper_id_list[to_paper_idx]
                        rel_type = rel.relationship_type.value
                        description = rel.description
                        
                        # Check if this relationship already exists
                        if (from_paper, to_paper) not in existing_relationships:
                            # Add the edge
                            success = self.add_graph_edge(user_id, from_paper, to_paper, rel_type, description, session_id)
                            if success:
                                added_relationships.append({
                                    "from": from_paper,
                                    "to": to_paper,
                                    "from_name": paper_summaries[from_paper]["filename"],
                                    "to_name": paper_summaries[to_paper]["filename"],
                                    "relationship_type": rel_type,
                                    "description": description
                                })
                                # Update existing relationships to avoid duplicates in this session
                                existing_relationships.add((from_paper, to_paper))
                                existing_relationships.add((to_paper, from_paper))
                        else:
                            logger.info(f"Relationship {from_paper} -> {to_paper} already exists, skipping")
                    else:
                        logger.warning(f"Invalid paper indices: from={rel.from_paper}, to={rel.to_paper}, total_papers={len(paper_id_list)}")
                        
                except Exception as e:
                    logger.error(f"Error processing relationship {rel}: {str(e)}")
                    continue
            
            logger.info(f"Graph completion analysis: analyzed {len(paper_summaries)} papers, suggested {len(suggested_relationships)} relationships, added {len(added_relationships)} new edges")
            
            return {
                "success": True,
                "added_count": len(added_relationships),
                "added_relationships": added_relationships,
                "total_suggested": len(suggested_relationships)
            }
            
        except Exception as e:
            logger.error(f"Error completing graph with LLM for user {user_id}, session {session_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def format_rwg_messages(self, user_id: str, session_id: str = None) -> List[Dict[str, str]]:
        """
        Format related work generation messages for API call with conversation support
        - Different system prompts for first round vs subsequent rounds
        - Maintains conversation context appropriately
        """
        if session_id is None:
            session_id = "default"
        
        # Check if this is the first round
        existing_messages = self.get_messages(user_id, session_id)
        
        # Get file names from session-specific uploaded files
        file_names = []
        session_files = self.get_session_files(user_id, session_id)
        for file_data in session_files:
            if file_data.get("selected", True):  # Default to selected for uploaded files
                file_names.append(file_data.get("filename", "Unknown file"))

        # Get target paper for the session
        target_paper_id = self.get_target_paper(user_id, session_id)
        target_paper_info = ""
        if target_paper_id:
            # Find target paper details
            for file_data in session_files:
                if file_data.get("paper_id") == target_paper_id:
                    target_filename = file_data.get("filename", "Unknown file")
                    target_paper_info = f" The target paper is '{target_filename}' (the paper missing a related work section)."
                    break
        
        system_content = (
            "You are a professional academic writing assistant specialized in generating related work sections. "
            "You will be given: "
            "1. the summaries of the papers. "
            "2. the relationships between the papers. "
            "3. the guidance for the related work section. "
            f"{target_paper_info} "
            "Your role is to help users create a concise related work section by analyzing the summaries of the papers. "
            "When a target paper is specified, focus on generating a related work section specifically for that paper, "
            "discussing how the other papers relate to the target paper's research. "
            "Directly output the related work section, do not include any other text. "
        )
        
        api_messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history
        user_messages = [m for m in existing_messages if m["role"] in ["user", "assistant"]]
        recent_messages = user_messages[-self.max_context_messages:]
        for msg in recent_messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return api_messages
    
    async def generate_rwg_response(self, user_id: str, session_id: str = None, guidance: str = None) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        generate streaming response for related work generation with conversation support
        - Full paper texts are only included in the FIRST conversation round
        - Graph context and guidance are included in ALL rounds
        - Subsequent rounds use conversation history without full paper texts
        - User input is now handled through guidance parameter
        """
        if session_id is None:
            session_id = "default"
        
        # Check if this is the first conversation round (no previous messages)
        existing_messages = self.get_messages(user_id, session_id)
        is_first_round = len(existing_messages) == 0
        
        # Generate the complete prompt
        session_files = self.get_session_files(user_id, session_id)
        
        total_files = len(session_files)
        
        # Create appropriate message based on round
        if is_first_round:
            # First round: Include full paper analysis request
            base_message = f"Generate a comprehensive related work section based on the {total_files} available papers."
            if guidance:
                base_message += f" Please also refer to the following guidance: {guidance}"
        else:
            # Subsequent rounds: Use guidance as the user request
            base_message = "Please continue or refine the related work section based on the current context."
            if guidance:
                base_message += f" Please also refer to the following guidance: {guidance}"
        
        formatted_query = base_message
        
        # Always add graph context (relationships between papers)
        graph_context = self.get_graph_context(user_id, session_id)
        if graph_context:
            formatted_query = formatted_query + graph_context
        
        try:
            # Format messages for API call
            api_messages = await self.format_rwg_messages(user_id, session_id)
            
            # Only include full paper texts in the FIRST round
            if is_first_round:
                # Generate summaries for all session files if not already done
                await self.summarize_session_files(user_id, session_id)
                
                # Get summaries from session files
                session_summaries = []
                for file_info in session_files:
                    if file_info.get("selected", True):  # Only include selected files
                        paper_id = file_info["paper_id"]
                        filename = file_info.get("filename", f"{paper_id}.pdf")
                        summary = file_info.get("summary")
                        
                        if summary:
                            session_summaries.append({
                                "filename": filename,
                                "paper_id": paper_id,
                                "summary": summary
                            })
                        else:
                            logger.warning(f"No summary available for paper {paper_id}")
                
                # Add summaries to the latest user message only for first round
                if session_summaries:
                    # Create context with paper summaries
                    papers_context = []
                    for i, paper in enumerate(session_summaries):
                        paper_section = f"=== {paper['filename']} (paper id: {i+1}) ===\n{paper['summary']}"
                        papers_context.append(paper_section)
                    
                    context_text = "\n\n".join(papers_context)
                    last_message_idx = len(api_messages) - 1
                    
                    # Get target paper information for the enhanced query
                    target_paper_id = self.get_target_paper(user_id, session_id)
                    target_instruction = ""
                    if target_paper_id:
                        # Find target paper in the summaries
                        target_paper_index = None
                        for i, paper in enumerate(session_summaries):
                            if paper['paper_id'] == target_paper_id:
                                target_paper_index = i + 1  # 1-based index for citation
                                target_filename = paper['filename']
                                break
                        
                        if target_paper_index:
                            target_instruction = f"""
                            
                            IMPORTANT: The target paper is paper {target_paper_index} ({target_filename}) - this is the paper that is missing a related work section. 
                            Generate a related work section specifically for this target paper, focusing on how the other papers relate to the target paper's research.
                            When citing the target paper itself, refer to it as "our work" or "this paper" instead of using a citation number.
                            """
                    
                    # Create enhanced query with summary context for first round only
                    enhanced_query = f"""
                    {formatted_query}
                    
                    Based on the summaries of the following papers, help generate a comprehensive related work section:
                    ---
                    {context_text}
                    ---{target_instruction}
                    Please synthesize this information into a coherent related work section with proper flow and citations. 
                    Notice that you should cite the papers in the related work section when mentioning them using the paper id, e.g. [1], [2], etc. Do not cite them too many times. Write at most two sentences for each paper. Please directly output the related work section, do not include any other text.
                    """
                    
                    api_messages[last_message_idx]["content"] = enhanced_query
                    # Update formatted_query to include summary context for storage
                    formatted_query = enhanced_query
                    logger.info(f"First round: Enhanced RWG query with {len(session_summaries)} session paper summaries for user {user_id}, session {session_id}")
            else:
                # Subsequent rounds: just use conversation history with graph context and guidance
                logger.info(f"Subsequent round: Using conversation history with graph context for user {user_id}, session {session_id}")
            
            # Add user message to conversation history AFTER full texts are prepared
            # For display: show the guidance if it exists, otherwise show the base message for subsequent rounds
            display_content = guidance if guidance else base_message
            self.add_message(user_id, session_id, "user", formatted_query, display_content)
                
        except Exception as e:
            logger.error(f"Error preparing context for RWG {user_id}: {str(e)}")
            # If failed, fallback to regular message format
            api_messages = await self.format_rwg_messages(user_id, session_id)
            # Still add the basic message to conversation history
            display_content = guidance if guidance else base_message
            self.add_message(user_id, session_id, "user", formatted_query, display_content)
        
        # Generate response from LLM
        assistant_response = ""
        try:
            # Stream response from LLM for related work generation
            stream_response = await llm_service.get_conversation_completion(
                messages=api_messages
            )
            
            if not stream_response:
                error_msg = "Sorry, I encountered an error while processing your related work generation request."
                self.add_message(user_id, session_id, "assistant", error_msg)
                yield error_msg, True
                return
            
            # Process each chunk of the stream response
            async for chunk in stream_response:
                if chunk.text:
                    content = chunk.text
                    assistant_response += content
                    # Immediately send each token
                    yield content, False
            
            # Add to RWG history after completion
            if assistant_response:
                self.add_message(user_id, session_id, "assistant", assistant_response)
                
            # Send end flag
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
    
    def add_files_to_session(self, user_id: str, session_id: str, paper_ids: List[str]) -> bool:
        """
        Add existing files from global filelist to a specific session
        """
        try:
            # Get global user files from chat service
            from app.services.chat_service import chat_service
            chat_data = chat_service.active_chats.get(user_id)
            if not chat_data or not chat_data.get("files"):
                logger.warning(f"No global files found for user {user_id}")
                return False
            
            # Ensure session exists
            if user_id not in self.active_rws:
                self.active_rws[user_id] = {"sessions": {}}
            if session_id not in self.active_rws[user_id]["sessions"]:
                self.active_rws[user_id]["sessions"][session_id] = {
                    "messages": [],
                    "title": "Untitled RWS Session",
                    "lastMessageAt": time.time(),
                    "uploaded_files": []
                }
            
            session_data = self.active_rws[user_id]["sessions"][session_id]
            if "uploaded_files" not in session_data:
                session_data["uploaded_files"] = []
            
            # Get existing paper IDs in session to avoid duplicates
            existing_paper_ids = {file["paper_id"] for file in session_data["uploaded_files"]}
            
            # Add files from global list that match the paper_ids
            added_count = 0
            for file_data in chat_data["files"]:
                if file_data["paper_id"] in paper_ids and file_data["paper_id"] not in existing_paper_ids:
                    paper_id = file_data["paper_id"]
                    
                    # Copy embedding file from global to session-specific location
                    try:
                        # Source: global embedding file location
                        year_month = paper_id[:4]
                        year = year_month[:2]
                        month = year_month[2:4]
                        global_path = pdf_service.embedding_dir / year / month / f"{paper_id}.json"
                        
                        # Destination: session-specific location
                        session_dir = pdf_service.embedding_dir / "uploads" / user_id / session_id
                        session_path = session_dir / f"{paper_id}.json"
                        
                        # Create session directory if it doesn't exist
                        session_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Copy the embedding file if global file exists
                        if global_path.exists():
                            shutil.copy2(global_path, session_path)
                            logger.info(f"Copied embedding file from {global_path} to {session_path}")
                        else:
                            logger.warning(f"Global embedding file not found: {global_path}")
                            continue  # Skip this file if embedding doesn't exist
                        
                    except Exception as e:
                        logger.error(f"Error copying embedding file for paper {paper_id}: {str(e)}")
                        continue  # Skip this file if copy fails
                    
                    # Create session file entry based on global file
                    session_file = {
                        "paper_id": paper_id,
                        "filename": file_data["filename"],
                        "file_size": file_data.get("file_size", 0),  # May not be available in global files
                        "upload_date": time.time(),  # Use current time as "added to session" time
                        "content_type": file_data.get("content_type", "application/pdf"),
                        "selected": True,  # Auto-select added files
                        "file_path": file_data.get("file_path"),  # Keep reference to original file
                        "paper_URL": file_data.get("paper_URL"),
                        "added_from_global": True  # Flag to indicate this was added from global list
                    }
                    session_data["uploaded_files"].append(session_file)
                    added_count += 1
            
            logger.info(f"Added {added_count} files to session {session_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding files to session: {str(e)}")
            return False
    
    def remove_file_from_session(self, user_id: str, session_id: str, paper_id: str) -> bool:
        """
        Remove a file from a specific session
        """
        try:
            if (user_id not in self.active_rws or 
                session_id not in self.active_rws[user_id]["sessions"]):
                return False
            
            session_data = self.active_rws[user_id]["sessions"][session_id]
            uploaded_files = session_data.get("uploaded_files", [])
            
            # Find and remove the file
            for i, file_data in enumerate(uploaded_files):
                if file_data.get("paper_id") == paper_id:
                    uploaded_files.pop(i)
                    logger.info(f"Removed file {paper_id} from session {session_id} for user {user_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing file {paper_id} from session {session_id}: {str(e)}")
            return False
    
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

    async def get_session_full_texts(self, user_id: str, session_id: str) -> List[Dict[str, str]]:
        """
        Get full text from uploaded files in a specific session
        """
        try:
            session_files = self.get_session_files(user_id, session_id)
            if not session_files:
                return []
            
            full_texts = []
            for file_info in session_files:
                if not file_info.get("selected", True):
                    continue
                
                paper_id = file_info["paper_id"]
                filename = file_info.get("filename", f"{paper_id}.pdf")
                
                # Load full text from embedding file
                local_path = pdf_service.embedding_dir / "uploads" / user_id / session_id / f"{paper_id}.json"
                
                if not await aiofiles.os.path.exists(local_path):
                    logger.warning(f"Session embedding file not found: {local_path}")
                    continue
                
                async with aiofiles.open(local_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                
                full_text = data.get("full_text", "")
                if full_text:
                    full_texts.append({
                        "filename": filename,
                        "paper_id": paper_id,
                        "full_text": full_text
                    })
            
            logger.info(f"Retrieved {len(full_texts)} full texts from session {session_id}")
            return full_texts
            
        except Exception as e:
            logger.error(f"Error getting session full texts: {str(e)}")
            return []

    async def summarize_session_files(self, user_id: str, session_id: str) -> bool:
        """
        Generate and store summaries for all session files to be used by both graph completion and RWG
        """
        try:
            session_files = self.get_session_files(user_id, session_id)
            if not session_files:
                logger.warning(f"No session files found for user {user_id}, session {session_id}")
                return False
            
            # Get full texts for summarization
            session_full_texts = await self.get_session_full_texts(user_id, session_id)
            if not session_full_texts:
                logger.warning(f"No full texts available for user {user_id}, session {session_id}")
                return False
            
            # Create mapping from paper_id to full_text
            full_text_map = {paper["paper_id"]: paper for paper in session_full_texts}
            
            summary_count = 0
            for file_info in session_files:
                paper_id = file_info["paper_id"]
                
                # Skip if summary already exists
                if file_info.get("summary"):
                    logger.info(f"Summary already exists for paper {paper_id}")
                    continue
                
                # Get full text for this paper
                paper_data = full_text_map.get(paper_id)
                if not paper_data:
                    logger.warning(f"Full text not found for paper {paper_id}")
                    continue
                
                full_text = paper_data["full_text"]
                filename = paper_data["filename"]
                
                # Generate summary using LLM
                summary_prompt = f"""
                Please provide a concise summary of the following research paper. Focus on:
                1. The main research problem and objectives
                2. Key methodology and approach
                3. Main findings and contributions
                4. Significance and implications
                Paper: {filename}
                ---
                {full_text}
                ---
                """
                
                try:
                    # Use LLM service to generate summary
                    from .llm_service import llm_service
                    
                    api_messages = [
                        {"role": "system", "content": "You are an expert at summarizing academic papers. Provide clear, concise summaries that capture the essential contributions and methods."},
                        {"role": "user", "content": summary_prompt}
                    ]
                    
                    summary_response = await llm_service.get_conversation_completion(messages=api_messages, stream=False)
                    
                    if summary_response:
                        # Handle non-streaming response
                        summary_text = ""
                        if hasattr(summary_response, 'text'):
                            summary_text = summary_response.text
                        elif hasattr(summary_response, 'content'):
                            summary_text = summary_response.content
                        else:
                            # Fallback to streaming handling (shouldn't happen with stream=False)
                            logger.warning(f"Unexpected response format for paper {paper_id}, falling back to chunk processing")
                            async for chunk in summary_response:
                                if chunk.text:
                                    summary_text += chunk.text
                        
                        if summary_text.strip():
                            # Store summary in file_info
                            file_info["summary"] = summary_text.strip()
                            file_info["summary_generated_at"] = time.time()
                            summary_count += 1
                            logger.info(f"Generated summary for paper {paper_id}")
                        else:
                            logger.warning(f"Empty summary generated for paper {paper_id}")
                    else:
                        logger.warning(f"No response from LLM for paper {paper_id}")
                        
                except Exception as e:
                    logger.error(f"Error generating summary for paper {paper_id}: {str(e)}")
                    continue
            
            logger.info(f"Generated {summary_count} new summaries for session {session_id}")
            return summary_count > 0
            
        except Exception as e:
            logger.error(f"Error in summarize_session_files for user {user_id}, session {session_id}: {str(e)}")
            return False

    # ============ TARGET PAPER MANAGEMENT ============
    
    def set_target_paper(self, user_id: str, session_id: str, paper_id: str) -> bool:
        """
        Set the target paper (paper missing related work section) for a session
        """
        try:
            # Ensure session exists
            if user_id not in self.active_rws:
                self.active_rws[user_id] = {"sessions": {}}
            if session_id not in self.active_rws[user_id]["sessions"]:
                self.active_rws[user_id]["sessions"][session_id] = {
                    "messages": [],
                    "title": "Untitled RWS Session",
                    "lastMessageAt": time.time(),
                    "uploaded_files": []
                }
            
            session_data = self.active_rws[user_id]["sessions"][session_id]
            
            # Validate that the paper exists in the session
            session_files = session_data.get("uploaded_files", [])
            paper_exists = any(file_data.get("paper_id") == paper_id for file_data in session_files)
            
            if not paper_exists:
                logger.warning(f"Paper {paper_id} not found in session {session_id} for user {user_id}")
                return False
            
            # Set the target paper
            session_data["target_paper"] = paper_id
            session_data["target_paper_set_at"] = time.time()
            
            logger.info(f"Set target paper {paper_id} for session {session_id} of user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting target paper {paper_id} for session {session_id}: {str(e)}")
            return False
    
    def get_target_paper(self, user_id: str, session_id: str) -> str | None:
        """
        Get the current target paper for a session
        """
        try:
            if (user_id not in self.active_rws or 
                session_id not in self.active_rws[user_id]["sessions"]):
                return None
            
            session_data = self.active_rws[user_id]["sessions"][session_id]
            return session_data.get("target_paper")
            
        except Exception as e:
            logger.error(f"Error getting target paper for session {session_id}: {str(e)}")
            return None
    
    def clear_target_paper(self, user_id: str, session_id: str) -> bool:
        """
        Clear the target paper for a session
        """
        try:
            if (user_id not in self.active_rws or 
                session_id not in self.active_rws[user_id]["sessions"]):
                return False
            
            session_data = self.active_rws[user_id]["sessions"][session_id]
            
            if "target_paper" in session_data:
                del session_data["target_paper"]
            if "target_paper_set_at" in session_data:
                del session_data["target_paper_set_at"]
            
            logger.info(f"Cleared target paper for session {session_id} of user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing target paper for session {session_id}: {str(e)}")
            return False

review_service = ReviewService()