#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 HEALER AGENT (Level 5 — Debate-Aware + DNA-Enhanced Self-Healer)
- Checks Debate verdict: if BLOCKED, skips healing for that phase.
- Queries DNA for similar past failures and their solutions.
- Generates AI-powered fix suggestions (if router available).
- Updates DNA with successful fixes for future learning.
- Logs all healing attempts to evolution_log.json.
- Implements retry limit (max 3 attempts per phase).
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from pathlib import Path

logger = logging.getLogger("ZeroRecon")

class HealerAgent(BaseAgent):
    def __init__(self):
        super().__init__("HealerAgent")
        self.max_attempts = 3
        self.fix_history = {}  # {phase_key: attempt_count}
        self.evolution_log = Path("state/evolution_log.json")
        self.evolution_log.parent.mkdir(parents=True, exist_ok=True)

    def run(self, target: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        self._log_start()
        if not context:
            return {"error": "No context provided", "status": "failed"}

        results = context.get("results", {})
        router = context.get("router")
        debate_rules = context.get("debate_rules", {})
        dna = context.get("dna")

        fixed_phases = []
        errors_remaining = []

        for phase_key, phase_data in results.items():
            if not isinstance(phase_data, dict):
                continue

            # Skip if no error and not skipped
            if "error" not in phase_data and phase_data.get("status") != "skipped":
                continue

            phase_num = phase_key.replace("phase_", "")
            if not phase_num.isdigit():
                continue

            # If debate blocked, don't attempt fix
            if debate_rules.get("verdict") == "BLOCKED":
                logger.warning(f"⚠️ Debate blocked Phase {phase_num}. Skipping healing.")
                errors_remaining.append(phase_key)
                continue

            # Track attempts
            if phase_key not in self.fix_history:
                self.fix_history[phase_key] = 0
            self.fix_history[phase_key] += 1

            if self.fix_history[phase_key] > self.max_attempts:
                logger.warning(f"⚠️ Max attempts reached for {phase_key}. Giving up.")
                errors_remaining.append(phase_key)
                continue

            logger.info(f"🩹 Attempting to fix {phase_key} (attempt {self.fix_history[phase_key]})")
            fix_result = self._fix_phase(
                phase_num, phase_data, target, router, dna, self.fix_history[phase_key]
            )

            if fix_result.get("fixed"):
                fixed_phases.append(phase_key)
                # Update results with fix data
                results[phase_key]["fixed"] = fix_result.get("fix_data")
                # Log success to evolution log
                self._log_evolution(target, phase_num, fix_result, outcome="success")
                # If DNA exists, store the successful fix pattern
                if dna and fix_result.get("fix_data"):
                    try:
                        dna.add_pattern(
                            text=str(fix_result["fix_data"]),
                            metadata={
                                "target": target,
                                "phase": phase_num,
                                "success": True,
                                "timestamp": time.time()
                            }
                        )
                    except Exception as e:
                        logger.debug(f"DNA update failed: {e}")
            else:
                errors_remaining.append(phase_key)
                self._log_evolution(target, phase_num, fix_result, outcome="failure")
                logger.warning(f"⚠️ Could not fix {phase_key}")

        result = {
            "target": target,
            "fixed_phases": fixed_phases,
            "errors_remaining": errors_remaining,
            "status": "complete" if not errors_remaining else "partial",
            "total_fixed": len(fixed_phases)
        }

        self._log_complete(result)
        return result

    def _fix_phase(
        self,
        phase_num: str,
        phase_data: Dict,
        target: str,
        router,
        dna,
        attempt: int
    ) -> Dict:
        """Attempt to fix a single phase using AI and DNA."""
        error_msg = phase_data.get("error", "Unknown error")
        phase_key = f"phase_{phase_num}"

        # Try to find a solution from DNA (if available)
        dna_solution = None
        if dna:
            try:
                similar = dna.get_similarity(f"Phase {phase_num} error: {error_msg}", top_k=1)
                if similar and similar[0].get("similarity", 0) > 0.6:
                    dna_solution = similar[0].get("text", "")
                    logger.info(f"🧬 DNA suggested fix: {dna_solution[:100]}...")
            except Exception as e:
                logger.debug(f"DNA query failed: {e}")

        # If AI router available, generate a fix suggestion
        ai_suggestion = None
        if router:
            try:
                prompt = f"""
                Phase {phase_num} for target {target} failed with error:
                {error_msg}
                Partial data: {json.dumps(phase_data, indent=2, default=str)[:500]}
                {f'DNA suggestion: {dna_solution}' if dna_solution else ''}
                Provide a fix strategy (2-3 sentences) or suggest skipping this phase.
                """
                ai_resp = router.route("fix_phase", prompt)
                if ai_resp:
                    ai_suggestion = ai_resp
            except Exception as e:
                logger.warning(f"AI fix generation failed: {e}")

        # Decide fix action
        fix_data = {}
        fixed = False

        # 1. If DNA solution exists and seems applicable
        if dna_solution:
            fix_data["dna_solution"] = dna_solution
            fixed = True

        # 2. If AI gave a suggestion
        elif ai_suggestion:
            fix_data["ai_suggestion"] = ai_suggestion
            fixed = True

        # 3. Generic fallback based on error type
        else:
            if "timeout" in error_msg.lower():
                fix_data["action"] = "increase_timeout"
                fix_data["new_timeout"] = min(30, 10 + attempt * 5)
                fixed = True
            elif "not found" in error_msg.lower() or "import" in error_msg.lower():
                fix_data["action"] = "skip_phase"
                fix_data["reason"] = "Module missing or dependency issue"
                fixed = True
            elif "rate limit" in error_msg.lower():
                fix_data["action"] = "wait_and_retry"
                fix_data["wait_seconds"] = 60 * attempt
                fixed = True
            else:
                # Unknown error - mark as unfixable
                fix_data["action"] = "manual_review_required"
                fixed = False

        return {
            "fixed": fixed,
            "fix_data": fix_data,
            "attempt": attempt
        }

    def _log_evolution(self, target: str, phase_num: str, fix_result: Dict, outcome: str):
        """Log healing attempt to evolution_log.json."""
        entry = {
            "timestamp": time.time(),
            "target": target,
            "phase": phase_num,
            "outcome": outcome,
            "fix_data": fix_result.get("fix_data", {}),
            "attempt": fix_result.get("attempt", 0)
        }
        try:
            if self.evolution_log.exists():
                with open(self.evolution_log, 'r') as f:
                    log = json.load(f)
            else:
                log = {"entries": []}
            log["entries"].append(entry)
            # Keep only last 500 entries to avoid file bloat
            if len(log["entries"]) > 500:
                log["entries"] = log["entries"][-500:]
            with open(self.evolution_log, 'w') as f:
                json.dump(log, f, indent=2)
        except Exception as e:
            logger.debug(f"Evolution log write failed: {e}")
