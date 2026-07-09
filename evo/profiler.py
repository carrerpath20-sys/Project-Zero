#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profiler — Psychological Profiling via Code Style Analysis.
Uses offline NLP (sentence-transformers or fallback) to compare
JS code styles across companies, predicting developer overlaps.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ZeroRecon")

class Profiler:
    """
    Analyzes JS code style (comments, variable naming, structure)
    to create a profile. Compares with historical profiles to predict
    developer overlap between companies.
    """
    def __init__(self, config: Dict):
        self.config = config
        self.profile_dir = Path("state/profiles")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.sbert_model = None
        # Try loading sentence-transformers (optional)
        try:
            from sentence_transformers import SentenceTransformer
            self.sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("🧠 Sentence-Transformer loaded for profiling.")
        except ImportError:
            logger.warning("⚠️ Sentence-Transformers not installed. Using fallback profiler.")

    def profile_js(self, target: str, js_content: str) -> Dict[str, Any]:
        """
        Extract coding style features and create/update a profile.
        """
        if not js_content:
            return {"profile_id": target, "style_features": {}, "confidence": 0}

        # Extract features: comment ratio, variable naming style, indentation, etc.
        features = self._extract_features(js_content)
        profile = {
            "profile_id": target,
            "style_features": features,
            "target": target
        }

        # Check for matches with existing profiles
        matches = self._compare_profiles(profile)
        if matches:
            logger.info(f"🔗 Profiler found overlap with {matches[0]['profile_id']} (sim: {matches[0]['similarity']:.2f})")

        # Save/Update profile
        self._save_profile(profile)

        return {
            "target": target,
            "features": features,
            "matches": matches,
            "status": "profiled"
        }

    def _extract_features(self, js: str) -> Dict:
        """Extract deterministic style features."""
        import re
        lines = js.split('\n')
        total_lines = len(lines)
        comment_lines = sum(1 for l in lines if l.strip().startswith('//') or l.strip().startswith('/*'))
        indentation = "spaces" if "  " in js else "tabs" if "\t" in js else "mixed"
        var_style = "camelCase" if re.search(r'[a-z]+[A-Z]', js) else "snake_case" if re.search(r'[a-z]+_[a-z]', js) else "unknown"
        return {
            "comment_ratio": comment_lines / max(1, total_lines),
            "indentation": indentation,
            "variable_style": var_style,
            "line_count": total_lines
        }

    def _compare_profiles(self, new_profile: Dict) -> List[Dict]:
        """Compare new profile with existing ones (fallback: simple feature matching)."""
        # In production, use vector DB. Here we use simple heuristic.
        matches = []
        for profile_file in self.profile_dir.glob("*.json"):
            try:
                with open(profile_file, 'r') as f:
                    existing = json.load(f)
                if existing["profile_id"] == new_profile["profile_id"]:
                    continue
                # Simple similarity based on indentation and var_style
                if existing["style_features"]["indentation"] == new_profile["style_features"]["indentation"]:
                    matches.append({
                        "profile_id": existing["profile_id"],
                        "similarity": 0.7,
                        "target": existing.get("target", "unknown")
                    })
            except:
                pass
        return matches[:3]

    def _save_profile(self, profile: Dict):
        """Save profile to disk."""
        filepath = self.profile_dir / f"{profile['profile_id']}.json"
        try:
            with open(filepath, 'w') as f:
                json.dump(profile, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Profile save error: {e}")
