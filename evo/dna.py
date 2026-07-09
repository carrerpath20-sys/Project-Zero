#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNA — Local Vector Weight Matrix for Evolutionary Learning.
Stores successful patterns as embedding vectors (NumPy) and metadata.
Provides similarity search and incremental updates.
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
    The DNA is a lightweight, compressed database of learned patterns.
    It stores vectors (successful reconnaissance patterns) and metadata.
    """
    def __init__(self, state_dir: Path = Path("state/dna"), embedding_dim: int = 384):
        self.state_dir = Path(state_dir)
        self.embedding_dim = embedding_dim
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.weights_file = self.state_dir / "weights.npy"
        self.meta_file = self.state_dir / "meta.json"
        self.meta: Dict[str, Any] = {}
        self.weights: Optional[np.ndarray] = None
        self._load()

    def _load(self) -> None:
        """Load weights and metadata from disk. Create if missing."""
        try:
            if self.weights_file.exists() and self.meta_file.exists():
                self.weights = np.load(self.weights_file)
                with open(self.meta_file, 'r') as f:
                    self.meta = json.load(f)
                logger.info(f"🧬 DNA loaded: {self.weights.shape[0]} vectors, dim {self.weights.shape[1]}")
            else:
                # Initialize empty DNA
                self.weights = np.empty((0, self.embedding_dim), dtype=np.float32)
                self.meta = {"entries": [], "version": "2.0"}
                self._save()
                logger.info("🧬 New DNA initialized.")
        except Exception as e:
            logger.error(f"❌ DNA load failed: {e}. Re-initializing.")
            self.weights = np.empty((0, self.embedding_dim), dtype=np.float32)
            self.meta = {"entries": [], "version": "2.0"}
            self._save()

    def _save(self) -> None:
        """Save weights and metadata to disk atomically."""
        try:
            # Atomic write: temp then rename
            temp_weight = self.weights_file.with_suffix(".tmp.npy")
            np.save(temp_weight, self.weights)
            temp_weight.rename(self.weights_file)
            
            temp_meta = self.meta_file.with_suffix(".tmp.json")
            with open(temp_meta, 'w') as f:
                json.dump(self.meta, f, indent=2)
            temp_meta.rename(self.meta_file)
        except Exception as e:
            logger.error(f"❌ DNA save failed: {e}")

    def add_pattern(self, vector: np.ndarray, metadata: Dict[str, Any]) -> None:
        """
        Add a new pattern vector (embedding) to the DNA with metadata.
        """
        if vector.shape[0] != self.embedding_dim:
            raise ValueError(f"Vector dim {vector.shape[0]} != {self.embedding_dim}")
        self.weights = np.vstack([self.weights, vector.reshape(1, -1)])
        self.meta["entries"].append({
            "index": len(self.meta["entries"]),
            "timestamp": metadata.get("timestamp", ""),
            "target": metadata.get("target", ""),
            "success": metadata.get("success", False),
            "pattern": metadata.get("pattern", "")
        })
        self._save()
        logger.info(f"🧬 Pattern added to DNA (total: {self.weights.shape[0]})")

    def get_similarity(self, vector: np.ndarray) -> List[Tuple[int, float]]:
        """
        Compute cosine similarity between input vector and all stored vectors.
        Returns list of (index, similarity) sorted descending.
        """
        if self.weights.shape[0] == 0:
            return []
        # Normalize
        norm_vec = vector / (np.linalg.norm(vector) + 1e-8)
        norm_weights = self.weights / (np.linalg.norm(self.weights, axis=1, keepdims=True) + 1e-8)
        sim = np.dot(norm_weights, norm_vec)
        # Sort by similarity descending
        indices = np.argsort(sim)[::-1]
        return [(int(i), float(sim[i])) for i in indices if sim[i] > 0.1]

    def predict_patterns(self, vector: np.ndarray, top_k: int = 3) -> List[Dict]:
        """
        Predict likely successful patterns based on the most similar DNA entries.
        Returns list of metadata of top_k similar patterns.
        """
        similarities = self.get_similarity(vector)
        results = []
        for idx, score in similarities[:top_k]:
            if idx < len(self.meta["entries"]):
                entry = self.meta["entries"][idx].copy()
                entry["similarity"] = score
                results.append(entry)
        logger.info(f"🧬 Predicted {len(results)} patterns from DNA.")
        return results

    def get_stats(self) -> Dict:
        return {
            "total_vectors": self.weights.shape[0] if self.weights is not None else 0,
            "dimension": self.embedding_dim,
            "entries_count": len(self.meta.get("entries", []))
        }
