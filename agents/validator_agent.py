#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validator Agent — Verifies data from all phases.
Deduplicates, checks schemas, and flags suspicious/missing data.
"""
import logging
from typing import Dict, Any, List, Set
from .base_agent import BaseAgent

logger = logging.getLogger("ZeroRecon")

class ValidatorAgent(BaseAgent):
    """সব ফেজের ডাটা যাচাই করে — ডুপ্লিকেট বাদ, স্কিমা চেক, খালি ডাটা ফ্ল্যাগ"""
    
    def __init__(self):
        super().__init__("ValidatorAgent")
        self.required_fields = {
            "phase_1": ["subdomains", "cert_info"],
            "phase_2": ["asn", "org", "prefixes"],
            "phase_3": ["repos", "secrets"],
            "phase_4": ["wayback_urls"],
            "phase_5": ["s3_buckets", "azure_storage"],
            "phase_6": ["permutations"],
            "phase_7": ["asn_mapping"],
            "phase_8": ["dns_results"],
            "phase_9": ["osint_data"],
            "phase_10": ["vulnerabilities"],
            "phase_11": ["attack_surface"],
            "phase_12": ["report"]
        }
    
    def run(self, target: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        self._log_start()
        
        if not context or "results" not in context:
            result = {"error": "No results to validate", "status": "failed"}
            self._log_error("No results provided")
            return result
        
        all_results = context.get("results", {})
        validated = {}
        errors = []
        warnings = []
        
        for phase_key, phase_data in all_results.items():
            # ফেজ নাম্বার বের করা (phase_1, phase_2 ...)
            phase_num = phase_key.replace("phase_", "")
            if not phase_num.isdigit():
                continue
            phase_num = int(phase_num)
            
            required = self.required_fields.get(f"phase_{phase_num}", [])
            
            if not phase_data:
                warnings.append(f"Phase {phase_num}: Empty data")
                validated[phase_key] = {"status": "empty", "data": {}}
                continue
            
            # ১. বেসিক ভ্যালিডেশন: ডাটা ডিকশনারি কিনা
            if not isinstance(phase_data, dict):
                errors.append(f"Phase {phase_num}: Data is not a dictionary")
                validated[phase_key] = {"status": "invalid_type", "data": phase_data}
                continue
            
            # ২. রিকোয়ার্ড ফিল্ড চেক
            missing_fields = []
            for field in required:
                if field not in phase_data:
                    missing_fields.append(field)
            
            if missing_fields:
                warnings.append(f"Phase {phase_num}: Missing fields: {missing_fields}")
            
            # ৩. ডুপ্লিকেট বাদ (যদি ডাটা লিস্ট হয়)
            cleaned_data = {}
            for key, value in phase_data.items():
                if isinstance(value, list):
                    # লিস্ট থেকে ডুপ্লিকেট বাদ
                    try:
                        if value and isinstance(value[0], str):
                            cleaned_data[key] = list(set(value))
                        else:
                            cleaned_data[key] = value
                    except:
                        cleaned_data[key] = value
                else:
                    cleaned_data[key] = value
            
            validated[phase_key] = {
                "status": "valid" if not missing_fields else "partial",
                "missing_fields": missing_fields,
                "data": cleaned_data,
                "item_count": sum(len(v) if isinstance(v, list) else 1 for v in cleaned_data.values())
            }
        
        result = {
            "target": target,
            "validated_phases": validated,
            "errors": errors,
            "warnings": warnings,
            "status": "complete"
        }
        
        self._log_complete(result)
        return result