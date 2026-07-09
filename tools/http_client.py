#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 STEALTH HTTP CLIENT (Level 5 — Proxy Rotator Integrated)
- Rotates User-Agent (fake_useragent)
- Random delays (1-3s) to avoid detection
- Handles 429 Retry-After (auto-wait)
- Proxy support via ProxyRotator (auto-rotate)
- Thread-safe
- Auto-blacklists failed proxies
"""

import time
import random
import logging
import requests
from typing import Dict, Optional, Any
from fake_useragent import UserAgent

logger = logging.getLogger("ZeroRecon")

class StealthSession:
    def __init__(self, use_proxy: bool = False, proxy_rotator=None):
        """
        Initialize a stealth HTTP session.
        
        Args:
            use_proxy: Enable proxy rotation
            proxy_rotator: ProxyRotator instance (if None and use_proxy=True, will try to import)
        """
        self.session = requests.Session()
        self.ua = UserAgent()
        self.proxy_rotator = proxy_rotator
        self.use_proxy = use_proxy and proxy_rotator is not None

        # If proxy_rotator not provided but use_proxy is True, try to load
        if use_proxy and proxy_rotator is None:
            try:
                from tools.proxy_rotator import ProxyRotator
                from tools import config
                self.proxy_rotator = ProxyRotator(config)
                self.use_proxy = True
                logger.info("🔄 ProxyRotator auto-loaded.")
            except ImportError:
                logger.warning("⚠️ ProxyRotator not available. Running without proxy.")
                self.use_proxy = False

        # Default headers (resembles a real browser)
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })

    def _rotate_ua(self):
        """Rotate User-Agent to mimic different browsers."""
        try:
            self.session.headers.update({"User-Agent": self.ua.random})
        except:
            self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    def _random_delay(self, min_sec=1.0, max_sec=3.0):
        """Random delay to avoid WAF detection."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _get_proxy(self) -> Optional[Dict]:
        """Get a proxy from the rotator (if enabled)."""
        if self.use_proxy and self.proxy_rotator:
            proxy_info = self.proxy_rotator.get_proxy()
            if proxy_info:
                proxy_url = proxy_info["url"]
                return {"http": proxy_url, "https": proxy_url}
        return None

    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Stealth GET request with proxy rotation and rate-limit handling.
        """
        self._rotate_ua()
        self._random_delay()

        proxies = self._get_proxy()
        if proxies:
            kwargs["proxies"] = proxies

        # Retry logic for 429 and proxy failures
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=30, **kwargs)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 30))
                    logger.warning(f"⏳ Rate limited (429). Waiting {wait}s...")
                    time.sleep(wait)
                    # Rotate proxy before retry
                    if self.use_proxy and self.proxy_rotator:
                        self.proxy_rotator._refresh_pool()
                    continue
                return resp

            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Timeout for {url}. Retrying...")
                time.sleep(2)
                continue

            except requests.exceptions.ProxyError:
                # Proxy failed — mark it and retry without proxy
                if proxies and self.proxy_rotator:
                    proxy_url = proxies.get("http")
                    if proxy_url:
                        self.proxy_rotator.mark_failed(proxy_url)
                        logger.warning(f"🚫 Proxy failed: {proxy_url}. Retrying without proxy.")
                        kwargs.pop("proxies", None)
                        continue
                break

            except requests.exceptions.ConnectionError:
                # Connection error — could be proxy issue, try without proxy
                if proxies and self.proxy_rotator:
                    proxy_url = proxies.get("http")
                    if proxy_url:
                        self.proxy_rotator.mark_failed(proxy_url)
                        logger.warning(f"🚫 Proxy connection failed: {proxy_url}. Retrying without proxy.")
                        kwargs.pop("proxies", None)
                        continue
                break

            except Exception as e:
                logger.error(f"❌ HTTP error: {e}")
                break

        # Final fallback: direct request without proxy
        if "proxies" in kwargs:
            kwargs.pop("proxies")
        return self.session.get(url, timeout=60, **kwargs)

    def post(self, url: str, data=None, json=None, **kwargs) -> requests.Response:
        """
        Stealth POST request with proxy rotation.
        """
        self._rotate_ua()
        self._random_delay()

        proxies = self._get_proxy()
        if proxies:
            kwargs["proxies"] = proxies

        try:
            resp = self.session.post(url, data=data, json=json, timeout=30, **kwargs)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 30))
                logger.warning(f"⏳ Rate limited (429) on POST. Waiting {wait}s...")
                time.sleep(wait)
            return resp
        except requests.exceptions.ProxyError as e:
            if proxies and self.proxy_rotator:
                proxy_url = proxies.get("http")
                if proxy_url:
                    self.proxy_rotator.mark_failed(proxy_url)
                    logger.warning(f"🚫 Proxy failed on POST: {proxy_url}. Retrying without proxy.")
                    kwargs.pop("proxies", None)
            return self.session.post(url, data=data, json=json, timeout=60, **kwargs)
        except Exception as e:
            logger.error(f"❌ POST error: {e}")
            return self.session.post(url, data=data, json=json, timeout=60, **kwargs)


# Global shortcut function
def stealth_request(url: str, delay: float = 1.5, rotate_ua: bool = True) -> requests.Response:
    """Quick stealth GET request."""
    session = StealthSession()
    return session.get(url)
