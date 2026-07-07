#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 10: Vulnerability Specific Enumeration
- Subdomain Takeover testing (CNAME + dangling)
- CORS misconfiguration discovery (Access-Control-Allow-Origin: *)
- Open port and service discovery (Top 20 ports)
- Uses AI to prioritize and confirm false positives
"""

import socket
import logging
import requests
import concurrent.futures
from typing import Dict, Any, List, Set, Optional, Tuple

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 10.
    """
    logger.info(f"🛡️ Phase 10 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 5)
    max_threads = scan_config.get("max_threads", 10)
    
    # আগের ফেজ থেকে সাবডোমেইন ও আইপি নেওয়া
    prev_results = context.get("previous_results", {})
    all_subdomains = set()
    all_ips = set()
    
    # বিভিন্ন ফেজ থেকে সাবডোমেইন সংগ্রহ
    for phase_key in ["phase_1", "phase_6", "phase_8", "phase_9"]:
        phase_data = prev_results.get(phase_key, {})
        if phase_key == "phase_1":
            all_subdomains.update(phase_data.get("subdomains", []))
        elif phase_key == "phase_6":
            all_subdomains.update(phase_data.get("permutations", []))
        elif phase_key == "phase_8":
            all_subdomains.update(phase_data.get("found_subdomains", []))
        elif phase_key == "phase_9":
            all_subdomains.update(phase_data.get("subdomains", []))
    
    # ফেজ ২ ও ৭ থেকে আইপি
    phase2 = prev_results.get("phase_2", {})
    phase7 = prev_results.get("phase_7", {})
    if phase2.get("target_ip"):
        all_ips.add(phase2["target_ip"])
    all_ips.update(phase2.get("origin_ips", []))
    all_ips.update(phase7.get("live_hosts", []))
    
    all_subdomains = list(all_subdomains)[:100]
    all_ips = list(all_ips)[:20]
    
    result = {
        "target": target,
        "takeover_candidates": [],
        "cors_misconfigs": [],
        "open_ports": [],
        "ai_analysis": None,
        "errors": []
    }
    
    # =====================================================================
    # ১. সাবডোমেইন টেকওভার চেক
    # =====================================================================
    takeover_candidates = []
    logger.info(f"🔍 Checking {len(all_subdomains)} subdomains for takeover...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_sub = {executor.submit(_check_takeover, sub, timeout): sub for sub in all_subdomains}
        for future in concurrent.futures.as_completed(future_to_sub):
            sub = future_to_sub[future]
            try:
                is_vuln, details = future.result()
                if is_vuln:
                    takeover_candidates.append({"subdomain": sub, "details": details})
                    logger.warning(f"⚠️ Potential takeover: {sub}")
            except Exception as e:
                logger.debug(f"Takeover check error for {sub}: {e}")
    
    result["takeover_candidates"] = takeover_candidates
    
    # =====================================================================
    # ২. CORS মিসকনফিগ চেক
    # =====================================================================
    cors_issues = []
    targets_to_check = all_subdomains[:10] + [target]  # প্রথম ১০টি সাবডোমেইন + মূল ডোমেইন
    logger.info(f"🔍 Checking CORS for {len(targets_to_check)} targets...")
    
    for host in targets_to_check:
        url = f"https://{host}"
        try:
            # `Origin: https://evil.com` হেডার পাঠানো
            headers = {"Origin": "https://evil.com"}
            resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=False, verify=False)
            acao = resp.headers.get("Access-Control-Allow-Origin")
            acac = resp.headers.get("Access-Control-Allow-Credentials")
            
            if acao == "*" or acao == "https://evil.com":
                issue = {
                    "host": host,
                    "acao": acao,
                    "credentials": acac == "true",
                    "status_code": resp.status_code
                }
                cors_issues.append(issue)
                logger.warning(f"⚠️ CORS misconfig on {host}: ACAO={acao}")
        except Exception as e:
            logger.debug(f"CORS check error for {host}: {e}")
    
    result["cors_misconfigs"] = cors_issues
    
    # =====================================================================
    # ৩. ওপেন পোর্ট স্ক্যান (মূল টার্গেট ও লাইভ আইপি)
    # =====================================================================
    open_ports = []
    ports_to_scan = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 
                     995, 1723, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017]
    
    scan_targets = [target] + all_ips[:5]
    logger.info(f"🔍 Scanning ports for {len(scan_targets)} targets...")
    
    for target_ip in scan_targets:
        open_for_target = []
        for port in ports_to_scan:
            if _check_port(target_ip, port, timeout):
                open_for_target.append(port)
        if open_for_target:
            open_ports.append({
                "target": target_ip,
                "ports": open_for_target,
                "count": len(open_for_target)
            })
            logger.info(f"📡 {target_ip} has open ports: {open_for_target}")
    
    result["open_ports"] = open_ports
    
    # =====================================================================
    # ৪. AI দিয়ে ফলাফল অ্যানালাইসিস
    # =====================================================================
    if router:
        try:
            prompt = f"""
            Vulnerability scan results for {target}:
            - Subdomain takeover candidates: {len(takeover_candidates)}
            - CORS misconfigurations: {len(cors_issues)}
            - Open ports found: {sum(p['count'] for p in open_ports)}
            
            Provide:
            1. Which takeover candidates are most likely real?
            2. Criticality of CORS issues (any with credentials=True)?
            3. Recommended immediate actions for high-risk findings.
            """
            ai_response = router.route("vuln_analysis", prompt)
            if ai_response:
                result["ai_analysis"] = ai_response
                logger.info("✅ AI vulnerability analysis completed")
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
    
    logger.info(f"✅ Phase 10 complete. Takeover: {len(takeover_candidates)}, CORS: {len(cors_issues)}")
    return result


def _check_takeover(domain: str, timeout: int) -> Tuple[bool, Dict]:
    """
    সাবডোমেইন টেকওভার চেক: CNAME রেকর্ড খোঁজে এবং সেই CNAME-র IP/স্ট্যাটাস চেক করে
    """
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        
        # CNAME রেকর্ড খোঁজা
        try:
            answers = resolver.resolve(domain, 'CNAME')
            cname = str(answers[0].target).rstrip('.')
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return False, {}
        
        # CNAME পাওয়া গেলে, সেই ডোমেইনে HTTP রিকোয়েস্ট পাঠানো
        # (এটা নির্ভর করে লক্ষ্য সেবা ডাউন কিনা, যেমন: 404/403)
        try:
            resp = requests.get(f"https://{domain}", timeout=timeout, allow_redirects=False, verify=False)
            # 404 বা 503 প্রায়ই টেকওভারের নির্দেশক
            if resp.status_code in [404, 503, 403]:
                return True, {"cname": cname, "status_code": resp.status_code, "reason": "Dangling service"}
        except requests.exceptions.ConnectionError:
            # কোনো সার্ভার নেই => টেকওভার সম্ভব
            return True, {"cname": cname, "status_code": 0, "reason": "No server responding"}
        except:
            pass
        return False, {}
    except ImportError:
        # dns.resolver না থাকলে সকেট দিয়ে ডামি চেক
        logger.warning("dnspython not found, skipping detailed takeover check.")
        return False, {}
    except:
        return False, {}


def _check_port(host: str, port: int, timeout: int) -> bool:
    """পোর্ট ওপেন কিনা চেক"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except:
        return False