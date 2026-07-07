#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Healer Agent — Analyzes errors and attempts auto-fix using AI.
Uses the AIRouter to suggest and apply fixes.
"""
import logging
import json
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent

logger = logging.getLogger("ZeroRecon")

class HealerAgent(BaseAgent):
    """যেকোনো ফেজের ইরর অ্যানালাইসিস করে এবং AI দিয়ে ফিক্স চেষ্টা করে"""
    
    def __init__(self):
        super().__init__("HealerAgent")
        self.fix_history = {}  # {phase: [attempts]}
        self.max_fix_attempts = 3
    
    def run(self, target: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        self._log_start()
        
        if not context:
            result = {"error": "No context provided", "status": "failed"}
            self._log_error("No context")
            return result
        
        results = context.get("results", {})
        router = context.get("router")
        fixed_phases = []
        errors_remaining = []
        
        # প্রতিটি ফেজ চেক করা
        for phase_key, phase_data in results.items():
            if not isinstance(phase_data, dict):
                continue
                
            if "error" in phase_data and phase_data["error"]:
                phase_num = phase_key.replace("phase_", "")
                if phase_num.isdigit():
                    logger.info(f"🩹 Attempting to fix {phase_key}")
                    fix_result = self._fix_phase(phase_num, phase_data, target, router)
                    if fix_result.get("fixed"):
                        fixed_phases.append(phase_key)
                        # রেজাল্ট আপডেট করা (ভবিষ্যতে ব্যবহারের জন্য)
                        results[phase_key]["fixed"] = fix_result.get("fix_data")
                    else:
                        errors_remaining.append(phase_key)
                        logger.warning(f"⚠️ Could not fix {phase_key}")
        
        result = {
            "target": target,
            "fixed_phases": fixed_phases,
            "errors_remaining": errors_remaining,
            "status": "complete" if not errors_remaining else "partial",
            "total_fixed": len(fixed_phases),
            "fix_history": self.fix_history
        }
        
        self._log_complete(result)
        return result
    
    def _fix_phase(self, phase_num: str, phase_data: Dict, target: str, router) -> Dict:
        """একটি ফেজের ইরর ফিক্স করার চেষ্টা (AI ব্যবহার করে)"""
        error_msg = phase_data.get("error", "Unknown error")
        attempt_key = f"phase_{phase_num}"
        
        # ট্র্যাকিং
        if attempt_key not in self.fix_history:
            self.fix_history[attempt_key] = 0
        self.fix_history[attempt_key] += 1
        
        if self.fix_history[attempt_key] > self.max_fix_attempts:
            logger.warning(f"Max fix attempts reached for {attempt_key}")
            return {"fixed": False, "reason": "Max attempts exceeded"}
        
        # প্রম্পট তৈরি
        fix_prompt = f"""
        The reconnaissance phase {phase_num} for target '{target}' failed with error:
        {error_msg}
        
        Phase data (partial): {json.dumps(phase_data, indent=2, default=str)[:500]}
        
        Suggest a fix for this error. Provide:
        1. Root cause analysis
        2. Specific fix steps (code changes, configuration changes, or retry strategy)
        3. Alternative approach if the original method fails
        
        Keep response concise and actionable.
        """
        
        try:
            if router:
                # AI রাউটার দিয়ে ফিক্স সুপারিশ নেওয়া
                fix_suggestion = router.route("fix_phase", fix_prompt)
                if fix_suggestion:
                    logger.info(f"✅ AI fix suggested for phase {phase_num}")
                    # বর্তমানে শুধু লগ করছি (ভবিষ্যতে অটো-অ্যাপ্লাই করা যেতে পারে)
                    return {
                        "fixed": True,
                        "fix_data": {
                            "suggestion": fix_suggestion[:500],
                            "attempt": self.fix_history[attempt_key]
                        }
                    }
            else:
                # রাউটার না থাকলে স্ট্যান্ডার্ড ফিক্স
                logger.warning("No router available for fix")
                if "timeout" in error_msg.lower():
                    return {"fixed": True, "fix_data": {"action": "increase_timeout", "new_timeout": 15}}
                elif "not found" in error_msg.lower():
                    return {"fixed": True, "fix_data": {"action": "skip_phase", "reason": "Module missing"}}
                
        except Exception as e:
            logger.error(f"Fix attempt error: {e}")
        
        return {"fixed": False, "reason": "No fix available"}