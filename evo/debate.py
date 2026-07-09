#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debate — Adversarial Multi-Agent Debate (Parallel Execution).
Runs Attacker & Defender in parallel threads to reduce time by 50%.
"""

import json
import logging
import concurrent.futures
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ZeroRecon")

class DebateEngine:
    def __init__(self, config: Dict, router):
        self.config = config
        self.router = router
        self.rounds = config.get("evo", {}).get("adversarial_debate", {}).get("rounds", 3)

    def run_debate(self, target: str, proposed_rules: List[Dict]) -> Dict[str, Any]:
        if not proposed_rules:
            return {"final_rules": [], "verdict": "No rules"}
        
        logger.info(f"⚖️ Parallel debate started for {target}")
        defender_flaws = []
        
        for _ in range(self.rounds):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Attacker (Optimist)
                attack_future = executor.submit(
                    self._call_ai, "debate_attacker", 
                    f"Justify rules for {target}: {json.dumps(proposed_rules)}"
                )
                # Defender (Skeptic) - parallel
                defend_future = executor.submit(
                    self._call_ai, "debate_defender",
                    f"Find WAF flaws in rules for {target}: {json.dumps(proposed_rules)}"
                )
                
                attacker_resp = attack_future.result(timeout=20)
                defender_resp = defend_future.result(timeout=20)
                
                if defender_resp:
                    try:
                        data = json.loads(defender_resp)
                        defender_flaws.extend(data.get("flaws", []))
                    except:
                        pass
        
        if len(defender_flaws) > 2:
            return {"final_rules": [], "verdict": "BLOCKED", "flaws": defender_flaws}
        return {"final_rules": proposed_rules, "verdict": "APPROVED", "flaws": defender_flaws}

    def _call_ai(self, task: str, prompt: str) -> Optional[str]:
        try:
            return self.router.route(task, prompt)
        except:
            return None
