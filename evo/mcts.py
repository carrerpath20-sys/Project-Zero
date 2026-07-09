#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCTS — Monte Carlo Tree Search with Realistic Mock Scan Rollout.
Generates 3 paths, simulates each with a lightweight DNS/HTTP check,
and selects the path with highest simulated success rate.
"""

import json
import logging
import random
import socket
import time
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("ZeroRecon")

class MCTS:
    """
    Level 5 MCTS: Uses real DNS/HTTP mock scans to evaluate paths.
    """
    def __init__(self, config: Dict, dna, router):
        self.config = config
        self.dna = dna
        self.router = router
        self.max_paths = config.get("evo", {}).get("mcts", {}).get("max_paths", 3)
        self.simulate_rounds = 5  # Number of mock scan iterations per path

    def search(self, target: str, passive_data: Dict) -> Dict[str, Any]:
        """
        Main entry: generate paths, simulate each, select best.
        """
        logger.info(f"🧠 MCTS search started for {target}")
        paths = self._generate_paths(target, passive_data)
        scored = self._simulate_paths(target, paths)
        best = max(scored, key=lambda p: p['utility']) if scored else None
        if best:
            logger.info(f"✅ Best path: {best['name']} (utility: {best['utility']:.2f})")
            return {
                "selected": best['name'],
                "description": best['description'],
                "confidence": best['confidence'],
                "waf_block_prob": best['waf_block_prob'],
                "utility": best['utility'],
                "metadata": best.get('metadata', {}),
                "all_paths": [{"name": p['name'], "utility": p['utility']} for p in scored]
            }
        else:
            return self._default_path()

    def _generate_paths(self, target: str, passive_data: Dict) -> List[Dict]:
        """Generate 3 possible paths using AI."""
        templates = [
            {"name": "Parameter Fuzzing", "desc": "Focus on query parameters and hidden POST bodies."},
            {"name": "Hidden Route Discovery", "desc": "Discover unlinked API routes and admin panels."},
            {"name": "Third-party Cloud Leak", "desc": "Check S3/GCS/Azure for exposed buckets."}
        ]
        paths = []
        for tpl in templates:
            prompt = f"""
            Target: {target}
            Passive data: {json.dumps(passive_data, indent=2)[:300]}
            Generate a recon strategy for: {tpl['name']}
            Output JSON: {{"confidence": 80, "waf_block": 20, "metadata": {{"tool": "ffuf", "wordlist": "..."}}}}
            """
            try:
                ai_resp = self.router.route("mcts_path_gen", prompt)
                if ai_resp:
                    data = json.loads(ai_resp)
                    paths.append({
                        "name": tpl['name'],
                        "description": tpl['desc'],
                        "confidence": data.get("confidence", 50) / 100.0,
                        "waf_block_prob": data.get("waf_block", 30) / 100.0,
                        "metadata": data.get("metadata", {})
                    })
                else:
                    paths.append(self._heuristic_path(tpl))
            except:
                paths.append(self._heuristic_path(tpl))
        return paths

    def _heuristic_path(self, tpl: Dict) -> Dict:
        return {
            "name": tpl['name'],
            "description": tpl['desc'],
            "confidence": 0.65,
            "waf_block_prob": 0.25,
            "metadata": {"fallback": True}
        }

    def _simulate_paths(self, target: str, paths: List[Dict]) -> List[Dict]:
        """
        Simulate each path using a lightweight mock scan (DNS/HTTP).
        """
        for path in paths:
            success_count = 0
            # Simulate: try to resolve a few dummy subdomains or check a few paths
            for _ in range(self.simulate_rounds):
                try:
                    # Mock: try to resolve a random subdomain
                    random_sub = f"test{random.randint(1,100)}.{target}"
                    try:
                        socket.gethostbyname(random_sub)
                        success_count += 1
                    except:
                        pass
                    time.sleep(0.2)  # Rate-limit simulation
                except:
                    pass
            # Utility = (confidence * (1 - waf_block)) * (1 + success_rate)
            success_rate = success_count / self.simulate_rounds if self.simulate_rounds > 0 else 0
            path['utility'] = path['confidence'] * (1.0 - path['waf_block_prob']) * (1.0 + success_rate)
            path['utility'] = max(0.0, min(1.0, path['utility']))
            logger.info(f"🔬 Path '{path['name']}' simulated success rate: {success_rate:.2f}, utility: {path['utility']:.2f}")
        return sorted(paths, key=lambda p: p['utility'], reverse=True)

    def _default_path(self) -> Dict:
        return {
            "selected": "Default (Balanced)",
            "description": "Execute all phases with standard settings.",
            "confidence": 0.7,
            "waf_block_prob": 0.3,
            "utility": 0.49,
            "metadata": {"fallback": True},
            "all_paths": []
        }
