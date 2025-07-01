import torch
from transformers import AutoTokenizer, AutoModel

MODEL = "allenai/specter2_base"      # 或 specter2_msmarco

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModel.from_pretrained(MODEL, trust_remote_code=True)  # 关键 flag

text = "Random walk on GPUs accelerates Markov chains."
with torch.inference_mode():
    emb = model(**tok(text, return_tensors="pt")).pooler_output

print(emb)