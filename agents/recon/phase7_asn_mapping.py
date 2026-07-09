#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 7 — ASN TO IP RANGE + HOST MAPPING (Level 5 — God-Tier)
- Debate Verdict: Skips if WAF risk is high (BLOCKED).
- MCTS Integration: Uses priority IPs from MCTS metadata.
- Parallel Host Scanning: ThreadPool for fast live host discovery.
- Smart Port Scanning: Checks common ports (80, 443, 22, 3389).
- AI-Powered Host Prioritization: Identifies critical hosts (web servers, databases).
"""

import socket
import logging
import ipaddress
import concurrent.futures
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

# ============================================================
#  কোর পোর্ট (দ্রুত স্ক্যানের জন্য)
# ============================================================
CORE_PORTS = [80, 443, 22, 3389, 3306, 6379, 5432, 8080, 8443]

# ============================================================
#  মেইন ফাংশন
# ============================================================
def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🗺️ Phase 7 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক (WAF বাইপাস)
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked Phase 7 (ASN Mapping). Skipping to avoid WAF detection.")
        return {
            "target": target,
            "status": "skipped",
            "reason": "Debate BLOCKED",
            "live_hosts": [],
            "hosts_by_service": {},
            "mcts_priority_used": False,
            "errors": []
        }

    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 5)
    max_workers = min(scan_config.get("max_threads", 10), 10)

    # =================================================================
    # ২. আগের ফেজ থেকে ASN প্রিফিক্স ও অরিজিন আইপি সংগ্রহ
    # =================================================================
    prev_results = context.get("previous_results", {})
    phase2 = prev_results.get("phase_2", {})
    prefixes = phase2.get("prefixes", [])
    asn = phase2.get("asn_info", {}).get("asn", "Unknown")
    origin_ips = phase2.get("origin_ips", [])

    # =================================================================
    # ৩. MCTS থেকে প্রায়োরিটি আইপি (যদি থাকে)
    # =================================================================
    mcts_path = context.get("mcts_path", {})
    priority_ips = mcts_path.get("metadata", {}).get("priority_ips", [])
    if priority_ips:
        logger.info(f"⭐ MCTS provided {len(priority_ips)} priority IPs.")

    result = {
        "target": target,
        "asn": asn,
        "total_ranges": len(prefixes),
        "live_hosts": [],
        "hosts_by_service": {},
        "mcts_priority_used": bool(priority_ips),
        "ai_insights": None,
        "errors": []
    }

    if not prefixes and not priority_ips and not origin_ips:
        logger.warning("No IP ranges or priority IPs available. Skipping.")
        result["errors"].append("No prefixes or priority IPs")
        return result

    # =================================================================
    # ৪. টার্গেট আইপি লিস্ট তৈরি (MCTS Priority -> Origin IPs -> Prefixes)
    # =================================================================
    targets_to_scan: Set[str] = set()

    # ৪a: MCTS Priority IPs (সর্বোচ্চ প্রায়োরিটি)
    if priority_ips:
        targets_to_scan.update(priority_ips[:10])

    # ৪b: Origin IPs (Phase 2 থেকে)
    if origin_ips:
        targets_to_scan.update(origin_ips[:10])

    # ৪c: Prefixes থেকে আইপি (সীমিত সংখ্যক)
    for prefix in prefixes[:5]:  # প্রথম ৫টি রেঞ্জ
        try:
            network = ipaddress.ip_network(prefix, strict=False)
            # প্রথম ১০টি হোস্ট (প্রায়োরিটি)
            for ip in list(network.hosts())[:10]:
                targets_to_scan.add(str(ip))
        except Exception as e:
            logger.debug(f"Prefix parse error {prefix}: {e}")

    # সীমাবদ্ধতা (max 100 টার্গেট)
    targets_to_scan = list(targets_to_scan)[:100]
    logger.info(f"🎯 Scanning {len(targets_to_scan)} targets (Priority: MCTS={bool(priority_ips)}, Origin={bool(origin_ips)})")

    # =================================================================
    # ৫. প্যারালাল হোস্ট স্ক্যান
    # =================================================================
    live_hosts: Set[str] = set()
    hosts_with_services: Dict[str, List[int]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ip = {
            executor.submit(_scan_host, ip, timeout): ip 
            for ip in targets_to_scan
        }
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                is_live, ports = future.result(timeout=timeout+5)
                if is_live:
                    live_hosts.add(ip)
                    if ports:
                        hosts_with_services[ip] = ports
                        # লাইভ হোস্টের সার্ভিস লগ
                        services = ", ".join([f"{p}" for p in ports])
                        logger.info(f"✅ Live host: {ip} (ports: {services})")
                    else:
                        logger.debug(f"✅ Live host: {ip} (no open core ports)")
            except Exception as e:
                logger.debug(f"Scan error for {ip}: {e}")

    result["live_hosts"] = list(live_hosts)[:50]
    result["hosts_by_service"] = hosts_with_services

    # =================================================================
    # ৬. AI-চালিত হোস্ট প্রায়োরিটাইজেশন (যদি রাউটার থাকে)
    # =================================================================
    if router and live_hosts:
        try:
            # শীর্ষ ১০টি হোস্টের তথ্য
            top_hosts = list(live_hosts)[:10]
            top_services = {ip: hosts_with_services.get(ip, []) for ip in top_hosts}
            prompt = f"""
            ASN Mapping results for {target} (ASN: {asn}):
            - Total live hosts: {len(live_hosts)}
            - Hosts with services: {len(hosts_with_services)}
            - Sample hosts: {top_hosts}
            - Sample services: {top_services}
            
            Provide:
            1. Which hosts are most critical (web servers, databases, admin panels)?
            2. Suggested manual enumeration targets.
            3. Potential attack paths.
            """
            ai_response = router.route("asn_mapping_insights", prompt)
            if ai_response:
                result["ai_insights"] = ai_response
                logger.info("✅ AI mapping insights received.")
        except Exception as e:
            logger.warning(f"AI insights failed: {e}")

    logger.info(f"✅ Phase 7 complete. Live hosts: {len(live_hosts)}")
    return result


# ============================================================
#  হেল্পার ফাংশন: হোস্ট স্ক্যান (প্যারালাল-রেডি)
# ============================================================
def _scan_host(ip: str, timeout: int) -> tuple:
    """
    Scan a single host for core ports.
    Returns: (is_live, [open_ports])
    """
    open_ports = []
    for port in CORE_PORTS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                open_ports.append(port)
        except:
            pass

    is_live = bool(open_ports)  # যেকোনো একটি পোর্ট ওপেন থাকলেই লাইভ
    # বিশেষ করে ৮০ বা ৪৪৩ ওপেন থাকলে নিশ্চিত লাইভ
    if 80 in open_ports or 443 in open_ports:
        is_live = True

    return is_live, open_ports
