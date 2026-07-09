#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  API ROUTER — Hybrid AI Provider Selection with Key Rotation        █
█  Level 5: Increased token limit for Evo engines                   █
████████████████████████████████████████████████████████████████████████████
"""

import time
import json
import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger("ZeroRecon")

class AIRouter:
    """
    হাইব্রিড এআই রাউটার — কাজের জটিলতা ও প্রোভাইডারের লিমিট দেখে মডেল সিলেক্ট করে।
    Cerebras (Primary) + OpenRouter (Fallback) — একাধিক কী রোটেট করতে পারে।
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cerebras_keys = []          # একাধিক Cerebras কী (যদি থাকে)
        self.openrouter_keys = []        # একাধিক OpenRouter কী (যদি থাকে)
        self.blacklisted_keys = {}       # {key: unblock_time}
        self.last_request_time = 0
        self.cerebras_usage_today = 0
        self.openrouter_usage_today = 0
        
        # কনফিগ থেকে কী লোড করি
        self._load_keys()
        
        # লিমিট কনফিগ
        self.cerebras_limit_rpd = config.get("ai", {}).get("cerebras", {}).get("limits", {}).get("max_rpd", 2400)
        self.cerebras_limit_rpm = config.get("ai", {}).get("cerebras", {}).get("limits", {}).get("max_rpm", 5)
        self.openrouter_limit_rpd = config.get("ai", {}).get("openrouter", {}).get("limits", {}).get("max_rpd", 50)
        
        # Level 5: বড় প্রম্পটের জন্য টোকেন লিমিট বাড়ানো
        self.max_tokens_large = 8000   # MCTS, Debate, Mutator
        self.max_tokens_normal = 4000  # বাকি কাজ
        
        logger.info("🧠 AIRouter (Level 5) initialized with Cerebras + OpenRouter fallback")
    
    def _load_keys(self):
        """কনফিগ থেকে API Keys লোড করে — একাধিক কী সাপোর্ট করে"""
        # Cerebras
        c_key = self.config.get("ai", {}).get("cerebras", {}).get("api_key")
        if c_key and c_key != "YOUR_CEREBRAS_API_KEY":
            self.cerebras_keys.append({
                "key": c_key,
                "used_today": 0,
                "status": "active"
            })
        # OpenRouter
        o_key = self.config.get("ai", {}).get("openrouter", {}).get("api_key")
        if o_key and o_key != "YOUR_OPENROUTER_API_KEY":
            self.openrouter_keys.append({
                "key": o_key,
                "used_today": 0,
                "status": "active"
            })
        
        if not self.cerebras_keys and not self.openrouter_keys:
            logger.warning("⚠️ No valid API keys found. AI features will be limited.")
    
    def _get_complexity(self, task_type: str) -> str:
        """টাস্কের ধরণ দেখে জটিলতা লেভেল রিটার্ন করে"""
        high_tasks = ["planning", "analysis", "code_rewrite", "cert_chain", "supervisor_decision",
                      "mcts_path_gen", "debate_attacker", "debate_defender", "mutator_gen",
                      "attack_path_generation", "executive_summary_final", "asn_mapping_insights"]
        medium_tasks = ["subdomain_enum", "dns_parse", "github_dork", "asn_lookup", "permutation",
                        "pattern_learning", "permutation_filter", "historical_analysis"]
        low_tasks = ["validation", "formatting", "extract", "simple_check", "cert_analysis"]
        
        task_lower = task_type.lower()
        if any(t in task_lower for t in high_tasks):
            return "high"
        elif any(t in task_lower for t in medium_tasks):
            return "medium"
        else:
            return "low"
    
    def _get_available_key(self, keys: List[Dict]) -> Optional[Dict]:
        """সবচেয়ে কম ব্যবহৃত ও সক্রিয় কী বেছে নেয় (রাউন্ড-রবিন)"""
        active = [k for k in keys if k["status"] == "active"]
        if not active:
            return None
        available = [k for k in active if k["used_today"] < self.cerebras_limit_rpd]
        if not available:
            return None
        return min(available, key=lambda k: k["used_today"])
    
    def _call_cerebras(self, model: str, prompt: str, key_info: Dict, max_tokens: int) -> Optional[str]:
        """Cerebras API-তে কল করে — রেট লিমিট (৫ RPM) মেনে"""
        now = time.time()
        if now - self.last_request_time < 12:
            time.sleep(12 - (now - self.last_request_time))
        
        headers = {
            "Authorization": f"Bearer {key_info['key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        base_url = self.config.get("ai", {}).get("cerebras", {}).get("base_url", "https://api.cerebras.ai/v1/chat/completions")
        
        try:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30)
            self.last_request_time = time.time()
            key_info["used_today"] += 1
            self.cerebras_usage_today += 1
            
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                logger.warning("⚠️ Cerebras rate limit (429). Marking key as blocked.")
                self._blacklist_key(key_info["key"], provider="cerebras")
                return None
            else:
                logger.error(f"❌ Cerebras error {resp.status_code}: {resp.text[:100]}")
                return None
        except Exception as e:
            logger.error(f"❌ Cerebras connection error: {e}")
            return None
    
    def _call_openrouter(self, model: str, prompt: str, key_info: Dict, max_tokens: int) -> Optional[str]:
        """OpenRouter API-তে কল করে (ব্যাকআপ) — ৫০ RPD লিমিট মেনে"""
        if self.openrouter_usage_today >= self.openrouter_limit_rpd:
            logger.warning("⚠️ OpenRouter daily limit reached.")
            return None
        
        headers = {
            "Authorization": f"Bearer {key_info['key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }
        base_url = self.config.get("ai", {}).get("openrouter", {}).get("base_url", "https://openrouter.ai/api/v1/chat/completions")
        
        try:
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30)
            key_info["used_today"] += 1
            self.openrouter_usage_today += 1
            
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                logger.error(f"❌ OpenRouter error {resp.status_code}: {resp.text[:100]}")
                return None
        except Exception as e:
            logger.error(f"❌ OpenRouter error: {e}")
            return None
    
    def _blacklist_key(self, key: str, provider: str = "cerebras"):
        """একটি কী ব্ল্যাকলিস্ট করে (১ ঘন্টা)"""
        unblock_time = datetime.now() + timedelta(hours=1)
        self.blacklisted_keys[key] = unblock_time
        for k in self.cerebras_keys + self.openrouter_keys:
            if k["key"] == key:
                k["status"] = "blocked"
                break
    
    def route(self, task_type: str, prompt: str) -> Optional[str]:
        """মেইন রাউটিং ফাংশন — জটিলতা অনুযায়ী প্রোভাইডার ও মডেল নির্বাচন করে"""
        complexity = self._get_complexity(task_type)
        
        # Level 5: বড় কাজের জন্য টোকেন লিমিট বাড়ানো
        if task_type in ["mcts_path_gen", "debate_attacker", "debate_defender", "mutator_gen",
                         "attack_path_generation", "executive_summary_final"]:
            max_tokens = self.max_tokens_large
        else:
            max_tokens = self.max_tokens_normal
        
        # ১. Cerebras (Primary) চেষ্টা
        c_key = self._get_available_key(self.cerebras_keys)
        if c_key:
            c_model = self.config.get("ai", {}).get("cerebras", {}).get("models", {}).get(complexity, "gpt-oss-120b")
            logger.debug(f"🧠 Routing to Cerebras [{c_model}] for {task_type}")
            result = self._call_cerebras(c_model, prompt, c_key, max_tokens)
            if result is not None:
                return result
            else:
                logger.info(f"🔄 Cerebras failed, trying OpenRouter fallback...")
        
        # ২. OpenRouter (Fallback) চেষ্টা
        o_key = self._get_available_key(self.openrouter_keys)
        if o_key:
            o_model = self.config.get("ai", {}).get("openrouter", {}).get("fallback_models", {}).get(complexity, "nvidia/nemotron-3-ultra")
            logger.debug(f"🔄 Fallback to OpenRouter [{o_model}]")
            result = self._call_openrouter(o_model, prompt, o_key, max_tokens)
            if result is not None:
                return result
        
        logger.critical("🚨 All AI providers exhausted. No response.")
        return None
