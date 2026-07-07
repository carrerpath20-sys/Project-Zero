#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stealth HTTP Client — WAF Bypass & Rate Limiting
- Rotates User-Agent (fake_useragent)
- Random delays to avoid detection
- Handles 429 Retry-After
- Proxy support
"""
import time
import random
import logging
import requests
from typing import Dict, Optional, Any
from fake_useragent import UserAgent

logger = logging.getLogger("ZeroRecon")

class StealthSession:
    def __init__(self, use_proxy: bool = False, proxy_list: list = None):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.proxy_list = proxy_list or []
        self.use_proxy = use_proxy
        
        # ডিফল্ট হেডার
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
    
    def _rotate_ua(self):
        """ইউজার-এজেন্ট রোটেট করে"""
        try:
            self.session.headers.update({"User-Agent": self.ua.random})
        except:
            # ফ্যালব্যাক
            self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    
    def _random_delay(self, min_sec=1.0, max_sec=3.0):
        """১-৩ সেকেন্ড র্যান্ডম ডিলে (WAF এভয়েড)"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def _get_proxy(self) -> Optional[Dict]:
        """প্রক্সি সিলেক্ট (যদি ব্যবহার হয়)"""
        if self.use_proxy and self.proxy_list:
            proxy = random.choice(self.proxy_list)
            return {"http": proxy, "https": proxy}
        return None
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """স্টেলথ GET রিকোয়েস্ট"""
        self._rotate_ua()
        self._random_delay()
        
        proxies = self._get_proxy()
        if proxies:
            kwargs["proxies"] = proxies
        
        # ৪২৯ হ্যান্ডলিং (রেট্রাই)
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=30, **kwargs)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 30))
                    logger.warning(f"⏳ Rate limited (429). Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                return resp
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Timeout for {url}. Retrying...")
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ HTTP error: {e}")
                break
        # শেষ চেষ্টা
        return self.session.get(url, timeout=60, **kwargs)
    
    def post(self, url: str, data=None, json=None, **kwargs) -> requests.Response:
        """স্টেলথ POST রিকোয়েস্ট"""
        self._rotate_ua()
        self._random_delay()
        return self.session.post(url, data=data, json=json, timeout=30, **kwargs)


# গ্লোবাল ফাংশন (কুইক কলে)
def stealth_request(url: str, delay: float = 1.5, rotate_ua: bool = True) -> requests.Response:
    """সরাসরি স্টেলথ রিকোয়েস্ট করার শর্টকাট"""
    session = StealthSession()
    return session.get(url)