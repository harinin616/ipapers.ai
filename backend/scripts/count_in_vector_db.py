import faiss
import pickle

# Path to your faiss index file
index_path = "/home/ec2-user/PMo/backend/data/paper_index.faiss"

# Load the index
index = faiss.read_index(index_path)

# If you used IndexIDMap or also stored IDs separately, load that instead
# index = faiss.read_index(index_path, faiss.IO_FLAG_MMAP)

print("Number of vectors in index:", index.ntotal)
