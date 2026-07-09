#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 DNA ENGINE (Level 5 — ChromaDB Cloud + Local Fallback)
- Uses ChromaDB Cloud (if configured) or PersistentClient (local).
- Falls back to NumPy if neither is available.
- Generates embeddings via SBERT or deterministic random.
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
    Level 5 DNA: Persistent vector memory with automatic fallback.
    Now supports ChromaDB Cloud.
    """
    def __init__(self, state_dir: Path = Path("state/dna"), config: Dict = None, embedding_dim: int = 384):
        self.state_dir = Path(state_dir)
        self.embedding_dim = embedding_dim
        self.config = config or {}
        # ফোল্ডার তৈরি (যদি না থাকে) — লোকাল ফ্যালব্যাকের জন্য
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # ব্যাকএন্ড ভেরিয়েবল
        self.chroma = None
        self.collection = None
        self.sbert = None
        self._use_chroma = False
        
        # NumPy ফ্যালব্যাকের জন্য
        self.weights = np.empty((0, self.embedding_dim), dtype=np.float32)
        self.meta = {"entries": []}
        
        # ইনি‌শিয়ালাইজেশন
        self._init_backend()

    def _init_backend(self):
        """
        Initialize ChromaDB Cloud, then Local, then NumPy fallback.
        """
        try:
            import chromadb
            cloud_config = self.config.get("chromadb", {}).get("cloud", {})
            
            # 🔥 চেক করি ক্লাউড কনফিগ আছে কিনা
            if cloud_config.get("enabled") and cloud_config.get("api_key"):
                # ChromaDB Cloud
                self.chroma = chromadb.CloudClient(
                    api_key=cloud_config.get("api_key"),
                    tenant=cloud_config.get("tenant", "431f5d32-100a-4016-a2ae-43d9572e46ad"),
                    database=cloud_config.get("database", "zero_recon_dna")
                )
                self._use_chroma = True
                logger.info("🧬 DNA using ChromaDB Cloud.")
            else:
                # Local PersistentClient
                self.chroma = chromadb.PersistentClient(path=str(self.state_dir))
                self._use_chroma = True
                logger.info("🧬 DNA using ChromaDB PersistentClient (local).")
            
            # Collection তৈরি (যদি না থাকে)
            self.collection = self.chroma.get_or_create_collection(
                name="dna_patterns",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"🧬 ChromaDB collection ready: {self.collection.count()} vectors.")
            
            # SBERT লোড করার চেষ্টা (ঐচ্ছিক)
            try:
                from sentence_transformers import SentenceTransformer
                self.sbert = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("🧬 SBERT loaded for embeddings.")
            except ImportError:
                logger.warning("⚠️ Sentence-Transformers not installed. Using random embeddings.")
            except Exception as e:
                logger.warning(f"⚠️ SBERT load failed: {e}. Using random embeddings.")
                
        except ImportError:
            logger.warning("⚠️ ChromaDB not installed. Falling back to NumPy in-memory.")
            self._use_chroma = False
            self.weights = np.empty((0, self.embedding_dim), dtype=np.float32)
            self.meta = {"entries": []}
        except Exception as e:
            logger.error(f"❌ ChromaDB initialization failed: {e}. Falling back to NumPy.")
            self._use_chroma = False
            self.weights = np.empty((0, self.embedding_dim), dtype=np.float32)
            self.meta = {"entries": []}

    def _embed(self, text: str) -> np.ndarray:
        """
        Generate embedding vector from text.
        Uses SBERT if available, otherwise deterministic random.
        """
        if self.sbert:
            try:
                return self.sbert.encode(text, normalize_embeddings=True)
            except Exception as e:
                logger.debug(f"SBERT encode failed: {e}. Using random fallback.")
        # Fallback: deterministic random (same text → same vector)
        np.random.seed(hash(text) % 2**32)
        return np.random.randn(self.embedding_dim)

    def add_pattern(self, text: str, metadata: Dict[str, Any]) -> None:
        """
        Add a new pattern to the DNA (text + metadata).
        """
        try:
            vector = self._embed(text)
            if self._use_chroma and self.chroma:
                # ID তৈরি (target + timestamp)
                doc_id = f"{metadata.get('target', 'unknown')}_{len(self.collection.get()['ids'])}"
                self.collection.add(
                    embeddings=[vector.tolist()],
                    documents=[text],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                logger.info(f"🧬 Pattern added to ChromaDB: {doc_id}")
            else:
                # NumPy fallback
                self.weights = np.vstack([self.weights, vector.reshape(1, -1)])
                self.meta["entries"].append(metadata)
                logger.info(f"🧬 Pattern added to NumPy DNA (total: {self.weights.shape[0]})")
        except Exception as e:
            logger.error(f"❌ Failed to add pattern: {e}")

    def get_similarity(self, text: str, top_k: int = 5) -> List[Dict]:
        """
        Search for similar patterns in the DNA.
        Returns list of metadata with similarity scores.
        """
        try:
            vector = self._embed(text)
            if self._use_chroma and self.chroma:
                results = self.collection.query(
                    query_embeddings=[vector.tolist()],
                    n_results=top_k,
                    include=["metadatas", "documents", "distances"]
                )
                if results and results['ids']:
                    sim_list = []
                    for idx, dist in enumerate(results['distances'][0]):
                        sim_list.append({
                            "similarity": 1.0 - dist,  # cosine distance → similarity
                            "metadata": results['metadatas'][0][idx],
                            "text": results['documents'][0][idx][:200] + "..."
                        })
                    return sorted(sim_list, key=lambda x: x['similarity'], reverse=True)
                return []
        except Exception as e:
            logger.error(f"❌ ChromaDB query failed: {e}. Falling back to NumPy.")
            return self._numpy_similarity(vector, top_k)

        # NumPy fallback (if ChromaDB not used)
        return self._numpy_similarity(vector, top_k)

    def _numpy_similarity(self, vector: np.ndarray, top_k: int) -> List[Dict]:
        """NumPy-based similarity search (fallback)."""
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
        """Return DNA statistics."""
        if self._use_chroma and self.chroma:
            try:
                count = self.collection.count()
                return {"backend": "ChromaDB Cloud" if "CloudClient" in str(type(self.chroma)) else "ChromaDB Local", "total_patterns": count}
            except:
                pass
        return {"backend": "NumPy", "total_patterns": self.weights.shape[0] if self.weights is not None else 0}

    def clear(self):
        """Clear all DNA data."""
        if self._use_chroma and self.chroma:
            try:
                all_ids = self.collection.get()['ids']
                if all_ids:
                    self.collection.delete(ids=all_ids)
                logger.info("🗑️ ChromaDB DNA cleared.")
            except Exception as e:
                logger.error(f"ChromaDB clear failed: {e}")
        else:
            self.weights = np.empty((0, self.embedding_dim), dtype=np.float32)
            self.meta = {"entries": []}
            logger.info("🗑️ NumPy DNA cleared.")
