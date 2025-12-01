#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_search_service import vector_search_service

print("FAISS index vectors:      ", vector_search_service.index.ntotal)
print("paper_ids length:         ", len(vector_search_service.paper_ids))
print("paper_platforms length:   ", len(vector_search_service.paper_platforms))
