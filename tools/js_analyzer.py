#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JS Analyzer — Level 4: Reliable JS Fetcher with Source Map Recovery.
Downloads JS files, extracts sourceMappingURL, handles large files safely,
and passes content to the Symbolic Engine (Level 5) for deep analysis.
"""

import re
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("ZeroRecon")

class JSAnalyzer:
    """
    Level 4 JS Analyzer:
    - Downloads JS with stealth headers (UA rotation).
    - Detects and fetches source maps (if available).
    - Truncates files > 2MB to avoid memory crashes.
    - Returns raw content and map data for Symbolic Engine.
    """
    def __init__(self, config: Dict):
        self.config = config
        self.timeout = config.get("scan", {}).get("timeout", 30)
        self.max_size_mb = 2  # 2MB limit for safety

    def fetch(self, js_url: str, target: str) -> Dict[str, Any]:
        """
        Fetch JS content and source map if available.
        Returns: {"content": str, "map": dict, "url": str, "truncated": bool}
        """
        logger.info(f"📜 Fetching JS: {js_url[:80]}...")
        result = {
            "url": js_url,
            "content": "",
            "map": None,
            "truncated": False,
            "error": None
        }
        try:
            # Stealth headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": f"https://{target}"
            }
            resp = requests.get(js_url, headers=headers, timeout=self.timeout, stream=True)
            if resp.status_code != 200:
                result["error"] = f"HTTP {resp.status_code}"
                return result

            # Check size before full download
            content_length = resp.headers.get('content-length')
            if content_length and int(content_length) > self.max_size_mb * 1024 * 1024:
                logger.warning(f"⚠️ JS file too large ({int(content_length) // 1024}KB). Truncating to {self.max_size_mb}MB.")
                result["truncated"] = True
                # Stream read limited bytes
                content = b""
                for chunk in resp.iter_content(chunk_size=1024):
                    if len(content) < self.max_size_mb * 1024 * 1024:
                        content += chunk
                    else:
                        break
                result["content"] = content.decode('utf-8', errors='ignore')
            else:
                result["content"] = resp.text

            # Extract Source Map URL
            map_url = self._extract_sourcemap(result["content"], js_url)
            if map_url:
                logger.info(f"🗺️ Source map found: {map_url[:60]}...")
                map_data = self._fetch_sourcemap(map_url)
                if map_data:
                    result["map"] = map_data

            return result

        except requests.exceptions.Timeout:
            result["error"] = "Timeout"
        except Exception as e:
            result["error"] = str(e)
        return result

    def _extract_sourcemap(self, content: str, fallback_url: str) -> Optional[str]:
        """Extract sourceMappingURL from JS content or header."""
        # Check for comment-based source map
        pattern = r'//# sourceMappingURL=(.+)$'
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        # Check if relative, convert to absolute
        if match:
            url = match.group(1).strip()
            if url.startswith('http'):
                return url
            # Relative path: construct absolute URL
            from urllib.parse import urljoin
            return urljoin(fallback_url, url)
        return None

    def _fetch_sourcemap(self, map_url: str) -> Optional[Dict]:
        """Fetch source map JSON."""
        try:
            resp = requests.get(map_url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None
