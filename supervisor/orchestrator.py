#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 SUPERVISOR ORCHESTRATOR (Level 5 — God-Tier Evo Integration)
- Initializes DNA, MCTS, Mutator, Debate, and Reflector engines.
- Runs MCTS search to find the best reconnaissance path.
- Passes MCTS result, Debate verdict, and DNA to the Executor.
- After all phases, runs Reflector to update DNA with learnings.
- Integrates health monitor and checkpoint system.
"""

import os
import sys
import json
import time
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Evo imports
from evo.dna import DNA
from evo.mcts import MCTS
from evo.mutator import Mutator
from evo.debate import DebateEngine
from evo.reflector import Reflector

# Supervisor imports
from .api_router import AIRouter
from .context_manager import ContextManager
from .health_monitor import HealthMonitor

logger = logging.getLogger("ZeroRecon")

class SupervisorOrchestrator:
    """
    Level 5 Supervisor — Master Orchestrator with Evo Intelligence.
    """

    def __init__(
        self,
        target: str,
        config: Dict[str, Any],
        auto_install: bool = False,
        resume_session: Optional[str] = None,
        phases_to_run: Optional[str] = None
    ):
        self.target = target
        self.config = config
        self.auto_install = auto_install
        self.resume_session = resume_session
        self.phases_to_run = self._parse_phases(phases_to_run)

        # Directories
        self.output_dir = Path(config.get("output_dir", "outputs"))
        self.state_dir = Path(config.get("state_dir", "state"))
        self.reports_dir = self.output_dir / "reports"
        self.logs_dir = self.output_dir / "logs"
        self.cache_dir = self.state_dir / "cache"
        self.checkpoint_dir = self.state_dir / "checkpoint"

        for d in [self.output_dir, self.state_dir, self.reports_dir,
                  self.logs_dir, self.cache_dir, self.checkpoint_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Core components
        self.router = AIRouter(config)
        self.context_manager = ContextManager()
        self.health_monitor = HealthMonitor()

        # ================================================================
        # 🧬 EVO ENGINES (Level 5)
        # ================================================================
        self.dna = DNA(state_dir=self.state_dir / "dna")
        self.mcts = MCTS(config, self.dna, self.router)
        self.mutator = Mutator(config, self.dna, self.router)
        self.debate = DebateEngine(config, self.router)
        self.reflector = Reflector(config, self.dna)

        # State
        self.results = {}
        self.current_phase = 0
        self.start_time = None
        self.mcts_result = None
        self.debate_rules = {"verdict": "APPROVED", "flaws": []}
        self.checkpoint_file = self.checkpoint_dir / f"session_{self.target}_{datetime.now().strftime('%Y%m%d')}.json"

        logger.info(f"🦅 SupervisorOrchestrator (Level 5) initialized for: {target}")

    def _parse_phases(self, phases_str: Optional[str]) -> List[int]:
        if not phases_str:
            return list(range(1, 16))
        try:
            return [int(p.strip()) for p in phases_str.split(",") if p.strip().isdigit()]
        except:
            logger.warning("⚠️ Invalid --phases format. Running all phases.")
            return list(range(1, 16))

    def run(self) -> Dict[str, Any]:
        """Main execution — ARTEMIS-style loop with Evo intelligence."""
        self.start_time = datetime.now()
        logger.info(f"🔥 Mission started for {self.target}")

        # Health check
        if not self.health_monitor.check_system_health():
            logger.critical("❌ System health check failed. Aborting.")
            return {}

        # Resume checkpoint if provided
        if self.resume_session:
            self._load_checkpoint(self.resume_session)

        # ================================================================
        # 🧠 PHASE 0: MCTS Search & Path Planning
        # ================================================================
        # Gather basic passive data for MCTS
        passive_data = {
            "target": self.target,
            "domain": self.target,
            "timestamp": datetime.now().isoformat()
        }

        logger.info("🧠 Running MCTS search for optimal reconnaissance path...")
        self.mcts_result = self.mcts.search(self.target, passive_data)
        logger.info(f"✅ MCTS selected: {self.mcts_result.get('selected')} (confidence: {self.mcts_result.get('confidence', 0):.2f})")

        # ================================================================
        # 🧬 PHASE 0.5: Mutator — Generate Custom Rules
        # ================================================================
        mutator_rules = self.mutator.generate_rules(
            self.target,
            self.mcts_result,
            passive_data
        )
        logger.info(f"🧬 Mutator generated {mutator_rules.get('count', 0)} custom rules.")

        # ================================================================
        # ⚖️ PHASE 0.6: Debate — Validate Rules
        # ================================================================
        if mutator_rules.get("rules"):
            debate_result = self.debate.run_debate(self.target, mutator_rules.get("rules", []))
            self.debate_rules = {
                "verdict": debate_result.get("verdict", "APPROVED"),
                "flaws": debate_result.get("flaws", [])
            }
            logger.info(f"⚖️ Debate verdict: {self.debate_rules['verdict']}")
        else:
            self.debate_rules = {"verdict": "APPROVED", "flaws": []}

        # ================================================================
        # 🚀 EXECUTION: Run all phases with Evo context
        # ================================================================
        for phase_num in self.phases_to_run:
            self.current_phase = phase_num
            logger.info(f"📡 Phase {phase_num} started")

            try:
                phase_result = self._run_phase(phase_num)
                self.results[f"phase_{phase_num}"] = phase_result
                self._save_checkpoint()

                if not self.health_monitor.is_healthy():
                    logger.warning("⚠️ Health monitor triggered recovery. Pausing briefly.")
                    time.sleep(5)

            except Exception as e:
                logger.error(f"❌ Phase {phase_num} failed: {e}")
                logger.debug(traceback.format_exc())
                self.results[f"phase_{phase_num}"] = {"error": str(e)}
                continue

        # ================================================================
        # 🧠 FINAL: Reflector — Update DNA with learnings
        # ================================================================
        logger.info("🔄 Running Reflector to update DNA...")
        reflection = self.reflector.reflect(
            self.target,
            mutator_rules.get("rules", []),
            self.results,
            self.mcts_result
        )
        logger.info(f"✅ Reflector: {reflection.get('insights', ['No insights'])[0]}")

        # ================================================================
        # 📊 REPORT: Generate final report
        # ================================================================
        report = self._generate_report()
        self._save_report(report)
        self._cleanup()

        logger.info(f"✅ Mission completed in {(datetime.now() - self.start_time).total_seconds():.2f}s")
        return report

    def _run_phase(self, phase_num: int) -> Dict[str, Any]:
        """Run a single phase with full Evo context."""
        phase_module = f"agents.recon.phase{phase_num}"
        try:
            module = __import__(phase_module, fromlist=["run"])
            run_func = getattr(module, "run")

            phase_context = {
                "target": self.target,
                "router": self.router,
                "config": self.config,
                "previous_results": self.results,
                "mcts_path": self.mcts_result,
                "debate_rules": self.debate_rules,
                "dna": self.dna,
                "mutator_rules": self.mutator.generate_rules(
                    self.target,
                    self.mcts_result,
                    {"target": self.target}
                )
            }

            result = run_func(self.target, phase_context)
            return result

        except ImportError as e:
            logger.warning(f"⚠️ Phase {phase_num} module not found: {e}")
            return {"error": f"Module not found: {e}", "skipped": True}
        except Exception as e:
            logger.error(f"❌ Phase {phase_num} execution error: {e}")
            return {"error": str(e)}

    def _save_checkpoint(self):
        """Save current progress to checkpoint file."""
        checkpoint_data = {
            "target": self.target,
            "current_phase": self.current_phase,
            "results": self.results,
            "mcts_result": self.mcts_result,
            "debate_rules": self.debate_rules,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            logger.debug(f"💾 Checkpoint saved: {self.checkpoint_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save checkpoint: {e}")

    def _load_checkpoint(self, session_id: str):
        """Load previous session from checkpoint."""
        checkpoint_path = self.checkpoint_dir / f"session_{session_id}.json"
        if not checkpoint_path.exists():
            logger.warning(f"⚠️ Checkpoint {checkpoint_path} not found. Starting fresh.")
            return
        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            self.results = data.get("results", {})
            self.current_phase = data.get("current_phase", 0)
            self.mcts_result = data.get("mcts_result")
            self.debate_rules = data.get("debate_rules", {"verdict": "APPROVED", "flaws": []})
            logger.info(f"✅ Resumed from checkpoint: phase {self.current_phase}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load checkpoint: {e}")

    def _generate_report(self) -> Dict[str, Any]:
        """Generate final report with Evo metadata."""
        return {
            "target": self.target,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "results": self.results,
            "evo_meta": {
                "mcts": self.mcts_result,
                "debate": self.debate_rules,
                "dna_stats": self.dna.get_stats()
            },
            "config_summary": {
                "phases_run": self.phases_to_run,
                "auto_install": self.auto_install
            }
        }

    def _save_report(self, report: Dict[str, Any]):
        """Save report in JSON and HTML formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.reports_dir / f"report_{self.target}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"📄 JSON report saved: {json_file}")

        html_file = self.reports_dir / f"report_{self.target}_{timestamp}.html"
        self._generate_html_report(report, html_file)

    def _generate_html_report(self, report: Dict[str, Any], html_path: Path):
        """Generate simple HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head><title>Zero Recon Report: {self.target}</title>
<style>
body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
h1 {{ color: #4fc3f7; }}
h2 {{ color: #81c784; }}
pre {{ background: #2d2d2d; padding: 15px; border-radius: 5px; overflow-x: auto; }}
.evo {{ color: #f8a4a4; }}
</style>
</head>
<body>
<h1>🔍 Zero Recon Report (Level 5)</h1>
<p><strong>Target:</strong> {self.target}</p>
<p><strong>Start:</strong> {report.get('start_time')}</p>
<p><strong>End:</strong> {report.get('end_time')}</p>
<p><strong>Duration:</strong> {report.get('duration_seconds', 0):.2f}s</p>
<h2>🧠 Evo Meta</h2>
<pre>{json.dumps(report.get('evo_meta', {}), indent=2, default=str)}</pre>
<h2>📊 Results by Phase</h2>
<pre>{json.dumps(report.get('results', {}), indent=2, default=str)}</pre>
</body>
</html>
        """
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"📄 HTML report saved: {html_path}")

    def _cleanup(self):
        """Clean up resources."""
        logger.debug("🧹 Cleanup complete.")
