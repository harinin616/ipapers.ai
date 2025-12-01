#!/usr/bin/env python3
"""
Fetch paper_id, platform, and embeddings from PostgreSQL and save to JSONL file.

Embeddings are encoded as base64 strings to preserve exact float32 precision.

To decode on another computer:
    import json
    import base64
    import numpy as np
    
    with open('papers_embeddings.jsonl', 'r') as f:
        for line in f:
            data = json.loads(line)
            emb_bytes = base64.b64decode(data['embeddings'])
            emb_array = np.frombuffer(emb_bytes, dtype=np.float32)
            # emb_array now contains the original float32 embedding
"""

import asyncio
import json
import logging
import os
import base64
import numpy as np
from sqlalchemy import select
from app.db.database import get_async_db
from app.models.db_models import DBPaper

# ----------------------------
# CONFIG
# ----------------------------
BATCH_SIZE = 10000  # Fetch papers in batches
OUTPUT_DIR = "/home/ec2-user/jsonl_data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "papers_embeddings.jsonl")
# ----------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("create_jsonl")


async def fetch_and_save_to_jsonl():
    """Fetch all paper_id, platform, and embeddings from DB and save to JSONL."""
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    total_rows = 0
    batch_number = 1
    
    async for db in get_async_db():
        # Open file in write mode
        with open(OUTPUT_FILE, 'w') as f:
            offset = 0
            
            while True:
                logger.info(f"📦 Fetching batch #{batch_number} (OFFSET {offset}, LIMIT {BATCH_SIZE})...")
                
                result = await db.execute(
                    select(DBPaper.paper_id, DBPaper.platform, DBPaper.embedding)
                    .order_by(DBPaper.paper_id)
                    .offset(offset)
                    .limit(BATCH_SIZE)
                )
                rows = result.all()
                
                if not rows:
                    logger.info("✅ No more rows found — export complete.")
                    break
                
                # Write each row as a JSON line
                for paper_id, platform, embedding in rows:
                    # Skip rows with no embedding
                    if embedding is None:
                        continue
                    
                    # Convert embedding to numpy array if it's not already
                    emb_array = np.array(embedding, dtype=np.float32)
                    
                    # Encode as base64 to preserve exact float32 precision
                    emb_bytes = emb_array.tobytes()
                    emb_base64 = base64.b64encode(emb_bytes).decode('utf-8')
                    
                    # Create JSON object
                    data = {
                        "paper_id": paper_id,
                        "paper_platform": platform,
                        "embeddings": emb_base64,
                        "embedding_shape": emb_array.shape[0],  # Store shape for reconstruction
                        "dtype": "float32"  # Store dtype for reconstruction
                    }
                    
                    # Write as JSON line
                    f.write(json.dumps(data) + '\n')
                    total_rows += 1
                
                logger.info(f"✅ Batch #{batch_number} processed. Total rows written: {total_rows}")
                
                offset += BATCH_SIZE
                batch_number += 1
        
        await db.close()
    
    logger.info(f"🎉 Export complete! Total rows written to {OUTPUT_FILE}: {total_rows}")
    return total_rows


if __name__ == "__main__":
    asyncio.run(fetch_and_save_to_jsonl())

