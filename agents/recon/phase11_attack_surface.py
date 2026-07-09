#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 11 — REAL-WORLD ATTACK SURFACE SUMMARY (Level 5 — API-Aware God-Tier)
- Debate Verdict: Skips if BLOCKED (0 API calls).
- MCTS Integration: Uses confidence scores from previous phases.
- Aggressive Banner Grabbing: Parallel HTTP checks (0 API calls).
- Infrastructure Stack Detection: Nginx/Apache/Cloudflare (0 API calls).
- Priority Scoring: Critical/High/Medium/Low based on patterns + MCTS.
- AI Summary: ONLY 1 optional call (can be disabled in config).
"""

import re
import logging
import requests
from typing import Dict, Any, List, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib3.exceptions import InsecureRequestWarning

# SSL সতর্কতা দমন
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger("ZeroRecon")

# ============================================================
#  ক্রিটিক্যাল প্যাটার্ন (অ্যাটাক সারফেস স্কোরিং)
# ============================================================
CRITICAL_PATTERNS = [
    "admin", "portal", "dashboard", "internal", "api", "secure",
    "auth", "vpn", "backup", "restore", "config", "console",
    "manager", "control", "monitor", "ops", "devops", "jenkins",
    "jira", "confluence", "gitlab", "grafana", "kibana", "elastic"
]

HIGH_PATTERNS = [
    "dev", "test", "staging", "qa", "uat", "stage", "demo",
    "sandbox", "experimental", "beta", "alpha", "preprod"
]

# ============================================================
#  মেইন ফাংশন
# ============================================================
def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"📊 Phase 11 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক (যদি BLOCKED, ০ API কল)
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked Phase 11 (Attack Surface). Skipping to avoid WAF.")
        return {
            "target": target,
            "status": "skipped",
            "reason": "Debate BLOCKED",
            "confirmed_subdomains": [],
            "critical_assets": [],
            "infrastructure_stack": {},
            "ai_executive_summary": None
        }

    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 10)
    max_workers = min(scan_config.get("max_threads", 15), 15)

    # =================================================================
    # ২. আগের ফেজ থেকে ডাটা সংগ্রহ (সাবডোমেইন + এন্ডপয়েন্ট)
    # =================================================================
    prev_results = context.get("previous_results", {})
    all_subdomains = set()

    # ফেজ ১, ৬, ৮, ৯, ১০ থেকে সাবডোমেইন সংগ্রহ
    for key in ["phase_1", "phase_6", "phase_8", "phase_9", "phase_10"]:
        data = prev_results.get(key, {})
        if key == "phase_1":
            all_subdomains.update(data.get("subdomains", []))
            all_subdomains.update(data.get("live_subdomains", []))
        elif key == "phase_6":
            all_subdomains.update(data.get("permutations", []))
        elif key == "phase_8":
            all_subdomains.update(data.get("found_subdomains", []))
        elif key == "phase_9":
            all_subdomains.update(data.get("subdomains", []))
        elif key == "phase_10":
            for item in data.get("takeover_candidates", []):
                all_subdomains.add(item.get("subdomain", ""))

    # =================================================================
    # ৩. MCTS কনফিডেন্স স্কোর (ইভো থেকে)
    # =================================================================
    mcts_path = context.get("mcts_path", {})
    mcts_confidence = mcts_path.get("confidence", 0.5)
    logger.info(f"🧠 MCTS Confidence: {mcts_confidence:.2f}")

    # =================================================================
    # ৪. প্যারালাল ব্যানার গ্র্যাবিং (HTTP চেক)
    # =================================================================
    logger.info(f"🔍 Confirming {len(all_subdomains)} subdomains via HTTP banner...")
    confirmed = []
    endpoints_to_check = list(all_subdomains)[:80]  # ৮০টি চেক (রেট লিমিট এড়াতে)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_sub = {
            executor.submit(_check_http_banner, sub, timeout): sub
            for sub in endpoints_to_check
        }
        for future in as_completed(future_to_sub):
            sub = future_to_sub[future]
            try:
                result = future.result(timeout=timeout+5)
                if result:
                    confirmed.append(result)
                    # শুধু গুরুত্বপূর্ণ লগ
                    if result.get("status") in [200, 403, 401, 302]:
                        logger.info(f"✅ {sub} -> {result['status']} ({result.get('server', 'unknown')})")
            except Exception as e:
                logger.debug(f"Banner error for {sub}: {e}")

    logger.info(f"📡 Confirmed {len(confirmed)} live subdomains.")

    # =================================================================
    # ৫. ইনফ্রাস্ট্রাকচার স্ট্যাক আইডেন্টিফাই (লোকাল অ্যালগরিদম)
    # =================================================================
    stack = {"webservers": set(), "cdn": set(), "technologies": set()}
    for entry in confirmed:
        server = entry.get("server", "").lower()
        if "nginx" in server:
            stack["webservers"].add("Nginx")
        elif "apache" in server:
            stack["webservers"].add("Apache")
        elif "cloudflare" in server:
            stack["cdn"].add("Cloudflare")
        elif "aws" in server or "amazon" in server:
            stack["cdn"].add("AWS")
        elif "github" in server:
            stack["cdn"].add("GitHub Pages")

    # =================================================================
    # ৬. অ্যাসেট প্রায়োরিটাইজেশন (প্যাটার্ন + MCTS কনফিডেন্স)
    # =================================================================
    assets = {"critical": [], "high": [], "medium": [], "low": []}

    for sub in all_subdomains:
        sub_lower = sub.lower()
        assigned = False

        # ক্রিটিক্যাল
        for pattern in CRITICAL_PATTERNS:
            if pattern in sub_lower:
                assets["critical"].append(sub)
                assigned = True
                break

        # হাই
        if not assigned:
            for pattern in HIGH_PATTERNS:
                if pattern in sub_lower:
                    assets["high"].append(sub)
                    assigned = True
                    break

        # মিডিয়াম
        if not assigned and any(part in sub_lower for part in ["api", "app", "web"]):
            assets["medium"].append(sub)
            assigned = True

        # লো
        if not assigned:
            assets["low"].append(sub)

    # MCTS কনফিডেন্স অনুযায়ী ক্রিটিক্যাল লিস্ট রিফাইন
    if mcts_confidence > 0.7:
        # শুধু টপ ২০টা ক্রিটিক্যাল রাখি
        assets["critical"] = assets["critical"][:20]

    # =================================================================
    # ৭. রেজাল্ট
    # =================================================================
    result = {
        "target": target,
        "confirmed_subdomains": confirmed[:50],
        "infrastructure_stack": {
            "webservers": list(stack["webservers"]),
            "cdn": list(stack["cdn"])
        },
        "assets_by_priority": {
            "critical": assets["critical"][:20],
            "high": assets["high"][:30],
            "medium": assets["medium"][:30],
            "low": assets["low"][:30]
        },
        "mcts_confidence": mcts_confidence,
        "ai_executive_summary": None
    }

    # =================================================================
    # ৮. AI এক্সিকিউটিভ সামারি (শুধু ১টি কল — ঐচ্ছিক)
    # =================================================================
    # ⚠️ এখানেই শুধুমাত্র ১টি API কল — কিন্তু আপনি চাইলে বন্ধ করতে পারেন
    if router and (result["confirmed_subdomains"] or assets["critical"]):
        try:
            prompt = f"""
            Attack surface summary for {target}:
            - Confirmed live subdomains: {len(result['confirmed_subdomains'])}
            - Critical assets: {len(assets['critical'])}
            - Web servers: {list(stack['webservers'])}
            - CDN: {list(stack['cdn'])}
            - MCTS Confidence: {mcts_confidence:.2f}

            Provide a 150-word executive summary covering:
            1. Overall security posture.
            2. Top 3 most critical assets to test manually.
            3. Recommended immediate actions.
            """
            ai_response = router.route("attack_surface_summary", prompt)
            if ai_response:
                result["ai_executive_summary"] = ai_response
                logger.info("✅ AI executive summary received.")
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")

    logger.info(f"✅ Phase 11 complete. Critical: {len(assets['critical'])}, High: {len(assets['high'])}")
    return result


# ============================================================
#  হেল্পার ফাংশন (HTTP ব্যানার গ্র্যাব — ০ API কল)
# ============================================================
def _check_http_banner(domain: str, timeout: int) -> Optional[Dict]:
    """
    Quick HTTP/HTTPS banner grab for a single subdomain.
    Returns: dict with status, server, content_type, or None if unreachable.
    """
    tech = {}
    # HTTPS প্রথমে চেষ্টা
    for protocol in ["https", "http"]:
        try:
            url = f"{protocol}://{domain}"
            resp = requests.get(url, timeout=timeout, allow_redirects=True, verify=False)
            tech = {
                "subdomain": domain,
                "status": resp.status_code,
                "server": resp.headers.get("Server", ""),
                "content_type": resp.headers.get("Content-Type", ""),
                "length": len(resp.content),
                "redirect": resp.url if resp.url != url else None
            }
            # যদি ২০০ বা ৩০x পাই, ব্রেক করি
            if resp.status_code in [200, 301, 302, 307, 401, 403, 404, 503]:
                break
        except requests.exceptions.SSLError:
            # SSL এরর হলে HTTP-তে চলে যাই (লুপের দ্বিতীয় পাসে)
            continue
        except requests.exceptions.ConnectionError:
            # Connection refused বা timeout
            continue
        except requests.exceptions.Timeout:
            continue
        except:
            continue

    return tech if tech else None
