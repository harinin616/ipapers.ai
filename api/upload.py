# app/routers/upload_router.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.services.db_service import db_service    
from app.services.pdf_service import pdf_service   
import os
import shutil
import uuid
import logging
from app.models.paper import Paper

router = APIRouter()
logger = logging.getLogger("upload")

UPLOAD_DIR = "./data/cached_pdfs/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def upload_pdf(
    file: UploadFile = File(...),
    title: str = Form(""),
    authors: str = Form(""),
    published: str = Form("1900-01-01"),
    abstract: str = Form("")
):
    logger.info(f"Received file upload request: {file.filename}")
    try:
        # === 1. 保存文件 ===
        ext = os.path.splitext(file.filename)[-1].lower()
        if ext != ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        paper_id = str(uuid.uuid4())
        filename = f"{paper_id}.pdf"
        save_path = os.path.join(UPLOAD_DIR, filename)

        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        logger.info(f"Saved PDF: {save_path}")

        # === 2. 写入数据库 ===
        paper= Paper(
            paper_id=paper_id,
            title=title.strip()if title else "Untitled",
            authors=[a.strip() for a in authors.split(",") if a.strip()],
            abstract=abstract.strip(),
            pdf_url=f"/data/cached_pdfs/uploads/{filename}",
            published_date=published.strip(),
            updated_date=published.strip(),
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

        return paper_id

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")
