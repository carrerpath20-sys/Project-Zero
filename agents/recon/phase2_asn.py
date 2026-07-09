#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 2 — ASN + ORIGIN IP DISCOVERY (Level 5 — God-Tier)
- Debate Verdict: Skips if WAF risk is high (BLOCKED).
- MCTS Integration: Uses predicted origin IP patterns from DNA.
- Aggressive Cloudflare Bypass: Hunts origin IPs from subdomains + MCTS hints.
- Dual-source ASN: ipinfo.io + bgpview.io (fallback).
- AI-powered origin IP confirmation (if router available).
- Parallel validation: Checks multiple origin candidates simultaneously.
"""

import socket
import time
import logging
import requests
from typing import Dict, Any, List, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🌐 Phase 2 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক (WAF বাইপাস)
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked Phase 2 (ASN). Skipping to avoid WAF detection.")
        return {
            "target": target,
            "status": "skipped",
            "reason": "Debate BLOCKED",
            "target_ip": None,
            "asn_info": {},
            "prefixes": [],
            "origin_ips": [],
            "cloudflare_detected": False,
            "mcts_hints_used": False,
            "errors": []
        }

    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 10)
    max_workers = min(scan_config.get("max_threads", 5), 5)

    # =================================================================
    # ২. MCTS থেকে প্রেডিক্টেড অরিজিন হিন্টস
    # =================================================================
    mcts_path = context.get("mcts_path", {})
    predicted_hints = mcts_path.get("metadata", {}).get("origin_hints", [])
    if predicted_hints:
        logger.info(f"🧠 MCTS provided {len(predicted_hints)} origin IP hints.")

    # =================================================================
    # ৩. আগের ফেজ থেকে সাবডোমেইন (Phase 1)
    # =================================================================
    prev_results = context.get("previous_results", {})
    phase1 = prev_results.get("phase_1", {})
    subdomains = phase1.get("subdomains", [])
    live_subdomains = phase1.get("live_subdomains", [])
    all_targets = list(set(live_subdomains + subdomains))[:50]

    result = {
        "target": target,
        "target_ip": None,
        "asn_info": {},
        "prefixes": [],
        "origin_ips": [],
        "cloudflare_detected": False,
        "mcts_hints_used": bool(predicted_hints),
        "ai_confirmation": None,
        "errors": []
    }

    # =================================================================
    # ৪. টার্গেট IP রেজলভ
    # =================================================================
    try:
        target_ip = socket.gethostbyname(target)
        result["target_ip"] = target_ip
        logger.info(f"📡 Resolved {target} -> {target_ip}")
    except Exception as e:
        err_msg = f"DNS resolution failed: {e}"
        logger.error(err_msg)
        result["errors"].append(err_msg)
        return result

    # =================================================================
    # ৫. ASN লুকআপ (ipinfo.io Primary + bgpview.io Fallback)
    # =================================================================
    asn_info = {}
    try:
        resp = requests.get(f"https://ipinfo.io/{target_ip}/json", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            org = data.get("org", "")
            asn = org.split(" ")[0] if org and " " in org else org
            asn_info = {
                "ip": target_ip,
                "asn": asn,
                "org": org,
                "country": data.get("country"),
                "city": data.get("city"),
                "region": data.get("region"),
                "hostname": data.get("hostname")
            }
            logger.info(f"✅ ASN found: {asn} ({org})")
        else:
            logger.warning(f"ipinfo.io returned {resp.status_code}, trying bgpview...")
            # Fallback: bgpview.io
            resp2 = requests.get(f"https://api.bgpview.io/ip/{target_ip}", timeout=timeout)
            if resp2.status_code == 200:
                data2 = resp2.json()
                if data2.get("status") == "ok":
                    asn_data = data2.get("data", {})
                    asn_info = {
                        "ip": target_ip,
                        "asn": asn_data.get("asn", ""),
                        "org": asn_data.get("name", ""),
                        "country": asn_data.get("country_code", ""),
                        "city": None,
                        "region": None,
                        "hostname": None
                    }
                    logger.info(f"✅ ASN found (bgpview): {asn_info.get('asn')}")
    except Exception as e:
        err_msg = f"ASN lookup failed: {e}"
        logger.error(err_msg)
        result["errors"].append(err_msg)

    result["asn_info"] = asn_info
    asn = asn_info.get("asn", "")

    # =================================================================
    # ৬. Cloudflare ডিটেক্ট
    # =================================================================
    if "13335" in asn or "cloudflare" in asn_info.get("org", "").lower():
        result["cloudflare_detected"] = True
        logger.info("☁️ Cloudflare detected! Hunting for origin IPs...")

    # =================================================================
    # ৭. ASN প্রিফিক্স (bgpview.io)
    # =================================================================
    prefixes = []
    if asn:
        asn_clean = asn.replace("AS", "")
        try:
            url = f"https://api.bgpview.io/asn/{asn_clean}/prefixes"
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    for item in data.get("data", {}).get("ipv4_prefixes", []):
                        prefix = item.get("prefix")
                        if prefix:
                            prefixes.append(prefix)
                    logger.info(f"📡 Found {len(prefixes)} IP ranges for ASN")
        except Exception as e:
            logger.warning(f"BGP prefix fetch failed: {e}")
    result["prefixes"] = prefixes

    # =================================================================
    # ৮. অরিজিন IP হান্ট (MCTS হিন্টস + সাবডোমেইন)
    # =================================================================
    origin_candidates = set()

    # ৮a: MCTS হিন্টস
    if predicted_hints:
        for hint in predicted_hints:
            try:
                ip = socket.gethostbyname(hint)
                origin_candidates.add(ip)
                logger.info(f"🧠 MCTS hint resolved: {ip} ({hint})")
            except:
                pass

    # ৮b: সাবডোমেইন থেকে
    if all_targets:
        logger.info(f"🔍 Scanning {len(all_targets)} subdomains for origin IPs...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sub = {executor.submit(_resolve_and_check_asn, sub, timeout): sub for sub in all_targets[:30]}
            for future in as_completed(future_to_sub):
                sub = future_to_sub[future]
                try:
                    ip, is_origin = future.result(timeout=timeout+5)
                    if is_origin:
                        origin_candidates.add(ip)
                        logger.info(f"🌍 Potential origin IP: {ip} ({sub})")
                except Exception as e:
                    logger.debug(f"Origin check error for {sub}: {e}")

    result["origin_ips"] = list(origin_candidates)[:10]

    # =================================================================
    # ৯. AI কনফার্মেশন (যদি রাউটার থাকে এবং অরিজিন পাওয়া যায়)
    # =================================================================
    if router and result["origin_ips"]:
        try:
            prompt = f"""
            Target: {target} is behind Cloudflare (AS{asn}).
            Potential origin IPs: {result['origin_ips']}
            ASN Info: {asn_info}
            
            Confirm the most likely real origin IP. Output only the IP address.
            """
            ai_conf = router.route("origin_confirmation", prompt)
            if ai_conf:
                # Clean AI response
                import re
                ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', ai_conf)
                if ip_match:
                    confirmed_ip = ip_match.group(0)
                    if confirmed_ip in result["origin_ips"]:
                        result["ai_confirmation"] = confirmed_ip
                        logger.info(f"✅ AI confirmed origin IP: {confirmed_ip}")
                    else:
                        result["ai_confirmation"] = f"AI suggested {confirmed_ip} (not in list)"
        except Exception as e:
            logger.warning(f"AI confirmation failed: {e}")

    logger.info(f"✅ Phase 2 complete. ASN: {asn}, Origin IPs: {len(result['origin_ips'])}")
    return result


# ============================================================
#  হেল্পার ফাংশন (প্যারালাল-রেডি)
# ============================================================

def _resolve_and_check_asn(domain: str, timeout: int) -> tuple:
    """
    Resolve domain and check if it's a non-Cloudflare IP (possible origin).
    Returns: (ip, is_origin)
    """
    try:
        ip = socket.gethostbyname(domain)
        # Skip if private IP
        if ip.startswith(('10.', '172.16.', '192.168.', '127.')):
            return ip, False
        # Quick ASN check via ipinfo.io
        try:
            resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                org = data.get("org", "").lower()
                if "cloudflare" not in org and "13335" not in org:
                    return ip, True
        except:
            # If ipinfo fails, assume it's a potential origin
            return ip, True
    except:
        pass
    return None, False
