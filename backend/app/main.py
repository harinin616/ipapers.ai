import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging


from fastapi.responses import HTMLResponse
from app.api import paper, search, chat, user, auth, review,share, metrics,contact,topics,folders,forum,comments,upload
from fastapi.staticfiles import StaticFiles
# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


logger = logging.getLogger(__name__)

# Create API sub-application
api_app = FastAPI()

# Main application
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_app.mount(
    "/data/cached_pdfs/uploads",
    StaticFiles(directory="data/cached_pdfs/uploads"),
    name="pdf_uploads",
)

#@app.get("/", response_class=HTMLResponse)   
#@app.head("/") 
#async def root():
#    return ""

# Include API routes
api_app.include_router(paper.router, prefix="/papers", tags=["papers"])
api_app.include_router(search.router, prefix="/search", tags=["search"])
api_app.include_router(chat.router, prefix="/chat", tags=["chat"])
api_app.include_router(review.router, prefix="/review", tags=["review"])
api_app.include_router(user.router, prefix="/user", tags=["user"])
api_app.include_router(auth.router, prefix="/auth", tags=["auth"])
#api_app.include_router(share.router, prefix="/share", tags=["share"]) 
api_app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_app.include_router(contact.router, prefix="/contact", tags=["contact"])
api_app.include_router(topics.router, prefix="/topics", tags=["topics"])
api_app.include_router(folders.router, prefix="/folders", tags=["folders"])
api_app.include_router(forum.router, prefix="/forum", tags=["forum"])
api_app.include_router(comments.router, prefix="/comments", tags=["comments"])
api_app.include_router(upload.router, prefix="/upload", tags=["upload"])
# Mount API sub-application to main application
app.mount("/api", api_app)