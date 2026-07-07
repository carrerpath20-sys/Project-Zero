#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  CONTEXT MANAGER — Token Caching & Conversation Context Tracking      █
█  - Count tokens in prompts and responses (tiktoken fallback)        █
█  - Cache AI responses to reduce API costs and latency               █
█  - Summarize long conversations to stay within token limits        █
█  - Track current context window usage                              █
████████████████████████████████████████████████████████████████████████████
"""

import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger("ZeroRecon")

class ContextManager:
    """
    টোকেন ক্যাশিং ও কনটেক্সট ট্র্যাকিং — AI কলের খরচ ও সময় বাঁচায়।
    """
    
    def __init__(self, config: Optional[Dict] = None, cache_dir: str = "state/cache"):
        self.config = config or {}
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # টোকেন কাউন্টার (tiktoken লোড করার চেষ্টা করি)
        self.tokenizer = None
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.debug("✅ tiktoken loaded successfully.")
        except ImportError:
            logger.warning("⚠️ tiktoken not installed. Using fallback token counting.")
        
        # ক্যাশের মেটাডেটা
        self.cache_meta_file = self.cache_dir / "cache_meta.json"
        self.meta = self._load_meta()
        
        # কনটেক্সট উইন্ডো ট্র্যাকিং
        self.current_tokens = 0
        self.max_allowed_tokens = self.config.get("max_context_tokens", 200000)
        
        logger.info(f"🧠 ContextManager initialized (cache: {self.cache_dir})")
    
    # ========== টোকেন কাউন্টিং ==========
    def count_tokens(self, text: str) -> int:
        """একটি টেক্সটের টোকেন সংখ্যা গণনা করে (tiktoken বা ফ্যালব্যাক)"""
        if not text:
            return 0
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except:
                pass
        # ফ্যালব্যাক: ১ টোকেন ≈ ৪ অক্ষর
        return len(text) // 4
    
    def count_conversation_tokens(self, messages: List[Dict]) -> int:
        """একাধিক মেসেজের মোট টোকেন গণনা"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.count_tokens(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += self.count_tokens(part["text"])
        return total
    
    def is_token_limit_reached(self, messages: List[Dict], threshold: float = 0.85) -> bool:
        """বর্তমান টোকেন ব্যবহার ৮৫%-এর বেশি কিনা চেক করে"""
        total = self.count_conversation_tokens(messages)
        return total > (self.max_allowed_tokens * threshold)
    
    # ========== ক্যাশিং ==========
    def _get_cache_key(self, prompt: str, model: str, task_type: str) -> str:
        """প্রম্পট, মডেল ও টাস্ক টাইপ দেখে একটি অনন্য কী তৈরি করে"""
        content = f"{prompt}|{model}|{task_type}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _load_meta(self) -> Dict:
        """ক্যাশ মেটাডেটা লোড করে"""
        if self.cache_meta_file.exists():
            try:
                with open(self.cache_meta_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"entries": {}}
    
    def _save_meta(self):
        """ক্যাশ মেটাডেটা সেভ করে"""
        try:
            with open(self.cache_meta_file, 'w') as f:
                json.dump(self.meta, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save cache meta: {e}")
    
    def get_cached(self, prompt: str, model: str, task_type: str, max_age_hours: int = 24) -> Optional[str]:
        """ক্যাশ থেকে রেসপন্স খোঁজে (যদি ২৪ ঘন্টার পুরনো না হয়)"""
        key = self._get_cache_key(prompt, model, task_type)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # সময় চেক
            timestamp = datetime.fromisoformat(data.get("timestamp", "2020-01-01T00:00:00"))
            age = datetime.now() - timestamp
            if age > timedelta(hours=max_age_hours):
                logger.debug(f"Cache expired for key {key}")
                return None
            
            logger.debug(f"✅ Cache hit for {key} (age: {age.total_seconds():.0f}s)")
            return data.get("response")
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
            return None
    
    def save_cache(self, prompt: str, model: str, task_type: str, response: str):
        """রেসপন্স ক্যাশে সেভ করে"""
        key = self._get_cache_key(prompt, model, task_type)
        cache_file = self.cache_dir / f"{key}.json"
        
        data = {
            "key": key,
            "prompt": prompt[:500],  # পুরো প্রম্পট না রাখলেও চলে
            "model": model,
            "task_type": task_type,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # মেটা আপডেট
            self.meta["entries"][key] = {
                "model": model,
                "task_type": task_type,
                "timestamp": data["timestamp"],
                "size": len(response)
            }
            self._save_meta()
            logger.debug(f"💾 Cache saved for key {key}")
        except Exception as e:
            logger.debug(f"Cache save error: {e}")
    
    # ========== কনটেক্সট সামারি (Future Use) ==========
    def summarize_context(self, messages: List[Dict], max_tokens: int = 10000) -> List[Dict]:
        """
        অতিরিক্ত লম্বা কনটেক্সটকে সংক্ষিপ্ত করে (ভবিষ্যতে Healer Agent ব্যবহার করবে)
        বর্তমানে শুধু ট্রাঙ্কেট করে।
        """
        current_tokens = self.count_conversation_tokens(messages)
        if current_tokens <= max_tokens:
            return messages
        
        logger.warning(f"⚠️ Context too long ({current_tokens} tokens). Truncating to {max_tokens}.")
        
        # সবচেয়ে সহজ পদ্ধতি: শেষের দিকের মেসেজগুলো রাখি
        truncated = []
        total = 0
        for msg in reversed(messages):
            msg_tokens = self.count_conversation_tokens([msg])
            if total + msg_tokens <= max_tokens:
                truncated.insert(0, msg)
                total += msg_tokens
            else:
                break
        
        if not truncated:
            truncated = messages[-1:]  # কমপক্ষে শেষ মেসেজটি রাখি
        
        return truncated
    
    # ========== পরিসংখ্যান ==========
    def get_stats(self) -> Dict[str, Any]:
        """ক্যাশ ও টোকেন ব্যবহারের পরিসংখ্যান"""
        total_cached = len(self.meta.get("entries", {}))
        total_size = sum(e.get("size", 0) for e in self.meta.get("entries", {}).values())
        
        return {
            "total_cached_entries": total_cached,
            "cache_size_mb": total_size / (1024 * 1024),
            "current_context_tokens": self.current_tokens,
            "max_context_tokens": self.max_allowed_tokens
        }
    
    def clear_cache(self, older_than_days: Optional[int] = None):
        """পুরানো ক্যাশ মুছে ফেলে (যদি প্রয়োজন হয়)"""
        if older_than_days is None:
            # সব ক্যাশ মুছে ফেলি
            for f in self.cache_dir.glob("*.json"):
                if f.name != "cache_meta.json":
                    f.unlink()
            self.meta = {"entries": {}}
            self._save_meta()
            logger.info("🗑️ Entire cache cleared.")
            return
        
        # নির্দিষ্ট দিনের বেশি পুরানো মুছে ফেলি
        cutoff = datetime.now() - timedelta(days=older_than_days)
        removed = 0
        for key, entry in list(self.meta["entries"].items()):
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts < cutoff:
                cache_file = self.cache_dir / f"{key}.json"
                if cache_file.exists():
                    cache_file.unlink()
                del self.meta["entries"][key]
                removed += 1
        self._save_meta()
        logger.info(f"🗑️ Removed {removed} cache entries older than {older_than_days} days.")