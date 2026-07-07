#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2: ASN Enumeration + Origin IP Discovery
- Finds ASN (Autonomous System Number) for target IP
- Gets all IP prefixes (CIDR ranges) belonging to that ASN
- Detects Cloudflare/other CDNs and attempts to find real origin IP
- Uses ipinfo.io and bgpview.io (free APIs, no keys required)
"""

import socket
import logging
import requests
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 2.
    context contains: router, config, previous_results (including subdomains from phase 1)
    """
    logger.info(f"🌐 Phase 2 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 10)
    
    # আগের ফেজ থেকে সাবডোমেইন নিয়ে নেওয়া
    prev_results = context.get("previous_results", {})
    phase1_data = prev_results.get("phase_1", {})
    subdomains = phase1_data.get("subdomains", [])
    
    result = {
        "target": target,
        "target_ip": None,
        "asn_info": {},
        "prefixes": [],
        "origin_ips": [],
        "cloudflare_detected": False,
        "ai_suggestions": None,
        "errors": []
    }
    
    # =====================================================================
    # ১. টার্গেট IP রেজলভ
    # =====================================================================
    try:
        target_ip = socket.gethostbyname(target)
        result["target_ip"] = target_ip
        logger.info(f"📡 Resolved {target} -> {target_ip}")
    except Exception as e:
        err_msg = f"DNS resolution failed: {e}"
        logger.error(err_msg)
        result["errors"].append(err_msg)
        return result
    
    # =====================================================================
    # ২. ASN লুকআপ (ipinfo.io)
    # =====================================================================
    try:
        resp = requests.get(f"https://ipinfo.io/{target_ip}/json", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            org = data.get("org", "")
            asn = org.split(" ")[0] if org and " " in org else org
            result["asn_info"] = {
                "ip": target_ip,
                "asn": asn,
                "org": org,
                "country": data.get("country"),
                "city": data.get("city"),
                "region": data.get("region"),
                "hostname": data.get("hostname")
            }
            logger.info(f"✅ ASN found: {asn} ({org})")
            
            # Cloudflare ডিটেক্ট
            if "13335" in asn or "cloudflare" in org.lower():
                result["cloudflare_detected"] = True
                logger.info("☁️ Cloudflare detected! Hunting for origin IPs...")
        else:
            logger.warning(f"ipinfo.io returned {resp.status_code}")
    except Exception as e:
        err_msg = f"ASN lookup failed: {e}"
        logger.error(err_msg)
        result["errors"].append(err_msg)
    
    # =====================================================================
    # ৩. ASN প্রিফিক্স (bgpview.io)
    # =====================================================================
    asn_clean = result["asn_info"].get("asn", "").replace("AS", "")
    if asn_clean:
        try:
            url = f"https://api.bgpview.io/asn/{asn_clean}/prefixes"
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    prefixes = []
                    for item in data.get("data", {}).get("ipv4_prefixes", []):
                        prefixes.append(item.get("prefix"))
                    result["prefixes"] = prefixes
                    logger.info(f"📡 Found {len(prefixes)} IP ranges for ASN")
            else:
                logger.warning(f"bgpview.io returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"BGP prefix fetch failed: {e}")
    
    # =====================================================================
    # ৪. ক্লাউডফ্লেয়ার বাইপাস: অরিজিন IP হান্ট (সাবডোমেইন থেকে)
    # =====================================================================
    if result["cloudflare_detected"] and subdomains:
        logger.info("🔍 Scanning subdomains for real origin IPs...")
        origin_candidates = set()
        # প্রথম ২০টি সাবডোমেইন চেক
        for sub in subdomains[:20]:
            try:
                ip = socket.gethostbyname(sub)
                # এই IP-র ASN চেক (ipinfo.io)
                try:
                    resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        org = data.get("org", "")
                        if "cloudflare" not in org.lower() and "13335" not in org:
                            origin_candidates.add(ip)
                            logger.info(f"🌍 Potential origin IP: {ip} ({org})")
                except:
                    pass
            except:
                pass
        
        result["origin_ips"] = list(origin_candidates)[:10]
        if result["origin_ips"]:
            logger.info(f"✅ Found {len(result['origin_ips'])} potential origin IPs")
    
    # =====================================================================
    # ৫. AI সুপারিশ (যদি রাউটার থাকে)
    # =====================================================================
    if router and result.get("origin_ips"):
        try:
            prompt = f"""
            Target {target} is behind Cloudflare.
            Found potential origin IPs: {result['origin_ips']}
            ASN: {result['asn_info']}
            
            Suggest:
            1. Which IP is most likely the real origin?
            2. Next steps to verify and exploit.
            """
            ai_response = router.route("origin_hunt", prompt)
            if ai_response:
                result["ai_suggestions"] = ai_response
                logger.info("✅ AI origin hunt suggestions received")
        except Exception as e:
            logger.warning(f"AI suggestion failed: {e}")
    
    logger.info(f"✅ Phase 2 complete. ASN: {result['asn_info'].get('asn')}, Origin IPs: {len(result.get('origin_ips', []))}")
    return result