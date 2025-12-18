export RESET_FAISS=0
export FAISS_PQ_M=64          # 保持不变
export FAISS_NPROBE=64
export FAISS_TRAIN_MAX=655360
export FAISS_IVF_NLIST=16384
export EMBEDDING_BATCH_SIZE=5120
nohup /home/ec2-user/miniconda3/envs/pmo311/bin/python reset_embeddings.py > logs/rebuild.log 2>&1 &