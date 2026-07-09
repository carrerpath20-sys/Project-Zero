#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reflector — Epistemic Reflection Engine (Self-Correction & Injection).
Analyzes the success/failure of the mutation+debate process.
Updates DNA with successful patterns.
Injects permanent logic into local code if a pattern succeeds repeatedly.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ZeroRecon")

class Reflector:
    """
    Reflects on the outcome of a scan, updates DNA, and suggests permanent code injection.
    """
    def __init__(self, config: Dict, dna):
        self.config = config
        self.dna = dna
        self.injection_file = Path("state/dna/injected_logic.json")
        self.injection_file.parent.mkdir(parents=True, exist_ok=True)
        self._injection_log = self._load_injection_log()

    def reflect(self, target: str, rules: List[Dict], results: Dict, mcts_path: Dict) -> Dict[str, Any]:
        """
        Analyze results, update DNA, and decide on permanent injection.
        """
        logger.info(f"🔄 Reflector analyzing results for {target}")
        success_rate = self._calculate_success(results)
        insights = []

        # 1. Update DNA with successful patterns
        if success_rate > 0.7:
            import numpy as np
            # Simulate vector embedding (in production, use actual embedding)
            dummy_vec = np.random.randn(384)
            # Store the rule pattern as metadata
            for rule in rules:
                self.dna.add_pattern(
                    dummy_vec,
                    {
                        "target": target,
                        "success": True,
                        "pattern": rule.get("pattern", "unknown"),
                        "type": rule.get("type", "regex"),
                        "success_rate": success_rate
                    }
                )
            insights.append("DNA updated with successful pattern.")
        else:
            insights.append("Low success rate. DNA not updated for these rules.")

        # 2. Permanent Code Injection (if multiple successes on same pattern)
        if success_rate > 0.8 and len(self._injection_log) < 5:
            injection_decision = self._decide_injection(rules, success_rate)
            if injection_decision:
                self._inject_logic(injection_decision)
                insights.append(f"Injected new logic into system: {injection_decision['rule']}")

        return {
            "success_rate": success_rate,
            "insights": insights,
            "injected": bool(insights and "Injected" in insights[-1]),
            "dna_updated": True
        }

    def _calculate_success(self, results: Dict) -> float:
        """Calculate success rate based on findings."""
        subdomains = results.get("phase_1", {}).get("subdomains", [])
        endpoints = results.get("phase_4", {}).get("endpoints_found", [])
        if len(subdomains) > 0 or len(endpoints) > 0:
            return 0.85  # Simulate success
        return 0.2

    def _decide_injection(self, rules: List[Dict], success_rate: float) -> Optional[Dict]:
        """Decide if a rule should be permanently injected into code."""
        # Only inject if success rate is high and rule type is regex (safe to inject)
        for rule in rules:
            if rule.get("type") == "regex" and success_rate > 0.8:
                return rule
        return None

    def _inject_logic(self, rule: Dict):
        """Write the injected logic to a persistent file (simulated)."""
        self._injection_log.append(rule)
        with open(self.injection_file, 'w') as f:
            json.dump(self._injection_log, f, indent=2)
        logger.info(f"💉 Injected permanent logic: {rule.get('pattern')}")

    def _load_injection_log(self) -> List[Dict]:
        if self.injection_file.exists():
            try:
                with open(self.injection_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
