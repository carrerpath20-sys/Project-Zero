#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mutator — AI-Powered Custom Rule Generator (Mutation Phase).
Uses DNA + MCTS path + target passive data to generate custom YARA,
Nuclei, or Regex rules on the fly. These rules are unique to the target
and do not exist in public databases.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ZeroRecon")

class Mutator:
    """
    Generates target-specific reconnaissance rules using AI and DNA.
    """
    def __init__(self, config: Dict, dna, router):
        self.config = config
        self.dna = dna
        self.router = router
        self._rule_history = []

    def generate_rules(self, target: str, mcts_path: Dict, passive_data: Dict) -> Dict[str, Any]:
        """
        Main entry: generate custom rules for the selected MCTS path.
        Returns a dict with YARA/Regex/Nuclei rules.
        """
        logger.info(f"🧬 Mutator generating rules for {target} (path: {mcts_path.get('selected')})")
        try:
            # 1. Get DNA similarity patterns
            # For now, we'll use a dummy vector. In production, pass target embedding.
            import numpy as np
            dummy_vec = np.random.randn(384)
            similar_patterns = self.dna.predict_patterns(dummy_vec, top_k=2)
            
            # 2. Build prompt for AI
            prompt = f"""
            Target: {target}
            Selected Recon Path: {mcts_path.get('selected')}
            Path Description: {mcts_path.get('description')}
            Passive Data: {json.dumps(passive_data, indent=2)[:500]}
            Historical Successful Patterns: {json.dumps(similar_patterns, indent=2)}
            
            Generate 3 custom reconnaissance rules (YARA/Regex format) specifically for this target.
            Output JSON format:
            {{
                "rules": [
                    {{"type": "regex", "pattern": "...", "description": "..."}},
                    {{"type": "yara", "rule": "rule ...", "description": "..."}}
                ]
            }}
            """
            ai_response = self.router.route("mutator_gen", prompt)
            if ai_response:
                try:
                    data = json.loads(ai_response)
                    rules = data.get("rules", [])
                    logger.info(f"✅ Mutator generated {len(rules)} custom rules.")
                    self._rule_history.append({"target": target, "rules": rules, "path": mcts_path.get('selected')})
                    return {"rules": rules, "count": len(rules), "source": "ai"}
                except json.JSONDecodeError:
                    logger.warning("⚠️ AI response invalid JSON. Using fallback.")
                    return self._fallback_rules(target)
            else:
                return self._fallback_rules(target)
        except Exception as e:
            logger.error(f"❌ Mutator error: {e}. Using fallback.")
            return self._fallback_rules(target)

    def _fallback_rules(self, target: str) -> Dict:
        """Deterministic fallback if AI fails."""
        return {
            "rules": [
                {"type": "regex", "pattern": r"/api/v\d+/[a-zA-Z0-9]+", "description": "Generic API versioning"},
                {"type": "regex", "pattern": r"/admin/|/backup/|/config/", "description": "Common admin paths"}
            ],
            "count": 2,
            "source": "fallback"
        }

    def get_history(self) -> List[Dict]:
        return self._rule_history
