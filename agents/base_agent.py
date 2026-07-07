#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Agent — Abstract interface for all sub-agents.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ZeroRecon")

class BaseAgent:
    """সকল এজেন্টের জন্য বেস ক্লাস — run(), validate(), rollback() মেথড আবশ্যক"""
    
    def __init__(self, name: str):
        self.name = name
        self.results = {}
        self.errors = []
        self.status = "idle"  # idle | running | completed | failed
    
    def run(self, target: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """প্রধান কাজ — প্রতিটি সাব-এজেন্টকে ওভাররাইড করতে হবে"""
        raise NotImplementedError(f"{self.name}.run() must be overridden")
    
    def validate(self, data: Dict) -> bool:
        """আউটপুট ডাটা যাচাই করে (যদি প্রয়োজন হয়)"""
        return True
    
    def rollback(self) -> bool:
        """পূর্ববর্তী নিরাপদ অবস্থায় ফিরে যেতে (যদি প্রযোজ্য)"""
        return True
    
    def _log_start(self):
        logger.info(f"🚀 {self.name} started")
        self.status = "running"
    
    def _log_complete(self, result: Dict):
        logger.info(f"✅ {self.name} completed")
        self.status = "completed"
        self.results = result
    
    def _log_error(self, error: str):
        logger.error(f"❌ {self.name} error: {error}")
        self.status = "failed"
        self.errors.append(error)