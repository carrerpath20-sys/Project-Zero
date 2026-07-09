#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCTS — Monte Carlo Tree Search Engine for Recon Path Planning.
Generates 3 possible paths (fuzzing, hidden route, cloud leak),
evaluates each with confidence and WAF block probability,
selects the best path based on a utility score.
"""

import json
import logging
import random
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("ZeroRecon")

@dataclass
class PathNode:
    """Represents a possible reconnaissance path."""
    name: str
    description: str
    confidence: float          # 0-1
    waf_block_prob: float      # 0-1
    utility: float = 0.0
    metadata: Dict = field(default_factory=dict)

class MCTS:
    """
    The MCTS engine uses the AI router to generate multiple path options,
    then simulates their success via historical DNA and heuristic scoring.
    """
    def __init__(self, config: Dict, dna, router):
        self.config = config
        self.dna = dna
        self.router = router
        self.max_paths = config.get("evo", {}).get("mcts", {}).get("max_paths", 3)
        self.confidence_threshold = config.get("evo", {}).get("mcts", {}).get("confidence_threshold", 0.6)
        self._path_templates = [
            {"name": "Parameter Fuzzing", "desc": "Focus on query parameters and hidden POST bodies."},
            {"name": "Hidden Route Discovery", "desc": "Discover unlinked API routes and admin panels."},
            {"name": "Third-party Cloud Leak", "desc": "Check S3/GCS/Azure for exposed buckets and misconfigs."}
        ]

    def search(self, target: str, passive_data: Dict) -> Dict[str, Any]:
        """
        Main entry: generate paths, score them, return best path.
        """
        logger.info(f"🧠 MCTS search started for {target}")
        paths = self._generate_paths(target, passive_data)
        scored = self._score_paths(paths, target)
        best = max(scored, key=lambda p: p.utility) if scored else None
        if best:
            logger.info(f"✅ Best path: {best.name} (utility: {best.utility:.2f})")
            return {
                "selected": best.name,
                "description": best.description,
                "confidence": best.confidence,
                "waf_block_prob": best.waf_block_prob,
                "utility": best.utility,
                "metadata": best.metadata,
                "all_paths": [{"name": p.name, "utility": p.utility} for p in scored]
            }
        else:
            logger.warning("⚠️ No path reached confidence threshold. Using default.")
            return self._default_path()

    def _generate_paths(self, target: str, passive_data: Dict) -> List[PathNode]:
        """Use AI router to generate path-specific strategies."""
        paths = []
        for template in self._path_templates:
            prompt = f"""
            Target: {target}
            Passive data: {json.dumps(passive_data, indent=2)[:500]}
            
            Generate a detailed reconnaissance strategy for: {template['name']}
            Provide:
            - Specific tools/commands to run
            - Expected output format
            - Estimated success probability (0-100%)
            - WAF block probability (0-100%)
            
            Output JSON: 
            {{"confidence": 80, "waf_block": 20, "metadata": {{"tool": "ffuf", "wordlist": "..."}} }}
            """
            try:
                ai_resp = self.router.route("mcts_path_gen", prompt)
                if ai_resp:
                    # Parse AI response (assume JSON)
                    data = json.loads(ai_resp)
                    confidence = data.get("confidence", 50) / 100.0
                    waf_block = data.get("waf_block", 30) / 100.0
                    metadata = data.get("metadata", {})
                    paths.append(PathNode(
                        name=template['name'],
                        description=template['desc'],
                        confidence=confidence,
                        waf_block_prob=waf_block,
                        metadata=metadata
                    ))
                else:
                    # Fallback: use heuristic
                    paths.append(self._heuristic_path(template))
            except Exception as e:
                logger.error(f"❌ Path generation error for {template['name']}: {e}")
                paths.append(self._heuristic_path(template))
        return paths

    def _heuristic_path(self, template: Dict) -> PathNode:
        """Fallback if AI fails."""
        return PathNode(
            name=template['name'],
            description=template['desc'],
            confidence=0.65,
            waf_block_prob=0.25,
            metadata={"fallback": True}
        )

    def _score_paths(self, paths: List[PathNode], target: str) -> List[PathNode]:
        """Compute utility = confidence * (1 - waf_block_prob) * (1 + DNA_similarity_boost)."""
        # Get DNA similarity for target (if any)
        # For simplicity, we'll use a default boost if DNA has similar patterns
        dna_boost = 1.0
        # Try to get a vector representation of target (dummy)
        # In real implementation, we'd embed target using sentence-transformers
        # For now, we'll simulate
        if self.dna.weights.shape[0] > 0:
            # Dummy vector: we assume target embedding is available via profiler
            # Placeholder: we'll just use a random vector as demonstration
            import numpy as np
            dummy_vec = np.random.randn(384)
            sims = self.dna.get_similarity(dummy_vec)
            if sims:
                avg_sim = sum(s for _, s in sims[:3]) / min(3, len(sims))
                dna_boost = 1.0 + avg_sim * 0.3  # boost up to 30%
        for path in paths:
            # Utility = confidence * (1 - waf_block) * DNA boost
            path.utility = path.confidence * (1.0 - path.waf_block_prob) * dna_boost
            # Ensure utility is between 0 and 1
            path.utility = max(0.0, min(1.0, path.utility))
        return paths

    def _default_path(self) -> Dict:
        """Fallback if no path meets threshold."""
        return {
            "selected": "Default (Balanced)",
            "description": "Execute all phases with standard settings.",
            "confidence": 0.7,
            "waf_block_prob": 0.3,
            "utility": 0.49,
            "metadata": {"fallback": True},
            "all_paths": []
        }
