#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debate — Adversarial Multi-Agent Debate Engine.
Runs a debate between an 'Attacker' (optimist) and a 'Defender' (skeptic)
to validate custom rules and reduce WAF detection risk.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ZeroRecon")

class DebateEngine:
    """
    Simulates a security debate between two AI personas.
    """
    def __init__(self, config: Dict, router):
        self.config = config
        self.router = router
        self.debate_rounds = config.get("evo", {}).get("adversarial_debate", {}).get("rounds", 3)
        self.temperature = config.get("evo", {}).get("adversarial_debate", {}).get("temperature", 0.5)
        self._debate_log = []

    def run_debate(self, target: str, proposed_rules: List[Dict]) -> Dict[str, Any]:
        """
        Run a debate between Attacker and Defender on the proposed rules.
        Returns the refined rules and a final verdict.
        """
        if not proposed_rules:
            return {"final_rules": [], "verdict": "No rules to debate"}

        logger.info(f"⚖️ Debate started for {target} on {len(proposed_rules)} rules")
        attacker_opinion = proposed_rules
        defender_critique = []

        # Phase 1: Attacker justifies rules
        for i in range(self.debate_rounds):
            # Attacker (Optimist)
            attack_prompt = f"""
            Target: {target}
            Proposed rules: {json.dumps(proposed_rules, indent=2)}
            Defender's critique so far: {json.dumps(defender_critique, indent=2) if defender_critique else 'None'}
            
            Act as an AGGRESSIVE attacker. Justify why these rules are safe and effective.
            Output JSON: {{"justification": "...", "confidence_boost": 0.1}}
            """
            attacker_resp = self.router.route("debate_attacker", attack_prompt)
            if attacker_resp:
                try:
                    attacker_data = json.loads(attacker_resp)
                    logger.info(f"✅ Attacker round {i+1}: {attacker_data.get('justification', '')[:50]}...")
                except:
                    pass

            # Defender (Skeptic)
            defend_prompt = f"""
            Target: {target}
            Proposed rules: {json.dumps(proposed_rules, indent=2)}
            Attacker's justification: {attacker_resp[:300] if attacker_resp else 'None'}
            
            Act as a STRICT WAF/Cloudflare defender. Find flaws in these rules.
            Point out exact patterns that will trigger rate limiting or IP bans.
            Output JSON: {{"flaws": ["..."], "waf_block_probability": 0.7}}
            """
            defender_resp = self.router.route("debate_defender", defend_prompt)
            if defender_resp:
                try:
                    defender_data = json.loads(defender_resp)
                    defender_critique = defender_data.get("flaws", [])
                    logger.info(f"🛡️ Defender round {i+1}: Found {len(defender_critique)} flaws")
                except:
                    pass

        # Final consensus: if defender finds critical flaws, block rules.
        if defender_critique and len(defender_critique) > 2:
            verdict = "BLOCKED"
            final_rules = []
            logger.warning("⚠️ Debate verdict: Rules blocked due to high WAF detection risk.")
        else:
            verdict = "APPROVED"
            final_rules = proposed_rules
            logger.info("✅ Debate verdict: Rules approved for execution.")

        self._debate_log.append({
            "target": target,
            "rules": proposed_rules,
            "critique": defender_critique,
            "verdict": verdict
        })

        return {
            "final_rules": final_rules,
            "verdict": verdict,
            "defender_critique": defender_critique,
            "log": self._debate_log[-1]
        }

    def get_log(self) -> List[Dict]:
        return self._debate_log
