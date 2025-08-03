import os
import logging
import json

import PyPDF2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import aiofiles
import aiofiles.os
import asyncio
from pathlib import Path
import re
from fastapi import UploadFile



from datetime import datetime
import aiohttp
import json

from pathlib import Path

from app.services.llm_service import llm_service
from app.services.extract_info import paper_info_extractor
logger = logging.getLogger(__name__)

class PdfService:
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.top_k = 20
        self.downloading_processes=set()
        
        self.pdf_dir = paper_info_extractor.pdf_base_dir
        self.embedding_dir = paper_info_extractor.embedding_base_dir
    
    async def get_pdf(self, paper_id: str, platform: str = "arxiv"):
        """
        if the pdf file is not in the local directory, download it from arxiv website
        return the pdf file path
        """
        try:
            target_dir = paper_info_extractor.get_pdf_storage_directory(paper_id)
            filename = f"{paper_id}.pdf"
            local_path = target_dir / filename
            if await aiofiles.os.path.exists(local_path):
                return local_path

            key = f"{paper_id}_{platform}"
            if key in self.downloading_processes:
                while key in self.downloading_processes:
                    await asyncio.sleep(0.2)
                
                if await aiofiles.os.path.exists(local_path):
                    return local_path
                else:
                    logger.error(f"PDF file not found at: {local_path}")
                    return None
                
            self.downloading_processes.add(key)

            await aiofiles.os.makedirs(target_dir, exist_ok=True)

            pdf_url = paper_info_extractor.get_pdf_url(paper_id)
 
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        return str(local_path)
            return None
        except Exception as e:
            logger.error(f"Error downloading PDF for paper {paper_id} (platform: {platform}): {str(e)}", exc_info=True)
            return None
        finally:
            key = f"{paper_id}_{platform}"
            self.downloading_processes.discard(key)
    
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """
        extract text from pdf file
        return the text content
        """
        try:
            loop = asyncio.get_event_loop()
            text_content = await loop.run_in_executor(None, self.extract_text_sync, file_path)
            
            text_content = self.clean_text(text_content)
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            return ""
    
    def extract_text_sync(self, file_path: str) -> str:
        """
        async function to extract text from pdf file
        """
        text_content = ""
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text() + "\n\n"
        
        return text_content
    
    def clean_text(self, text: str) -> str:
        """
        clean the text content
        return the cleaned text
        """
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\d+\n', ' ', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """
        chunk the text content into many chunks
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end < len(text):
                paragraph_break = text.rfind('\n\n', start, end)
                if paragraph_break != -1 and paragraph_break > start + self.chunk_size / 2:
                    end = paragraph_break + 2
                else:
                    sentence_break = text.rfind('. ', start, end)
                    if sentence_break != -1 and sentence_break > start + self.chunk_size / 2:
                        end = sentence_break + 2
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = max(start, end - self.chunk_overlap)
        
        return chunks
    
    
    async def update_chat_files(self, user_id: str, paper_id: str, paper_title: Optional[str] = None, platform: str = "arxiv") -> bool:
        """
        update chat files for a user
        """
        from app.services.chat_service import chat_service
        try:
            filename = f"{paper_id}.pdf"
            if paper_title:
                if len(paper_title) > 100:
                    paper_title = paper_title[:97] + "..."
                filename = f"{paper_title}"
            
            existing_files = chat_service.active_chats[user_id].get("files", [])
            for existing_file in existing_files:
                if existing_file.get("paper_id") == paper_id and existing_file.get("platform", "arxiv") == platform:
                    return True
                
            file_dir=paper_info_extractor.get_pdf_storage_directory(paper_id)
            file_path= file_dir/f"{paper_id}.pdf"
            pdf_url=paper_info_extractor.get_pdf_url(paper_id)

            file_info = {
                "file_path": file_path,
                "filename": filename,
                "paper_id": paper_id,
                "platform": platform,
                "paper_URL":pdf_url,
                "added_at": datetime.now().isoformat(),
                "selected": True
            }
            
            chat_service.active_chats[user_id]["files"].append(file_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating chat files for session {user_id}: {str(e)}")
            return False

    async def query_similar_chunks(self, user_id: str, query: str) -> List[str]:
        """
        query similar chunks for a chat
        """
        from app.services.chat_service import chat_service
        session = chat_service.active_chats.get(user_id)
        files = session.get("files", [])

        all_chunks = []
        all_embeddings = []
        for file_info in files:
            if not file_info.get("selected"):
                continue
            paper_id = file_info.get("paper_id")
            logger.info(f"chat Paper name: {file_info.get('filename')}")

            local_dir = paper_info_extractor.get_embedding_storage_directory(paper_id)
            local_path = local_dir / f"{paper_id}.json"

            if not local_path.exists():
                logger.warning(f"Embedding file not found: {local_path}")
                continue
            
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            chunks = data.get("chunks", [])
            embeddings = data.get("embeddings", [])

            if not chunks or not embeddings or len(chunks) != len(embeddings):
                logger.warning(f"Invalid embedding data in {local_path}")
                continue

            all_chunks.extend(chunks)
            all_embeddings.extend(embeddings)

        if not all_chunks or not all_embeddings:
            logger.info(f"No valid embeddings found for any file in session {user_id}")
            return []
        
        
        query_embedding_list = await llm_service.get_embeddings(
            texts=[query],
        )
        
        query_embedding = query_embedding_list[0]
        similarities = []
        for i, emb in enumerate(all_embeddings):
            emb_array = np.array(emb)
            query_array = np.array(query_embedding)
            dot_product = np.dot(emb_array, query_array)
            emb_norm = np.linalg.norm(emb_array)
            query_norm = np.linalg.norm(query_array)
            similarity = dot_product / (emb_norm * query_norm)
            similarities.append((i, similarity))
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_chunks = [all_chunks[idx] for idx, _ in similarities[:self.top_k]]
        logger.info(f"Retrieved {len(top_chunks)} relevant chunks for query in chat session: {user_id} (from {len(files)} files)")
        return top_chunks

    async def generate_embeddings_for_paper(self, paper_id: str, platform: str = "arxiv") -> bool:
        """
        generate embeddings for a paper and save to local directory
        """
        try:
            pdf_path = paper_info_extractor.get_pdf_storage_directory(paper_id) / f"{paper_id}.pdf"

            if not pdf_path.exists():
                await self.get_pdf(paper_id, platform)

            target_dir = paper_info_extractor.get_embedding_storage_directory(paper_id)
            local_path = target_dir / f"{paper_id}.json"

            if local_path.exists():
                return True

            await aiofiles.os.makedirs(target_dir, exist_ok=True)
            
            text_content = await self.extract_text_from_pdf(pdf_path)
            if not text_content:
                return False
            
            chunks = self.chunk_text(text_content)
            if not chunks:
                return False

            logger.info(f"Generating embeddings for {len(chunks)} chunks for paper {paper_id} (platform: {platform})")
            
            all_embeddings = await llm_service.get_embeddings(
                texts=chunks
            )
            if all_embeddings is None:
                logger.error(f"Embedding service returned None for paper {paper_id} (platform: {platform})")
                return False

            if not isinstance(all_embeddings, (list, tuple)):
                logger.error(
                    f"Embedding service returned an unexpected type "
                    f"{type(all_embeddings)} for paper {paper_id} (platform: {platform})"
                )
                return False

            if not all_embeddings:  # 空列表
                logger.error(f"No embeddings generated for paper {paper_id} (platform: {platform})")
                return False

            
            if len(all_embeddings) != len(chunks):
                logger.error(f"Generated embeddings count ({len(all_embeddings)}) doesn't match chunks count ({len(chunks)}) for paper {paper_id} (platform: {platform})")
                return False
            

            
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump({"chunks": chunks, "embeddings": all_embeddings, "full_text": text_content}, f)
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating embeddings for paper {paper_id} (platform: {platform}): {str(e)}", exc_info=True)
            return False

    async def save_uploaded_file(self, user_id: str, session_id: str, file: UploadFile, paper_id: str) -> str:
        """
        Save uploaded file using existing directory structure
        """
        try:
            # Use existing directory structure but add session context
            target_dir = self.pdf_dir / "uploads" / user_id / session_id
            await aiofiles.os.makedirs(target_dir, exist_ok=True)
            
            # Save with proper extension
            file_extension = Path(file.filename).suffix
            saved_filename = f"{paper_id}{file_extension}"
            file_path = target_dir / saved_filename
            
            # Save file to disk
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving uploaded file {file.filename}: {str(e)}")
            raise

    async def process_uploaded_file(self, user_id: str, session_id: str, file: UploadFile, paper_id: str) -> bool:
        """
        Process uploaded file and generate embeddings using existing methods
        """
        try:
            # Save file using existing pattern
            file_path = await self.save_uploaded_file(user_id, session_id, file, paper_id)
            
            # Extract text based on file type
            if file.content_type == 'application/pdf':
                text_content = await self.extract_text_from_pdf(file_path)
            elif file.content_type == 'text/plain':
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    text_content = await f.read()
                text_content = self.clean_text(text_content)
            else:
                # Handle other file types
                text_content = f"Content from {file.filename}"
            
            if not text_content:
                return False
            

            # Save embeddings using existing format and structure
            target_dir = self.embedding_dir / "uploads" / user_id / session_id
            await aiofiles.os.makedirs(target_dir, exist_ok=True)
            local_path = target_dir / f"{paper_id}.json"
            
            embedding_data = {
                "chunks": None, 
                "embeddings": None, 
                "full_text": text_content,
                "filename": file.filename,
                "content_type": file.content_type
            }
            
            async with aiofiles.open(local_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(embedding_data))
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing uploaded file {paper_id}: {str(e)}")
            return False

    async def query_session_chunks(self, user_id: str, session_id: str, query: str, file_list: List[Dict]) -> List[str]:
        """
        Query similar chunks from session files using existing similarity logic
        """
        try:
            all_chunks = []
            all_embeddings = []
            
            # Load embeddings for session files
            for file_info in file_list:
                if not file_info.get("selected", True):
                    continue
                
                paper_id = file_info["paper_id"]
                local_path = self.embedding_dir / "uploads" / user_id / session_id / f"{paper_id}.json"
                
                if not local_path.exists():
                    logger.warning(f"Session embedding file not found: {local_path}")
                    continue
                
                async with aiofiles.open(local_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                
                chunks = data.get("chunks", [])
                embeddings = data.get("embeddings", [])
                
                if chunks and embeddings and len(chunks) == len(embeddings):
                    all_chunks.extend(chunks)
                    all_embeddings.extend(embeddings)
            
            if not all_chunks or not all_embeddings:
                return []
            
            # Use existing similarity calculation logic
            query_embedding_list = await llm_service.get_embeddings(texts=[query])
            query_embedding = query_embedding_list[0]
            
            similarities = []
            for i, emb in enumerate(all_embeddings):
                emb_array = np.array(emb)
                query_array = np.array(query_embedding)
                dot_product = np.dot(emb_array, query_array)
                emb_norm = np.linalg.norm(emb_array)
                query_norm = np.linalg.norm(query_array)
                similarity = dot_product / (emb_norm * query_norm)
                similarities.append((i, similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_chunks = [all_chunks[idx] for idx, _ in similarities[:self.top_k]]
            
            logger.info(f"Retrieved {len(top_chunks)} relevant chunks for RWS session {session_id}")
            return top_chunks
            
        except Exception as e:
            logger.error(f"Error querying session chunks: {str(e)}")
            return []

pdf_service = PdfService() 