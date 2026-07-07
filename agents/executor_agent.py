#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Executor Agent — Orchestrates the 12 reconnaissance phases.
Runs phases sequentially or parallel (max 2 threads).
"""
import logging
import concurrent.futures
import importlib
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

logger = logging.getLogger("ZeroRecon")

class ExecutorAgent(BaseAgent):
    """১২টি রিকন ফেজ অর্কেস্ট্রেট করে — ম্যাক্স ২টি থ্রেড সমান্তরালে"""
    
    def __init__(self):
        super().__init__("ExecutorAgent")
        self.phases = list(range(1, 13))  # 1 to 12
        self.max_parallel = 2
        self.results = {}
    
    def run(self, target: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        self._log_start()
        
        # কনটেক্সট থেকে রাউটার নেওয়া
        router = context.get("router") if context else None
        config = context.get("config") if context else None
        
        logger.info(f"🚀 Executing {len(self.phases)} phases for {target} (max {self.max_parallel} parallel)")
        
        # Sequential execution (কোড সিম্পল রাখার জন্য)
        for phase_num in self.phases:
            phase_result = self._run_single_phase(phase_num, target, router, config)
            self.results[f"phase_{phase_num}"] = phase_result
            
            # যদি কোনো ফেজ মারাত্মকভাবে ব্যর্থ হয়, থামি না — শুধু লগ করি
            if phase_result.get("error"):
                logger.warning(f"⚠️ Phase {phase_num} had errors: {phase_result['error']}")
        
        self._log_complete(self.results)
        return self.results
    
    def _run_single_phase(self, phase_num: int, target: str, router=None, config=None) -> Dict:
        """একটি নির্দিষ্ট ফেজ ডায়নামিক ইম্পোর্ট করে চালায়"""
        phase_name = f"phase{phase_num}"
        
        # ফাইল নাম তৈরি
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
            12: "phase12_report"
        }
        
        module_name = phase_files.get(phase_num, f"phase{phase_num}")
        
        try:
            # ডায়নামিক ইম্পোর্ট: agents.recon.phase1_cert_subdomain
            full_module = f"agents.recon.{module_name}"
            module = importlib.import_module(full_module)
            
            # 'run' ফাংশন খোঁজা
            if hasattr(module, "run"):
                run_func = getattr(module, "run")
                # কনটেক্সট পাস করা
                phase_context = {
                    "target": target,
                    "router": router,
                    "config": config,
                    "previous_results": self.results
                }
                result = run_func(target, phase_context)
                logger.info(f"✅ Phase {phase_num} completed")
                return result
            else:
                error_msg = f"Phase {phase_num} module has no 'run' function"
                logger.warning(error_msg)
                return {"error": error_msg}
                
        except ImportError as e:
            error_msg = f"Module not found: {module_name} — {e}"
            logger.warning(error_msg)
            return {"error": error_msg, "skipped": True}
        except Exception as e:
            error_msg = f"Phase {phase_num} execution error: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def run_parallel(self, target: str, context: Optional[Dict] = None) -> Dict:
        """(ভবিষ্যতে) সমান্তরালে ফেজ চালানোর জন্য — বর্তমানে ব্যবহার করছি না"""
        # এই মেথডটি বর্তমানে ডিজেবল রাখা হয়েছে
        return self.run(target, context)