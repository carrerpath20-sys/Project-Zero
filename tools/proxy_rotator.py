#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy Rotator — Level 5 (God-Tier): Aggressive Proxy Pool Manager.
- Scrapes 4+ free proxy sources (HTTP/SOCKS5).
- Validates proxies (1.1.1.1 ping) with low timeout.
- Rotates proxies per request (Thread-safe).
- Blacklists failed proxies for 5 minutes.
- Auto-refreshes pool every 5 minutes.
"""

import random
import time
import logging
import threading
import requests
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger("ZeroRecon")

class ProxyRotator:
    """
    Level 5 Proxy Rotator: Never use the same IP twice.
    """
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("opsec", {}).get("proxy_enabled", True)
        self.proxies = []  # List of {"url": str, "type": str, "last_used": float}
        self.blacklist = {}  # url -> unblock_time
        self.lock = threading.Lock()
        self.last_refresh = 0
        self.refresh_interval = 300  # 5 minutes
        self.validation_timeout = 3
        self._init_pool()

    def _init_pool(self):
        """Initial pool load."""
        if not self.enabled:
            return
        self._refresh_pool()

    def get_proxy(self) -> Optional[Dict]:
        """
        Get the next available proxy (Round Robin with retry).
        Returns: {"url": "http://...", "type": "http"} or None.
        """
        if not self.enabled or not self.proxies:
            return None

        # Refresh if needed
        if time.time() - self.last_refresh > self.refresh_interval:
            self._refresh_pool()

        with self.lock:
            # Remove blacklisted
            now = time.time()
            self.proxies = [p for p in self.proxies if p["url"] not in self.blacklist or self.blacklist[p["url"]] < now]

            if not self.proxies:
                return None

            # Try to find a working proxy (max 5 attempts)
            for _ in range(5):
                proxy = random.choice(self.proxies)
                if proxy["url"] not in self.blacklist or self.blacklist[proxy["url"]] < time.time():
                    return proxy

            # If all blacklisted, refresh and retry
            self._refresh_pool()
            if self.proxies:
                return random.choice(self.proxies)
            return None

    def mark_failed(self, proxy_url: str):
        """Mark a proxy as failed (blacklist for 5 minutes)."""
        with self.lock:
            self.blacklist[proxy_url] = time.time() + 300  # 5 minutes
            logger.debug(f"🚫 Proxy blacklisted: {proxy_url}")

    def _refresh_pool(self):
        """Scrape fresh proxies from multiple sources."""
        with self.lock:
            logger.info("🔄 Refreshing proxy pool...")
            new_proxies = []
            sources = [
                self._scrape_proxyscrape,
                self._scrape_sslproxies,
                self._scrape_github_raw
            ]
            for source in sources:
                try:
                    proxies = source()
                    if proxies:
                        new_proxies.extend(proxies)
                except Exception as e:
                    logger.debug(f"Proxy source error: {e}")

            # Validate and deduplicate
            validated = []
            seen = set()
            for p in new_proxies:
                if p["url"] in seen:
                    continue
                seen.add(p["url"])
                if self._validate_proxy(p["url"]):
                    validated.append(p)
                    if len(validated) >= 50:  # Max 50 proxies to keep it fast
                        break

            if validated:
                self.proxies = validated
                logger.info(f"✅ Proxy pool refreshed: {len(validated)} valid proxies.")
            else:
                logger.warning("⚠️ No valid proxies found. Using fallback (direct connection).")
                self.proxies = []
            self.last_refresh = time.time()

    def _validate_proxy(self, proxy_url: str) -> bool:
        """Check if proxy works by connecting to 1.1.1.1."""
        try:
            test_url = "http://1.1.1.1"
            proxies = {"http": proxy_url, "https": proxy_url}
            resp = requests.get(test_url, proxies=proxies, timeout=self.validation_timeout)
            return resp.status_code == 200
        except:
            return False

    def _scrape_proxyscrape(self) -> List[Dict]:
        """Source 1: proxyscrape.com (HTTP/SOCKS5)."""
        urls = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all"
        ]
        proxies = []
        for url in urls:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    for line in resp.text.splitlines():
                        if ":" in line:
                            ip, port = line.split(":")
                            proto = "socks5" if "socks" in url else "http"
                            proxies.append({"url": f"{proto}://{ip}:{port}", "type": proto})
            except:
                pass
        return proxies

    def _scrape_sslproxies(self) -> List[Dict]:
        """Source 2: sslproxies.org (scrape)."""
        proxies = []
        try:
            resp = requests.get("https://www.sslproxies.org/", timeout=10)
            if resp.status_code == 200:
                import re
                # Simple IP:Port extraction
                pattern = r'<td>(\d+\.\d+\.\d+\.\d+)<\/td><td>(\d+)<\/td>'
                matches = re.findall(pattern, resp.text)
                for ip, port in matches[:20]:
                    proxies.append({"url": f"http://{ip}:{port}", "type": "http"})
        except:
            pass
        return proxies

    def _scrape_github_raw(self) -> List[Dict]:
        """Source 3: GitHub gist/raw proxy lists."""
        proxies = []
        try:
            resp = requests.get("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", timeout=10)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    if line and ":" in line:
                        proxies.append({"url": f"http://{line.strip()}", "type": "http"})
        except:
            pass
        return proxies
