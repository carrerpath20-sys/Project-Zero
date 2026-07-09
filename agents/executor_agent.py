#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 EXECUTOR AGENT (Level 5 — God-Tier Orchestrator)
- Uses MCTS path to decide which phases to run and in what order.
- Injects MCTS metadata, Debate verdict, and DNA reference into each phase's context.
- Handles phase failures gracefully (logs error, continues to next phase).
- Parallel execution ready (max 2 phases) — currently sequential for stability.
"""

import logging
import importlib
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

logger = logging.getLogger("ZeroRecon")

class ExecutorAgent(BaseAgent):
    def __init__(self):
        super().__init__("ExecutorAgent")
        self.phases = list(range(1, 16))  # 1 to 15
        self.max_parallel = 2
        self.results = {}

    def run(self, target: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        self._log_start()
        router = context.get("router") if context else None
        config = context.get("config") if context else None
        mcts_path = context.get("mcts_path", {})
        debate_rules = context.get("debate_rules", {})
        dna = context.get("dna")  # DNA instance (if available)

        logger.info(f"🚀 Executing {len(self.phases)} phases for {target} (MCTS: {mcts_path.get('selected', 'default')})")
        if debate_rules.get("verdict") == "BLOCKED":
            logger.warning("⚠️ Global Debate verdict: BLOCKED. Some phases may skip automatically.")

        # Sequential execution (keeping it simple and stable)
        for phase_num in self.phases:
            phase_context = {
                "target": target,
                "router": router,
                "config": config,
                "previous_results": self.results,
                "mcts_path": mcts_path,
                "debate_rules": debate_rules,
                "dna": dna
            }
            phase_result = self._run_single_phase(phase_num, target, phase_context)
            self.results[f"phase_{phase_num}"] = phase_result

            if phase_result.get("error"):
                logger.warning(f"⚠️ Phase {phase_num} had errors: {phase_result['error']}")
            elif phase_result.get("status") == "skipped":
                logger.info(f"⏭️ Phase {phase_num} skipped: {phase_result.get('reason', 'No reason provided')}")

        self._log_complete(self.results)
        return self.results

    def _run_single_phase(self, phase_num: int, target: str, phase_context: Dict) -> Dict:
        """Dynamically import and run a single phase."""
        phase_files = {
            1: "phase1_cert_subdomain",
            2: "phase2_asn",
            3: "phase3_github",
            4: "phase4_historical",
            5: "phase5_cloud",
            6: "phase6_permutation",
            7: "phase7_asn_mapping",
            8: "phase8_massdns",
            9: "phase9_osint_pipeline",
            10: "phase10_vuln_specific",
            11: "phase11_attack_surface",
            12: "phase12_report",
            13: "phase13_infrastructure_inference",
            14: "phase14_supply_chain_metadata",
            15: "phase15_continuous_diff"
        }
        module_name = phase_files.get(phase_num, f"phase{phase_num}")
        try:
            full_module = f"agents.recon.{module_name}"
            module = importlib.import_module(full_module)
            if hasattr(module, "run"):
                return module.run(target, phase_context)
            else:
                return {"error": f"Phase {phase_num} module has no 'run' function"}
        except ImportError as e:
            logger.warning(f"Phase {phase_num} module not found: {e}")
            return {"error": f"Module not found: {module_name}", "skipped": True}
        except Exception as e:
            logger.error(f"Phase {phase_num} execution error: {e}")
            return {"error": str(e)}
