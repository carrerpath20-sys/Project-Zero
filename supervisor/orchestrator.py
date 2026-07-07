#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  SUPERVISOR ORCHESTRATOR — ARTEMIS-Style Master Loop                 █
█  - Manages the entire reconnaissance pipeline                       █
█  - Spawns sub-agents (max 2 parallel)                             █
█  - Calls tools via api_router                                     █
█  - Handles state, checkpoints, and error recovery                 █
████████████████████████████████████████████████████████████████████████████
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

from .api_router import AIRouter
from .context_manager import ContextManager
from .health_monitor import HealthMonitor

logger = logging.getLogger("ZeroRecon")

class SupervisorOrchestrator:
    """
    ARTEMIS-স্টাইল সুপারভাইজার — এটি পুরো মিশনের 'মস্তিষ্ক'।
    ফেজগুলো অর্কেস্ট্রেট করে, এজেন্ট স্পন করে, এবং রেজাল্ট সংগ্রহ করে।
    """
    
    def __init__(self, target: str, config: Dict[str, Any], auto_install: bool = False,
                 resume_session: Optional[str] = None, phases_to_run: Optional[str] = None):
        self.target = target
        self.config = config
        self.auto_install = auto_install
        self.resume_session = resume_session
        self.phases_to_run = self._parse_phases(phases_to_run)
        
        # ডিরেক্টরি সেটআপ
        self.output_dir = Path(config.get("output_dir", "outputs"))
        self.state_dir = Path(config.get("state_dir", "state"))
        self.reports_dir = self.output_dir / "reports"
        self.logs_dir = self.output_dir / "logs"
        self.cache_dir = self.state_dir / "cache"
        self.checkpoint_dir = self.state_dir / "checkpoint"
        
        for d in [self.output_dir, self.state_dir, self.reports_dir, self.logs_dir, 
                  self.cache_dir, self.checkpoint_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # AI রাউটার
        self.router = AIRouter(config)
        self.context_manager = ContextManager()
        self.health_monitor = HealthMonitor()
        
        # স্টেট
        self.results = {}
        self.current_phase = 0
        self.start_time = None
        self.active_agents = []
        self.checkpoint_file = self.checkpoint_dir / f"session_{self.target}_{datetime.now().strftime('%Y%m%d')}.json"
        
        logger.info(f"🦅 SupervisorOrchestrator initialized for target: {target}")
    
    def _parse_phases(self, phases_str: Optional[str]) -> List[int]:
        """--phases আর্গুমেন্ট থেকে ফেজ লিস্ট তৈরি করে"""
        if not phases_str:
            return list(range(1, 13))  # ১ থেকে ১২ পর্যন্ত
        try:
            return [int(p.strip()) for p in phases_str.split(",") if p.strip().isdigit()]
        except:
            logger.warning("⚠️ Invalid --phases format. Running all phases.")
            return list(range(1, 13))
    
    def run(self) -> Dict[str, Any]:
        """মেইন মিশন এক্সিকিউশন — ARTEMIS-স্টাইল লুপ"""
        self.start_time = datetime.now()
        logger.info(f"🔥 Mission started for {self.target}")
        
        # ১. ইন্টিগ্রিটি চেক (Health Monitor)
        if not self.health_monitor.check_system_health():
            logger.critical("❌ System health check failed. Aborting.")
            return {}
        
        # ২. রেজিউম চেক (যদি resume session দেওয়া থাকে)
        if self.resume_session:
            self._load_checkpoint(self.resume_session)
        
        # ৩. রিকন ফেজগুলো চালানো
        for phase_num in self.phases_to_run:
            self.current_phase = phase_num
            logger.info(f"📡 Phase {phase_num} started")
            
            try:
                # ফেজ এক্সিকিউট
                phase_result = self._run_phase(phase_num)
                self.results[f"phase_{phase_num}"] = phase_result
                
                # চেকপয়েন্ট সেভ
                self._save_checkpoint()
                
                # হেলথ মনিটর চেক
                if not self.health_monitor.is_healthy():
                    logger.warning("⚠️ Health monitor triggered recovery. Pausing briefly.")
                    time.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Phase {phase_num} failed with error: {e}")
                logger.debug(traceback.format_exc())
                # হিলার এজেন্ট ট্রিগার করো (বর্তমানে শুধু লগ)
                self.results[f"phase_{phase_num}"] = {"error": str(e)}
                # থামো না — পরবর্তী ফেজে চলে যাও
                continue
        
        # ৪. ফাইনাল রিপোর্ট
        report = self._generate_report()
        self._save_report(report)
        
        # ৫. ক্লিনআপ
        self._cleanup()
        
        logger.info(f"✅ Mission completed in {(datetime.now() - self.start_time).total_seconds():.2f}s")
        return report
    
    def _run_phase(self, phase_num: int) -> Dict[str, Any]:
        """একটি নির্দিষ্ট ফেজ চালানো — ডায়নামিক ইম্পোর্ট করে"""
        phase_module = f"agents.recon.phase{phase_num}"
        try:
            # ডায়নামিক ইম্পোর্ট
            module = __import__(phase_module, fromlist=["run"])
            run_func = getattr(module, "run")
            # প্রতিটি ফেজের run(target, router, config) সিগনেচার আছে
            result = run_func(self.target, self.router, self.config)
            return result
        except ImportError as e:
            logger.warning(f"⚠️ Phase {phase_num} module not found: {e}")
            return {"error": f"Module not found: {e}"}
        except Exception as e:
            logger.error(f"❌ Phase {phase_num} execution error: {e}")
            return {"error": str(e)}
    
    def _save_checkpoint(self):
        """বর্তমান অগ্রগতি চেকপয়েন্ট ফাইলে সেভ করে"""
        checkpoint_data = {
            "target": self.target,
            "current_phase": self.current_phase,
            "results": self.results,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            logger.debug(f"💾 Checkpoint saved: {self.checkpoint_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save checkpoint: {e}")
    
    def _load_checkpoint(self, session_id: str):
        """আগের সেশন থেকে চেকপয়েন্ট লোড করে"""
        # session_id থেকে ফাইল পাথ তৈরি
        checkpoint_path = self.checkpoint_dir / f"session_{session_id}.json"
        if not checkpoint_path.exists():
            logger.warning(f"⚠️ Checkpoint {checkpoint_path} not found. Starting fresh.")
            return
        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            self.results = data.get("results", {})
            self.current_phase = data.get("current_phase", 0)
            logger.info(f"✅ Resumed from checkpoint: phase {self.current_phase}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load checkpoint: {e}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """ফাইনাল রিপোর্ট তৈরি — সব ফেজের ডাটা একত্রিত করে"""
        report = {
            "target": self.target,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "results": self.results,
            "config_summary": {
                "phases_run": self.phases_to_run,
                "auto_install": self.auto_install
            }
        }
        return report
    
    def _save_report(self, report: Dict[str, Any]):
        """রিপোর্ট JSON এবং HTML আকারে সেভ করে"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.reports_dir / f"report_{self.target}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"📄 JSON report saved: {json_file}")
        
        # HTML রিপোর্ট (সহজ টেমপ্লেট)
        html_file = self.reports_dir / f"report_{self.target}_{timestamp}.html"
        self._generate_html_report(report, html_file)
    
    def _generate_html_report(self, report: Dict[str, Any], html_path: Path):
        """সহজ HTML রিপোর্ট তৈরি (Markdown-স্টাইল)"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head><title>Zero Recon Report: {self.target}</title>
<style>
body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
h1 {{ color: #4fc3f7; }}
h2 {{ color: #81c784; }}
pre {{ background: #2d2d2d; padding: 15px; border-radius: 5px; overflow-x: auto; }}
</style>
</head>
<body>
<h1>🔍 Zero Recon Report</h1>
<p><strong>Target:</strong> {self.target}</p>
<p><strong>Start:</strong> {report.get('start_time')}</p>
<p><strong>End:</strong> {report.get('end_time')}</p>
<p><strong>Duration:</strong> {report.get('duration_seconds', 0):.2f}s</p>
<h2>Results by Phase</h2>
<pre>{json.dumps(report.get('results', {}), indent=2, default=str)}</pre>
</body>
</html>
        """
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"📄 HTML report saved: {html_path}")
    
    def _cleanup(self):
        """থ্রেড ও রিসোর্স ক্লিনআপ"""
        # (বর্তমানে কোনো থ্রেড নেই, কিন্তু ভবিষ্যতে এজেন্ট ক্লিনআপ এখানে হবে)
        logger.debug("🧹 Cleanup complete.")