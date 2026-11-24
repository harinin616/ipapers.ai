# app/routers/upload_router.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.services.db_service import db_service    
from app.services.pdf_service import pdf_service   
from app.services.llm_service import llm_service
import os
import shutil
import uuid
import logging
import json
from app.models.paper import Paper

router = APIRouter()
logger = logging.getLogger("upload")

UPLOAD_DIR = "./data/cached_pdfs/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024
_CHUNK = 1024 * 1024


async def save_validated_pdf(file: UploadFile, dest_path: str) -> int:
    """
    Stream the upload to dest_path enforcing a size cap and checking the real content starts with %PDF-
    (filename extension and browser MIME type are not trusted). Removes the partial file and raises
    HTTPException (415 / 413 / 400) on failure. Returns bytes written.
    """
    written = 0
    try:
        head = await file.read(5)
        if head != b"%PDF-":
            raise HTTPException(status_code=415, detail="File is not a valid PDF")
        with open(dest_path, "wb") as out:
            out.write(head)
            written = len(head)
            while True:
                chunk = await file.read(_CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
                    )
                out.write(chunk)
    except BaseException:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise
    if written == len(b"%PDF-"):
        os.remove(dest_path)
        raise HTTPException(status_code=400, detail="PDF file is empty")
    return written

async def extract_paper_metadata(pdf_path: str) -> dict:
    """
    从PDF中提取论文元数据(title, abstract, authors, year)
    策略：提取Introduction之前的所有内容，这部分通常包含论文的元数据
    """
    try:
        # 提取完整PDF文本
        full_text = await pdf_service.extract_text_from_pdf(pdf_path)
        
        if not full_text or len(full_text) < 50:
            logger.warning(f"PDF text too short or empty: {len(full_text)} chars")
            return {'title': '', 'abstract': '', 'authors': [], 'year': ''}
        
        # 查找Introduction或第一个章节的位置
        text_lower = full_text.lower()
        
        # 常见的章节开始标记（按优先级排序）
        section_markers = [
            r'\b1\.?\s+(introduction|background|overview)',
            r'\bintroduction\b',
            r'\b1\.?\s+',
            r'\bbackground\b',
            r'\brelated\s+work\b',
            r'\bmethods?\b',
            r'\bmethodology\b',
        ]
        
        intro_position = -1
        for pattern in section_markers:
            import re
            match = re.search(pattern, text_lower)
            if match:
                intro_position = match.start()
                logger.info(f"Found section marker at position {intro_position}: {match.group()}")
                break
        
        # 提取Introduction之前的内容（前置部分）
        if intro_position > 0:
            frontmatter = full_text[:intro_position].strip()
        else:
            # 如果没找到章节标记，取前8000字符
            frontmatter = full_text[:8000].strip()
        
        # 调试输出：显示提取的前置内容
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        
        # 使用LLM提取元数据
        prompt = f"""Extract the following information from this academic paper's front matter. Return ONLY a valid JSON object with these fields:
- title: the paper title (string)
- abstract: the paper abstract (string)  
- authors: list of author names (array of strings)
- year: publication year (string, 4 digits, or empty if not found)

If any field is not found, use empty string for title/abstract/year, or empty array for authors.

Paper front matter:
{frontmatter}

Return ONLY the JSON object, no other text:"""

        pass  # debug print removed (it logged document content)
        
        response = await llm_service.get_conversation_completion_non_streaming(
            messages=[{"role": "user", "content": prompt}]
        )
        
        # 检查 LLM 响应是否有效
        if response is None or not response.strip():
            logger.error(f"LLM returned empty response for PDF metadata extraction")
            raise Exception("LLM service returned empty response. The service may be unavailable.")
        
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        
        # 解析LLM返回的JSON
        try:
            # 尝试提取JSON（可能被包裹在其他文本中）
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                metadata = json.loads(json_str)
            else:
                metadata = json.loads(response)
            
            # 确保所有字段存在
            metadata.setdefault('title', '')
            metadata.setdefault('abstract', '')
            metadata.setdefault('authors', [])
            metadata.setdefault('year', '')
            
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            
            return metadata
        except json.JSONDecodeError as je:
            logger.error(f"JSON decode error: {je}\nResponse: {response}")
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            return {'title': '', 'abstract': '', 'authors': [], 'year': ''}
            
    except Exception as e:
        logger.error(f"Error extracting metadata from PDF: {e}", exc_info=True)
        pass  # debug print removed (it logged document content)
        pass  # debug print removed (it logged document content)
        return {'title': '', 'abstract': '', 'authors': [], 'year': ''}

@router.post("/")
async def upload_pdf(
    file: UploadFile = File(...),
    title: str = Form(""),
    authors: str = Form(""),
    published: str = Form("1900-01-01"),
    abstract: str = Form("")
):
    logger.info("Received file upload request")
    try:
        # === 1. 保存文件 ===
        ext = os.path.splitext(file.filename or "")[-1].lower()
        if ext != ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        paper_id = str(uuid.uuid4())
        filename = f"{paper_id}.pdf"
        save_path = os.path.join(UPLOAD_DIR, filename)

        await save_validated_pdf(file, save_path)
        logger.info(f"Saved PDF: {filename}")

        # === 2. 提取PDF元数据 ===
        try:
            extracted_metadata = await extract_paper_metadata(save_path)
            
            # 调试输出：打印提取到的信息
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            pass  # debug print removed (it logged document content)
            
            # 检查是否成功提取到关键信息（至少需要 title 或 abstract）
            if not extracted_metadata.get('title') and not extracted_metadata.get('abstract'):
                # 如果没有提取到任何关键信息，说明 LLM 调用可能失败了
                logger.error(f"Failed to extract metadata from PDF: {file.filename}")
                # 删除已保存的 PDF 文件
                if os.path.exists(save_path):
                    os.remove(save_path)
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to extract paper metadata. Please try uploading again or check if the PDF is valid."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during metadata extraction: {e}", exc_info=True)
            # 删除已保存的 PDF 文件
            if os.path.exists(save_path):
                os.remove(save_path)
            raise HTTPException(
                status_code=500,
                detail="Failed to process PDF. Please try again."
            )
        
        # 优先使用提取的元数据，如果提取失败则使用用户输入或默认值
        final_title = extracted_metadata.get('title') or title.strip() or "Untitled"
        final_authors = extracted_metadata.get('authors') or ([a.strip() for a in authors.split(",") if a.strip()])
        final_abstract = extracted_metadata.get('abstract') or abstract.strip()
        
        # 处理年份
        final_year = extracted_metadata.get('year', '')
        if final_year and len(final_year) == 4 and final_year.isdigit():
            final_published = f"{final_year}-01-01"
        else:
            final_published = published.strip() or "1900-01-01"

        # === 3. 写入数据库 ===
        paper= Paper(
            paper_id=paper_id,
            title=final_title,
            authors=final_authors,
            abstract=final_abstract,
            pdf_url=f"/api/data/cached_pdfs/uploads/{filename}",
            published_date=final_published,
            updated_date=final_published,
            platform="upload",
            is_public=False,
            categories=[]
        )
        try:
            added_ids = await db_service.add_papers([paper])
            if not added_ids:
                raise HTTPException(status_code=409, detail="Paper already exists")
        except Exception as e:
            logger.error(f"Database insertion failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Database error")

        logger.info(f"Inserted paper into DB: {paper_id}")

        # === 4. 生成 PDF embedding ===
     #   success = await pdf_service.generate_embeddings_for_paper(paper_id)
      #  if not success:
       #     logger.warning(f"Embedding generation failed for paper {paper_id}")

        return {"paper_id": paper_id, "platform": "upload"}

    except HTTPException:
        raise  # keep intended status codes (400/413/415/...) instead of masking them as 500
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")
