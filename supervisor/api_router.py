#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  API ROUTER — Level 6: God-Orchestrator                              █
█  Hybrid AI Provider Selection with Parallel Execution, Performance   █
█  Tracking, Adaptive Downgrade, and Smart Retry.                    █
████████████████████████████████████████████████████████████████████████████
"""

import time
import json
import logging
import random
import requests
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("ZeroRecon")

class AIRouter:
    """
    Level 6: Super-Intelligent AI Router with:
    - Complexity-based routing (high/medium/low)
    - Key rotation (multiple keys per provider)
    - Parallel requests for critical tasks
    - Performance tracking & adaptive selection
    - Smart retry with exponential backoff + jitter
    - Context length awareness
    - Response validation & automatic fallback
    """

    CONTEXT_LIMITS = {
        "gpt-oss-120b": 65000,
        "gemma-4-31b": 65000,
        "zai-glm-4.7": 8192,
        "nvidia/nemotron-3-ultra": 1000000,
        "openai/gpt-oss-120b": 65000,
        "google/gemma-4-26b-a4b-it": 256000,
        "nvidia/nemotron-3-super": 1000000,
        "poolside/laguna-m.1": 256000,
        "default": 16000
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cerebras_keys = []
        self.openrouter_keys = []
        self.blacklisted_keys = {}
        self.last_request_time = 0
        self.cerebras_usage_today = 0
        self.openrouter_usage_today = 0
        
        self.performance = {}
        
        self._load_keys()
        
        # 🔥 সব জায়গায় or {} ব্যবহার করে None হ্যান্ডেল করা হয়েছে
        cerebras_config = config.get("ai", {}).get("cerebras") or {}
        openrouter_config = config.get("ai", {}).get("openrouter") or {}
        
        self.cerebras_limit_rpd = cerebras_config.get("limits", {}).get("max_rpd", 2400)
        self.cerebras_limit_rpm = cerebras_config.get("limits", {}).get("max_rpm", 5)
        self.openrouter_limit_rpd = openrouter_config.get("limits", {}).get("max_rpd", 50)
        
        self.max_tokens_large = 8000
        self.max_tokens_normal = 4000
        
        self.parallel_tasks = ["mcts_path_gen", "debate_attacker", "debate_defender", "mutator_gen"]
        
        logger.info("🧠 AIRouter (Level 6) initialized with parallel execution & adaptive intelligence.")

    def _load_keys(self):
        """কনফিগ থেকে API Keys লোড করে — একাধিক কী সাপোর্ট করে"""
        ai_config = self.config.get("ai") or {}
        
        cerebras_config = ai_config.get("cerebras") or {}
        c_key = cerebras_config.get("api_key")
        if c_key and c_key != "YOUR_CEREBRAS_API_KEY":
            self.cerebras_keys.append({"key": c_key, "used_today": 0, "status": "active"})
        
        openrouter_config = ai_config.get("openrouter") or {}
        o_key = openrouter_config.get("api_key")
        if o_key and o_key != "YOUR_OPENROUTER_API_KEY":
            self.openrouter_keys.append({"key": o_key, "used_today": 0, "status": "active"})
        
        if not self.cerebras_keys and not self.openrouter_keys:
            logger.warning("⚠️ No valid API keys found. AI features will be limited.")

    def _get_complexity(self, task_type: str) -> str:
        high_tasks = ["planning", "analysis", "code_rewrite", "cert_chain", "supervisor_decision",
                      "mcts_path_gen", "debate_attacker", "debate_defender", "mutator_gen",
                      "attack_path_generation", "executive_summary_final", "asn_mapping_insights"]
        medium_tasks = ["subdomain_enum", "dns_parse", "github_dork", "asn_lookup", "permutation",
                        "pattern_learning", "permutation_filter", "historical_analysis"]
        task_lower = task_type.lower()
        if any(t in task_lower for t in high_tasks): return "high"
        elif any(t in task_lower for t in medium_tasks): return "medium"
        else: return "low"

    def _get_available_key(self, keys: List[Dict]) -> Optional[Dict]:
        active = [k for k in keys if k["status"] == "active"]
        if not active: return None
        available = [k for k in active if k["used_today"] < self.cerebras_limit_rpd]
        if not available: return None
        return min(available, key=lambda k: k["used_today"])

    def _estimate_tokens(self, prompt: str) -> int:
        return len(prompt) // 4

    def _call_api(self, provider: str, model: str, prompt: str, key_info: Dict, max_tokens: int) -> Optional[str]:
        start_time = time.time()
        result = None
        try:
            if provider == "cerebras":
                result = self._call_cerebras(model, prompt, key_info, max_tokens)
            else:
                result = self._call_openrouter(model, prompt, key_info, max_tokens)
        except Exception as e:
            logger.error(f"❌ {provider} call error: {e}")
        latency = time.time() - start_time
        key = (provider, model)
        if key not in self.performance:
            self.performance[key] = {"success": 0, "fail": 0, "avg_latency": 0.0, "count": 0}
        if result is not None:
            self.performance[key]["success"] += 1
            self.performance[key]["avg_latency"] = (self.performance[key]["avg_latency"] * self.performance[key]["count"] + latency) / (self.performance[key]["count"] + 1)
            self.performance[key]["count"] += 1
        else:
            self.performance[key]["fail"] += 1
        return result

    def route(self, task_type: str, prompt: str) -> Optional[str]:
        complexity = self._get_complexity(task_type)
        max_tokens = self.max_tokens_large if task_type in ["mcts_path_gen", "debate_attacker", "debate_defender", "mutator_gen", "attack_path_generation", "executive_summary_final"] else self.max_tokens_normal

        best_provider = self._get_best_provider(complexity, prompt)
        if best_provider:
            if best_provider == "cerebras":
                c_key = self._get_available_key(self.cerebras_keys)
                if c_key:
                    models = self.config.get("ai", {}).get("cerebras", {}).get("models") or {}
                    model = models.get(complexity, "gpt-oss-120b")
                    result = self._call_api("cerebras", model, prompt, c_key, max_tokens)
                    if result is not None:
                        return result
            else:
                o_key = self._get_available_key(self.openrouter_keys)
                if o_key:
                    fallback_models = self.config.get("ai", {}).get("openrouter", {}).get("fallback_models") or {}
                    model = fallback_models.get(complexity)
                    if not model:
                        model = self._get_default_fallback_model(complexity)
                    result = self._call_api("openrouter", model, prompt, o_key, max_tokens)
                    if result is not None:
                        return result

        if task_type in self.parallel_tasks:
            return self._parallel_route(complexity, prompt, max_tokens)
        else:
            return self._sequential_route(complexity, prompt, max_tokens)

    def _get_best_provider(self, complexity: str, prompt: str) -> Optional[str]:
        stats = {"cerebras": {"success": 0, "total": 0}, "openrouter": {"success": 0, "total": 0}}
        for (provider, model), perf in self.performance.items():
            if provider in stats:
                stats[provider]["success"] += perf["success"]
                stats[provider]["total"] += perf["success"] + perf["fail"]
        best = None
        best_rate = -1
        for provider, s in stats.items():
            if s["total"] > 5:
                rate = s["success"] / s["total"]
                if rate > best_rate:
                    best_rate = rate
                    best = provider
        return best

    def _parallel_route(self, complexity: str, prompt: str, max_tokens: int) -> Optional[str]:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            c_key = self._get_available_key(self.cerebras_keys)
            if c_key:
                models = self.config.get("ai", {}).get("cerebras", {}).get("models") or {}
                c_model = models.get(complexity, "gpt-oss-120b")
                futures.append(executor.submit(self._call_api, "cerebras", c_model, prompt, c_key, max_tokens))
            o_key = self._get_available_key(self.openrouter_keys)
            if o_key:
                fallback_models = self.config.get("ai", {}).get("openrouter", {}).get("fallback_models") or {}
                o_model = fallback_models.get(complexity)
                if not o_model:
                    o_model = self._get_default_fallback_model(complexity)
                futures.append(executor.submit(self._call_api, "openrouter", o_model, prompt, o_key, max_tokens))
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    if result is not None:
                        return result
                except Exception as e:
                    logger.debug(f"Parallel request error: {e}")
        return self._sequential_route(complexity, prompt, max_tokens)

    def _sequential_route(self, complexity: str, prompt: str, max_tokens: int) -> Optional[str]:
        c_key = self._get_available_key(self.cerebras_keys)
        if c_key:
            models = self.config.get("ai", {}).get("cerebras", {}).get("models") or {}
            c_model = models.get(complexity, "gpt-oss-120b")
            result = self._call_api("cerebras", c_model, prompt, c_key, max_tokens)
            if result is not None:
                return result
            logger.info("🔄 Cerebras failed, trying OpenRouter fallback...")
        o_key = self._get_available_key(self.openrouter_keys)
        if o_key:
            fallback_models = self.config.get("ai", {}).get("openrouter", {}).get("fallback_models") or {}
            o_model = fallback_models.get(complexity)
            if not o_model:
                o_model = self._get_default_fallback_model(complexity)
            if not o_model:
                if complexity == "high":
                    o_model = fallback_models.get("medium")
                if not o_model and complexity != "low":
                    o_model = fallback_models.get("low")
            if o_model:
                result = self._call_api("openrouter", o_model, prompt, o_key, max_tokens)
                if result is not None:
                    return result
        logger.critical("🚨 All AI providers exhausted. No response.")
        return None

    def _get_default_fallback_model(self, complexity: str) -> str:
        if complexity == "high":
            return "nvidia/nemotron-3-ultra:free"
        elif complexity == "medium":
            return "openai/gpt-oss-120b:free"
        else:
            return "google/gemma-4-26b-a4b-it:free"

    def _call_cerebras(self, model: str, prompt: str, key_info: Dict, max_tokens: int) -> Optional[str]:
        base_delay = 12
        for attempt in range(3):
            now = time.time()
            if now - self.last_request_time < base_delay:
                time.sleep(base_delay - (now - self.last_request_time) + random.uniform(0, 2))
            headers = {"Authorization": f"Bearer {key_info['key']}", "Content-Type": "application/json"}
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
                    content = resp.json().get("choices", [{}])[0].get("message", {}).get("content")
                    if content and len(content.strip()) > 0:
                        return content
                    else:
                        logger.warning("⚠️ Empty response from Cerebras.")
                elif resp.status_code == 429:
                    logger.warning("⚠️ Cerebras rate limit (429). Backing off.")
                    self._blacklist_key(key_info["key"], provider="cerebras")
                    time.sleep(60)
                    continue
                else:
                    logger.error(f"❌ Cerebras error {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                logger.error(f"❌ Cerebras connection error: {e}")
            time.sleep((2 ** attempt) + random.uniform(0, 1))
        return None

    def _call_openrouter(self, model: str, prompt: str, key_info: Dict, max_tokens: int) -> Optional[str]:
        if self.openrouter_usage_today >= self.openrouter_limit_rpd:
            logger.warning("⚠️ OpenRouter daily limit reached.")
            return None
        for attempt in range(3):
            headers = {"Authorization": f"Bearer {key_info['key']}", "Content-Type": "application/json"}
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
                    content = resp.json().get("choices", [{}])[0].get("message", {}).get("content")
                    if content and len(content.strip()) > 0:
                        return content
                    else:
                        logger.warning("⚠️ Empty response from OpenRouter.")
                elif resp.status_code == 400:
                    try:
                        err_data = resp.json()
                        err_msg = err_data.get("error", {}).get("message", "")
                        if "model" in err_msg.lower() or "not a valid model" in err_msg.lower():
                            logger.warning(f"⚠️ OpenRouter model invalid: {model}. Trying fallback.")
                            if ":" in model:
                                base_model = model.split(":")[0]
                                new_model = base_model + ":free" if not base_model.endswith(":free") else model
                            else:
                                new_model = model + ":free"
                            if new_model != model:
                                logger.info(f"🔄 Retrying with {new_model}")
                                return self._call_openrouter(new_model, prompt, key_info, max_tokens)
                            else:
                                default = "openai/gpt-oss-120b:free"
                                if default != model:
                                    return self._call_openrouter(default, prompt, key_info, max_tokens)
                    except:
                        pass
                else:
                    logger.error(f"❌ OpenRouter error {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                logger.error(f"❌ OpenRouter error: {e}")
            time.sleep((2 ** attempt) + random.uniform(0, 1))
        return None

    def _blacklist_key(self, key: str, provider: str = "cerebras"):
        unblock_time = datetime.now() + timedelta(hours=1)
        self.blacklisted_keys[key] = unblock_time
        for k in self.cerebras_keys + self.openrouter_keys:
            if k["key"] == key:
                k["status"] = "blocked"
                break
