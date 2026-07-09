#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mutator — AI-Powered Custom Rule Generator.
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ZeroRecon")

class Mutator:
    def __init__(self, config: Dict, dna, router):
        self.config = config
        self.dna = dna
        self.router = router

    def generate_rules(self, target: str, mcts_path: Dict, passive_data: Dict) -> Dict[str, Any]:
        logger.info(f"🧬 Mutator generating rules for {target}")
        try:
            prompt = f"Target: {target}\nPath: {mcts_path.get('selected')}\nPassive: {json.dumps(passive_data)[:300]}\nGenerate 3 custom regex rules."
            ai_resp = self.router.route("mutator_gen", prompt)
            if ai_resp:
                data = json.loads(ai_resp)
                return {"rules": data.get("rules", []), "count": len(data.get("rules", [])), "source": "ai"}
        except:
            pass
        return {"rules": [{"type": "regex", "pattern": r"/api/", "description": "Default"}], "count": 1, "source": "fallback"}
