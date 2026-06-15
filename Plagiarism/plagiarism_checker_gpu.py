#!/usr/bin/env python3
"""
Windows GPU-ready plagiarism checker.
- Use GPU for embeddings (SentenceTransformer)
- Optional faiss-gpu if installed; otherwise faiss-cpu fallback
"""

import os
import re
import csv
import argparse
from pathlib import Path
from tqdm import tqdm
import numpy as np

import fitz  # PyMuPDF

from sentence_transformers import SentenceTransformer
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except Exception:
    CROSS_ENCODER_AVAILABLE = False

# FAISS (GPU optional)
try:
    import faiss
    FAISS_AVAILABLE = True
except Exception:
    faiss = None
    FAISS_AVAILABLE = False

# -------------------------
# Utilities
# -------------------------
def extract_text_from_pdf(path):
    doc = fitz.open(path)
    pages = []
    for p in doc:
        txt = p.get_text().strip()
        if txt:
            pages.append(txt)
    return "\n".join(pages)

def clean_whitespace(text):
    return re.sub(r'\s+', ' ', text).strip()

def chunk_text(text, max_words=300, overlap=60):
    words = text.split()
    if len(words) <= max_words:
        return [" ".join(words)]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks

# -------------------------
# Embedding builder (uses GPU if available)
# -------------------------
def build_embeddings(model_name, texts, device, batch_size=32):
    model = SentenceTransformer(model_name, device=device)
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
    return model, np.asarray(embeddings, dtype=np.float32)

# -------------------------
# FAISS helpers (attempt GPU index)
# -------------------------
def build_faiss_index(embeddings, use_gpu=False):
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)  # inner product on normalized vectors -> cosine
    index.add(embeddings)
    if use_gpu:
        try:
            # try to move to all GPUs
            res = faiss.StandardGpuResources()
            gpu_index = faiss.index_cpu_to_gpu(res, 0, index)  # sends to GPU 0
            return gpu_index, True
        except Exception as e:
            print("Warning: failed to build faiss GPU index, falling back to CPU faiss:", e)
            return index, False
    return index, False

# -------------------------
# Report generator (doc-level mean + chunk-level best)
# -------------------------
def generate_report(names, doc_chunks, chunk_embeddings, doc_to_chunk_indices, threshold, out_csv,
                    device, top_k_neighbors=5, cross_encoder_model=None):
    n_docs = len(names)
    # compute doc embeddings as mean of chunk embeddings
    doc_embeddings = []
    for idxs in doc_to_chunk_indices:
        if len(idxs) == 0:
            doc_embeddings.append(np.zeros(chunk_embeddings.shape[1], dtype=np.float32))
        else:
            doc_embeddings.append(np.mean(chunk_embeddings[idxs], axis=0))
    doc_embeddings = np.vstack(doc_embeddings).astype('float32')
    # normalize
    norms = np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    doc_embeddings = doc_embeddings / norms

    # FAISS search (try GPU if available)
    if FAISS_AVAILABLE:
        try:
            # try GPU (if faiss has GPU support compiled)
            use_gpu_index = hasattr(faiss, 'StandardGpuResources')
            index, used_gpu_index = build_faiss_index(doc_embeddings, use_gpu=use_gpu_index)
            D, I = index.search(doc_embeddings, top_k_neighbors + 1)
        except Exception as e:
            print("faiss search failed, falling back to brute force:", e)
            sim = doc_embeddings @ doc_embeddings.T
            idx_sort = np.argsort(-sim, axis=1)
            I = idx_sort[:, :top_k_neighbors+1]
            D = np.take_along_axis(sim, I, axis=1)
    else:
        sim = doc_embeddings @ doc_embeddings.T
        idx_sort = np.argsort(-sim, axis=1)
        I = idx_sort[:, :top_k_neighbors+1]
        D = np.take_along_axis(sim, I, axis=1)

    # Cross-encoder optional
    cross_encoder = None
    if cross_encoder_model and CROSS_ENCODER_AVAILABLE:
        cross_encoder = CrossEncoder(cross_encoder_model, device=device)

    rows = []
    for i in range(n_docs):
        neighbors = I[i]
        scores = D[i]
        for rank_idx, j in enumerate(neighbors):
            if j == i: continue
            doc_score = float(scores[rank_idx])
            if doc_score < threshold:
                continue
            # chunk-level best match
            best = (-1.0, None, None)
            for ci in doc_to_chunk_indices[i]:
                for cj in doc_to_chunk_indices[j]:
                    s = float(np.dot(chunk_embeddings[ci], chunk_embeddings[cj]))
                    if s > best[0]:
                        best = (s, doc_chunks[ci], doc_chunks[cj])
            best_score, chunk_i_text, chunk_j_text = best
            final_score = best_score
            if cross_encoder is not None:
                try:
                    ce_in = [[chunk_i_text, chunk_j_text]]
                    ce_score = cross_encoder.predict(ce_in)[0]
                    # simple combination - you can tune this
                    final_score = (best_score + (ce_score / 5.0)) / 2.0
                except Exception as e:
                    pass
            rows.append({
                "doc_a": names[i],
                "doc_b": names[j],
                "doc_level_score": f"{doc_score:.4f}",
                "best_chunk_score": f"{final_score:.4f}",
                "snippet_a": chunk_i_text[:400].replace('\n',' '),
                "snippet_b": chunk_j_text[:400].replace('\n',' '),
            })

    # dedupe and write CSV
    seen = set()
    deduped = []
    for r in rows:
        key = tuple(sorted([r["doc_a"], r["doc_b"]]))
        if key in seen: continue
        seen.add(key)
        deduped.append(r)

    deduped.sort(key=lambda x: float(x["best_chunk_score"]), reverse=True)
    keys = ["doc_a", "doc_b", "doc_level_score", "best_chunk_score", "snippet_a", "snippet_b"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in deduped:
            writer.writerow(r)
    print(f"Report: {out_csv} — {len(deduped)} flagged pairs (threshold={threshold})")

# -------------------------
# CLI
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", required=True)
    parser.add_argument("--model", default="all-mpnet-base-v2")
    parser.add_argument("--threshold", type=float, default=0.82)
    parser.add_argument("--chunk_words", type=int, default=300)
    parser.add_argument("--overlap", type=int, default=60)
    parser.add_argument("--out", default="plagiarism_report_gpu.csv")
    parser.add_argument("--use_faiss", action="store_true")
    parser.add_argument("--cross_encoder", default=None)
    args = parser.parse_args()

    device = "cuda" if (os.environ.get("CUDA_VISIBLE_DEVICES", "") != "" or
                        (hasattr(__import__("torch"), "cuda") and __import__("torch").cuda.is_available())) else "cpu"
    print("Using device:", device)

    pdf_dir = Path(args.pdf_dir)
    pdf_paths = sorted([p for p in pdf_dir.iterdir() if p.suffix.lower() == ".pdf"])
    if not pdf_paths:
        print("No PDFs found")
        return

    names, docs_text = [], []
    for p in tqdm(pdf_paths, desc="Extracting PDFs"):
        txt = extract_text_from_pdf(str(p))
        txt = clean_whitespace(txt)
        names.append(p.name)
        docs_text.append(txt)

    # chunk
    all_chunks = []
    doc_to_chunk_indices = []
    for txt in docs_text:
        chunks = chunk_text(txt, max_words=args.chunk_words, overlap=args.overlap)
        idxs = list(range(len(all_chunks), len(all_chunks) + len(chunks)))
        all_chunks.extend(chunks)
        doc_to_chunk_indices.append(idxs)

    print(f"Total chunks: {len(all_chunks)}")

    # embed chunks on GPU if available
    print("Loading model and encoding chunks (this will use GPU if available)...")
    model, chunk_embeddings = build_embeddings(args.model, all_chunks, device=device, batch_size=32)
    # ensure float32 and normalized
    chunk_embeddings = np.asarray(chunk_embeddings, dtype=np.float32)
    norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
    norms[norms==0] = 1.0
    chunk_embeddings = chunk_embeddings / norms

    generate_report(names, all_chunks, chunk_embeddings, doc_to_chunk_indices,
                    threshold=args.threshold, out_csv=args.out,
                    device=device, top_k_neighbors=5, cross_encoder_model=args.cross_encoder)

if __name__ == "__main__":
    main()
