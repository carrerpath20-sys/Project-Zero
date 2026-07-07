#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 11: Real-World Attack Surface Summary
- Confirms subdomains (banner grabbing, status codes)
- Identifies infrastructure stack (Web server, CDN, OS)
- Scores and prioritizes assets
- Uses AI to generate executive-level summary
"""

import re
import logging
import requests
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 11.
    """
    logger.info(f"📊 Phase 11 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    timeout = config.get("scan", {}).get("timeout", 10)
    
    prev_results = context.get("previous_results", {})
    
    # =====================================================================
    # ১. ডাটা একত্রিত করা
    # =====================================================================
    all_subdomains = set()
    all_ips = set()
    
    # ফেজ ১, ৬, ৮, ৯, ১০ থেকে সাবডোমেইন
    for key in ["phase_1", "phase_6", "phase_8", "phase_9", "phase_10"]:
        data = prev_results.get(key, {})
        if key == "phase_1":
            all_subdomains.update(data.get("subdomains", []))
        elif key == "phase_6":
            all_subdomains.update(data.get("permutations", []))
        elif key == "phase_8":
            all_subdomains.update(data.get("found_subdomains", []))
        elif key == "phase_9":
            all_subdomains.update(data.get("subdomains", []))
        elif key == "phase_10":
            for item in data.get("takeover_candidates", []):
                all_subdomains.add(item.get("subdomain"))
    
    # আইপি
    phase2 = prev_results.get("phase_2", {})
    phase7 = prev_results.get("phase_7", {})
    if phase2.get("target_ip"):
        all_ips.add(phase2["target_ip"])
    all_ips.update(phase2.get("origin_ips", []))
    all_ips.update(phase7.get("live_hosts", []))
    
    result = {
        "target": target,
        "confirmed_subdomains": [],
        "infrastructure_stack": {},
        "assets_by_priority": {"critical": [], "high": [], "medium": [], "low": []},
        "ai_executive_summary": None,
        "errors": []
    }
    
    # =====================================================================
    # ২. সাবডোমেইন কনফার্মেশন (HTTP ব্যানার)
    # =====================================================================
    logger.info(f"🔍 Confirming {len(all_subdomains)} subdomains...")
    confirmed = []
    for sub in list(all_subdomains)[:50]:
        url = f"https://{sub}"
        try:
            resp = requests.get(url, timeout=timeout, allow_redirects=True, verify=False)
            server = resp.headers.get("Server", "Unknown")
            status = resp.status_code
            tech = {
                "status": status,
                "server": server,
                "content_type": resp.headers.get("Content-Type", ""),
                "length": len(resp.content)
            }
            confirmed.append({"subdomain": sub, "tech": tech})
            logger.debug(f"✅ {sub} -> {status} ({server})")
        except Exception as e:
            logger.debug(f"Failed to confirm {sub}: {e}")
    
    result["confirmed_subdomains"] = confirmed
    
    # =====================================================================
    # ৩. ইনফ্রাস্ট্রাকচার স্ট্যাক আইডেন্টিফাই
    # =====================================================================
    stack = {"webservers": set(), "cdn": set(), "technologies": set()}
    
    for entry in confirmed:
        server = entry.get("tech", {}).get("server", "").lower()
        if "nginx" in server:
            stack["webservers"].add("Nginx")
        elif "apache" in server:
            stack["webservers"].add("Apache")
        elif "cloudflare" in server:
            stack["cdn"].add("Cloudflare")
        elif "aws" in server or "amazon" in server:
            stack["cdn"].add("AWS")
    
    result["infrastructure_stack"] = {
        "webservers": list(stack["webservers"]),
        "cdn": list(stack["cdn"])
    }
    
    # =====================================================================
    # ৪. অ্যাসেট প্রায়োরিটাইজেশন
    # =====================================================================
    # ক্রিটিক্যাল: admin, portal, dashboard, api, internal
    critical_patterns = ["admin", "portal", "dashboard", "internal", "api", "secure", "auth", "vpn"]
    for sub in all_subdomains:
        assigned = False
        for pattern in critical_patterns:
            if pattern in sub:
                result["assets_by_priority"]["critical"].append(sub)
                assigned = True
                break
        if not assigned and sub.startswith(("dev", "test", "staging", "qa")):
            result["assets_by_priority"]["high"].append(sub)
        elif not assigned:
            result["assets_by_priority"]["medium"].append(sub)
    
    # =====================================================================
    # ৫. AI এক্সিকিউটিভ সামারি
    # =====================================================================
    if router:
        try:
            prompt = f"""
            Attack surface summary for {target}:
            - Total subdomains: {len(all_subdomains)}
            - Confirmed live: {len(confirmed)}
            - Web servers: {list(stack['webservers'])}
            - Critical assets: {len(result['assets_by_priority']['critical'])}
            
            Provide an executive summary (200 words) covering:
            1. Overall security posture.
            2. Top 3 most critical assets to test.
            3. Recommended immediate reconnaissance actions.
            """
            ai_response = router.route("executive_summary", prompt)
            if ai_response:
                result["ai_executive_summary"] = ai_response
                logger.info("✅ AI executive summary generated")
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")
    
    logger.info(f"✅ Phase 11 complete. Confirmed: {len(confirmed)}, Critical: {len(result['assets_by_priority']['critical'])}")
    return result