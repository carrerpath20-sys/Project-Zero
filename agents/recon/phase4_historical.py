#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 4: Historical Data Sources
- Wayback Machine (web.archive.org) snapshots
- JavaScript source code analysis
- DNS history (passive DNS)
- Extracts endpoints, subdomains, and hidden paths from historical data
"""

import re
import json
import time
import logging
import requests
from typing import Dict, Any, List, Set, Optional
from urllib.parse import urlparse, urljoin

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 4.
    Fetches historical URLs from Wayback Machine, parses JS for endpoints.
    """
    logger.info(f"📜 Phase 4 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    timeout = config.get("scan", {}).get("timeout", 10)
    
    result = {
        "target": target,
        "wayback_urls": [],
        "js_files": [],
        "endpoints_found": [],
        "dns_history": [],
        "ai_analysis": None,
        "errors": []
    }
    
    # =====================================================================
    # ১. ওয়েব্যাক মেশিন থেকে ইউআরএল ফেচ
    # =====================================================================
    try:
        # Wayback CDX API (JSON format)
        url = f"https://web.archive.org/cdx/search/cdx?url=*.{target}/*&output=json&fl=original&limit=1000"
        resp = requests.get(url, timeout=timeout)
        
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 1:
                urls = [row[0] for row in data[1:]]  # প্রথম লাইন হেডার, বাকি ডাটা
                result["wayback_urls"] = urls[:200]  # প্রথম ২০০টি
                logger.info(f"✅ Found {len(result['wayback_urls'])} historical URLs")
            else:
                logger.warning("No historical URLs found")
        else:
            logger.warning(f"Wayback API returned {resp.status_code}")
    except Exception as e:
        err_msg = f"Wayback fetch failed: {e}"
        logger.error(err_msg)
        result["errors"].append(err_msg)
    
    # =====================================================================
    # ২. JS ফাইল শনাক্ত ও পার্সিং
    # =====================================================================
    js_urls = [u for u in result["wayback_urls"] if u.endswith(('.js', '.jsx', '.ts', '.mjs'))]
    result["js_files"] = js_urls[:50]  # প্রথম ৫০টি JS ফাইল
    
    endpoints = set()
    for js_url in js_urls[:10]:  # প্রথম ১০টি JS পার্স করি (বড় না হওয়ার জন্য)
        try:
            resp = requests.get(js_url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                content = resp.text
                # API এন্ডপয়েন্ট খোঁজা: /api/, /v1/, /graphql, ইত্যাদি
                api_patterns = [
                    r'["\'](/api/[^\s"\']+)["\']',
                    r'["\'](/v[0-9]+/[^\s"\']+)["\']',
                    r'["\'](/graphql[^\s"\']*)["\']',
                    r'["\'](/rest/[^\s"\']+)["\']',
                    r'["\'](/[a-zA-Z0-9\-_]+/api/[^\s"\']+)["\']'
                ]
                for pattern in api_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        full_url = urljoin(target, match)
                        endpoints.add(full_url)
        except Exception as e:
            logger.debug(f"JS parsing error for {js_url}: {e}")
    
    result["endpoints_found"] = list(endpoints)[:50]
    if result["endpoints_found"]:
        logger.info(f"🔗 Found {len(result['endpoints_found'])} endpoints from JS")
    
    # =====================================================================
    # ৩. DNS হিস্ট্রি (প্যাসিভ DNS) — ডেমো, SecurityTrails API প্রয়োজন
    # =====================================================================
    # বাস্তবে SecurityTrails বা RiskIQ API লাগে। ফ্রি টায়ারে সীমিত।
    # আমরা ডেমো ডেটা রাখছি
    result["dns_history"] = [
        {"record": f"www.{target}", "ip": "192.0.2.1", "first_seen": "2023-01-01"},
        {"record": f"mail.{target}", "ip": "192.0.2.2", "first_seen": "2023-06-15"}
    ]
    logger.info("📋 DNS history (demo) added")
    
    # =====================================================================
    # ৪. AI অ্যানালাইসিস (যদি রাউটার থাকে)
    # =====================================================================
    if router and (result["wayback_urls"] or result["endpoints_found"]):
        try:
            prompt = f"""
            Historical recon results for {target}:
            - Wayback URLs: {len(result['wayback_urls'])}
            - JS files found: {len(result['js_files'])}
            - Endpoints extracted: {len(result['endpoints_found'])}
            - Sample endpoints: {result['endpoints_found'][:5]}
            
            Provide:
            1. Any sensitive endpoints (admin, internal, backup)?
            2. Suggest hidden subdomains based on URL patterns.
            3. Prioritize for further testing.
            """
            ai_response = router.route("historical_analysis", prompt)
            if ai_response:
                result["ai_analysis"] = ai_response
                logger.info("✅ AI historical analysis completed")
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
    
    logger.info(f"✅ Phase 4 complete. URLs: {len(result['wayback_urls'])}, Endpoints: {len(result['endpoints_found'])}")
    return result