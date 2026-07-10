#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 EXECUTOR AGENT (Level 5 — God-Tier Orchestrator v2.0)
- Dynamic Phase Discovery (no hardcoded mapping)
- Parallel Execution (ThreadPoolExecutor, max 2)
- Intelligent Retry (2 attempts for transient errors)
- MCTS Priority Scheduling (run priority phases first)
- Performance Logging (time per phase)
- Graceful Degradation (if a phase fails, continues with others)
"""

import os
import re
import time
import logging
import importlib
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .base_agent import BaseAgent

logger = logging.getLogger("ZeroRecon")

class ExecutorAgent(BaseAgent):
    def __init__(self):
        super().__init__("ExecutorAgent")
        self.max_parallel = 2
        self.results = {}
        self._phase_cache = None

    def _discover_phases(self) -> Dict[int, str]:
        """
        Dynamically scan agents/recon/ directory to discover phase files.
        Returns: {1: "phase1_cert_subdomain", 2: "phase2_asn", ...}
        """
        if self._phase_cache is not None:
            return self._phase_cache

        phase_map = {}
        recon_dir = Path(__file__).parent / "recon"
        
        if not recon_dir.exists():
            logger.error("❌ Recon directory not found!")
            return {}

        for py_file in recon_dir.glob("phase*.py"):
            filename = py_file.stem  # phase1_cert_subdomain
            # Extract the number using regex
            match = re.match(r'phase(\d+)', filename)
            if match:
                phase_num = int(match.group(1))
                phase_map[phase_num] = filename

        if not phase_map:
            logger.warning("⚠️ No phase files found in agents/recon/.")
        else:
            logger.info(f"🔍 Discovered {len(phase_map)} phases: {sorted(phase_map.keys())}")

        self._phase_cache = phase_map
        return phase_map

    def run(self, target: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        self._log_start()
        router = context.get("router") if context else None
        config = context.get("config") if context else None
        mcts_path = context.get("mcts_path", {})
        debate_rules = context.get("debate_rules", {})
        dna = context.get("dna")

        # 1. Discover available phases
        phase_map = self._discover_phases()
        if not phase_map:
            self._log_error("No phases discovered. Aborting execution.")
            return {"error": "No phases found"}

        # 2. Determine execution order (MCTS priority)
        priority_phases = mcts_path.get("metadata", {}).get("priority_phases", [])
        available_nums = sorted(phase_map.keys())
        
        # Start with priority phases (if they exist), then append the rest
        ordered_phases = []
        for p in priority_phases:
            if p in phase_map and p not in ordered_phases:
                ordered_phases.append(p)
        for p in available_nums:
            if p not in ordered_phases:
                ordered_phases.append(p)

        logger.info(f"🚀 Executing {len(ordered_phases)} phases for {target} (MCTS Priority: {bool(priority_phases)})")
        if debate_rules.get("verdict") == "BLOCKED":
            logger.warning("⚠️ Global Debate verdict: BLOCKED. Some phases may skip automatically.")

        # 3. Prepare context for all phases
        base_context = {
            "target": target,
            "router": router,
            "config": config,
            "mcts_path": mcts_path,
            "debate_rules": debate_rules,
            "dna": dna,
            "previous_results": self.results  # Will be updated in real-time
        }

        # 4. Execute phases in parallel (max self.max_parallel)
        phase_times = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            future_to_phase = {}
            
            # Submit all tasks
            for phase_num in ordered_phases:
                phase_name = phase_map.get(phase_num, f"phase{phase_num}")
                # Copy context to avoid cross-phase contamination, but keep reference to results
                phase_context = base_context.copy()
                phase_context["phase_name"] = phase_name
                phase_context["phase_num"] = phase_num
                
                future = executor.submit(
                    self._run_phase_with_retry, 
                    phase_num, 
                    phase_name, 
                    target, 
                    phase_context
                )
                future_to_phase[future] = phase_num

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_phase):
                phase_num = future_to_phase[future]
                try:
                    phase_result, elapsed = future.result(timeout=120)  # 2 min timeout per phase
                    phase_times[phase_num] = elapsed
                    self.results[f"phase_{phase_num}"] = phase_result
                    
                    if phase_result.get("error"):
                        logger.warning(f"⚠️ Phase {phase_num} completed with errors: {phase_result['error']}")
                    elif phase_result.get("status") == "skipped":
                        logger.info(f"⏭️ Phase {phase_num} skipped: {phase_result.get('reason', 'No reason')}")
                    else:
                        logger.info(f"✅ Phase {phase_num} completed in {elapsed:.2f}s")
                        
                except concurrent.futures.TimeoutError:
                    logger.error(f"❌ Phase {phase_num} timed out (120s). Skipping.")
                    self.results[f"phase_{phase_num}"] = {"error": "Timeout", "skipped": True}
                except Exception as e:
                    logger.error(f"❌ Phase {phase_num} crashed: {e}")
                    self.results[f"phase_{phase_num}"] = {"error": str(e), "skipped": True}

        # 5. Log summary
        total_time = sum(phase_times.values())
        logger.info(f"📊 Phase execution summary: {len(phase_times)} phases completed in {total_time:.2f}s total.")
        
        self._log_complete(self.results)
        return self.results

    def _run_phase_with_retry(self, phase_num: int, phase_name: str, target: str, context: Dict) -> Tuple[Dict, float]:
        """
        Run a single phase with intelligent retry (2 attempts for transient errors).
        Returns: (result_dict, elapsed_time)
        """
        max_attempts = 2
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                start_time = time.time()
                result = self._run_single_phase(phase_num, phase_name, target, context)
                elapsed = time.time() - start_time
                
                # If success, return immediately
                if not result.get("error"):
                    return result, elapsed
                
                # If it's a transient error (timeout/connection), retry
                error_msg = str(result.get("error", "")).lower()
                if "timeout" in error_msg or "connection" in error_msg or "rate" in error_msg:
                    last_error = result
                    logger.warning(f"🔄 Retrying Phase {phase_num} (attempt {attempt+1}/{max_attempts}) due to transient error.")
                    time.sleep(2 ** attempt)  # 1s, 2s backoff
                    continue
                else:
                    # Non-transient error, return immediately
                    return result, elapsed
                    
            except Exception as e:
                last_error = {"error": str(e)}
                if attempt < max_attempts - 1:
                    logger.warning(f"🔄 Retrying Phase {phase_num} (attempt {attempt+1}/{max_attempts}) due to exception: {e}")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return last_error, time.time() - start_time
        
        # If all attempts failed
        return last_error or {"error": "Max retries exceeded"}, elapsed

    def _run_single_phase(self, phase_num: int, phase_name: str, target: str, context: Dict) -> Dict:
        """Dynamically import and run a single phase."""
        try:
            full_module = f"agents.recon.{phase_name}"
            module = importlib.import_module(full_module)
            
            if not hasattr(module, "run"):
                return {"error": f"Module '{phase_name}' has no 'run' function", "skipped": True}
            
            run_func = getattr(module, "run")
            # Pass the context to the phase
            return run_func(target, context)
            
        except ImportError as e:
            logger.warning(f"Phase {phase_num} module not found: {e}")
            return {"error": f"Module not found: {phase_name}", "skipped": True}
        except Exception as e:
            logger.error(f"Phase {phase_num} execution error: {e}")
            return {"error": str(e), "skipped": True}
