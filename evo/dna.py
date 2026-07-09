#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNA — Persistent Vector Memory using ChromaDB + Sentence-Transformers.
Stores successful reconnaissance patterns as embeddings.
Provides fast similarity search and incremental learning.
"""

import os
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ZeroRecon")

class DNA:
    """
    Level 5 DNA: Uses ChromaDB for persistent storage and SBERT for embeddings.
    Falls back to NumPy if ChromaDB is not installed.
    """
    def __init__(self, state_dir: Path = Path("state/dna"), embedding_dim: int = 384):
        self.state_dir = Path(state_dir)
        self.embedding_dim = embedding_dim
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Try loading ChromaDB
        self.chroma = None
        self.sbert = None
        self._use_chroma = False
        self._init_backend()

    def _init_backend(self):
        """Initialize either ChromaDB or fallback to NumPy."""
        try:
            import chromadb
            from chromadb.config import Settings
            self.chroma = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(self.state_dir)
            ))
            self._use_chroma = True
            logger.info("🧬 DNA using ChromaDB (persistent vector DB).")
            # Create collection if not exists
            self.collection = self.chroma.get_or_create_collection(
                name="dna_patterns",
                metadata={"hnsw:space": "cosine"}
            )
            # Try loading SBERT for embeddings
            try:
                from sentence_transformers import SentenceTransformer
                self.sbert = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("🧬 SBERT loaded for embeddings.")
            except ImportError:
                logger.warning("⚠️ Sentence-Transformers not installed. Using random embeddings.")
        except ImportError:
            logger.warning("⚠️ ChromaDB not installed. Falling back to NumPy in-memory.")
            self._use_chroma = False
            self.weights = np.empty((0, self.embedding_dim), dtype=np.float32)
            self.meta = {"entries": []}

    def _embed(self, text: str) -> np.ndarray:
        """Generate embedding vector from text using SBERT or fallback."""
        if self.sbert:
            try:
                return self.sbert.encode(text, normalize_embeddings=True)
            except:
                pass
        # Fallback: random deterministic embedding
        np.random.seed(hash(text) % 2**32)
        return np.random.randn(self.embedding_dim)

    def add_pattern(self, text: str, metadata: Dict[str, Any]) -> None:
        """
        Add a new pattern to the DNA (text + metadata).
        """
        vector = self._embed(text)
        if self._use_chroma and self.chroma:
            try:
                self.collection.add(
                    embeddings=[vector.tolist()],
                    documents=[text],
                    metadatas=[metadata],
                    ids=[f"{metadata.get('target', 'unknown')}_{len(self.collection.get()['ids'])}"]
                )
                logger.info(f"🧬 Pattern added to ChromaDB.")
            except Exception as e:
                logger.error(f"❌ ChromaDB add failed: {e}")
        else:
            # NumPy fallback
            self.weights = np.vstack([self.weights, vector.reshape(1, -1)])
            self.meta["entries"].append(metadata)
            logger.info(f"🧬 Pattern added to NumPy DNA (total: {self.weights.shape[0]})")

    def get_similarity(self, text: str, top_k: int = 5) -> List[Dict]:
        """
        Search for similar patterns in the DNA.
        Returns list of metadata with similarity scores.
        """
        vector = self._embed(text)
        if self._use_chroma and self.chroma:
            try:
                results = self.collection.query(
                    query_embeddings=[vector.tolist()],
                    n_results=top_k,
                    include=["metadatas", "documents", "distances"]
                )
                if results and results['ids']:
                    sim_list = []
                    for idx, dist in enumerate(results['distances'][0]):
                        sim_list.append({
                            "similarity": 1.0 - dist,  # convert distance to similarity
                            "metadata": results['metadatas'][0][idx],
                            "text": results['documents'][0][idx]
                        })
                    return sorted(sim_list, key=lambda x: x['similarity'], reverse=True)
            except Exception as e:
                logger.error(f"❌ ChromaDB query failed: {e}")
        # NumPy fallback
        if self.weights.shape[0] == 0:
            return []
        norm_vec = vector / (np.linalg.norm(vector) + 1e-8)
        norm_weights = self.weights / (np.linalg.norm(self.weights, axis=1, keepdims=True) + 1e-8)
        sim = np.dot(norm_weights, norm_vec)
        indices = np.argsort(sim)[::-1][:top_k]
        results = []
        for idx in indices:
            if idx < len(self.meta["entries"]):
                entry = self.meta["entries"][idx].copy()
                entry["similarity"] = float(sim[idx])
                results.append(entry)
        return results

    def get_stats(self) -> Dict:
        if self._use_chroma and self.chroma:
            try:
                count = self.collection.count()
                return {"backend": "ChromaDB", "total_patterns": count}
            except:
                pass
        return {"backend": "NumPy", "total_patterns": self.weights.shape[0] if self.weights is not None else 0}
