#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 7: ASN to IP Range and Host Mapping
- Takes ASN from Phase 2, expands to all IP ranges (CIDRs)
- Scans each range for live hosts (ICMP ping, TCP ports)
- Creates a network map with IPs, services, and reverse DNS
- Uses AI to prioritize high-value targets
"""

import socket
import logging
import ipaddress
import concurrent.futures
import subprocess
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 7.
    Requires ASN info from Phase 2 (stored in previous_results).
    """
    logger.info(f"🗺️ Phase 7 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 5)
    max_threads = scan_config.get("max_threads", 5)
    
    # আগের ফেজ থেকে ASN ডাটা নেওয়া
    prev_results = context.get("previous_results", {})
    phase2_data = prev_results.get("phase_2", {})
    prefixes = phase2_data.get("prefixes", [])
    asn = phase2_data.get("asn_info", {}).get("asn", "Unknown")
    
    result = {
        "target": target,
        "asn": asn,
        "total_ranges": len(prefixes),
        "live_hosts": [],
        "hosts_by_service": {},
        "ai_insights": None,
        "errors": []
    }
    
    if not prefixes:
        logger.warning("No IP ranges found. Skipping Phase 7.")
        result["errors"].append("No prefixes available")
        return result
    
    # =====================================================================
    # ১. আইপি রেঞ্জ থেকে লাইভ হোস্ট খোঁজা (ICMP Ping বা TCP Connect)
    # =====================================================================
    live_hosts: Set[str] = set()
    host_services: Dict[str, List[int]] = {}
    
    # মাত্র ৫টি সাবনেট নিচ্ছি (বড় ASN-এর জন্য লিমিট)
    for prefix in prefixes[:5]:
        try:
            network = ipaddress.ip_network(prefix, strict=False)
            # প্রথম ১০টি আইপি চেক (পাবলিক নেটওয়ার্কের জন্য)
            hosts_to_check = []
            for ip in list(network.hosts())[:10]:
                hosts_to_check.append(str(ip))
            
            logger.info(f"🔍 Scanning {len(hosts_to_check)} hosts in {prefix}")
            
            # সমান্তরালে স্ক্যান
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                future_to_ip = {executor.submit(_check_host, ip, timeout): ip for ip in hosts_to_check}
                for future in concurrent.futures.as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        is_live, ports = future.result()
                        if is_live:
                            live_hosts.add(ip)
                            if ports:
                                host_services[ip] = ports
                    except Exception as e:
                        logger.debug(f"Host check error for {ip}: {e}")
        except Exception as e:
            err_msg = f"Failed to scan prefix {prefix}: {e}"
            logger.warning(err_msg)
            result["errors"].append(err_msg)
    
    result["live_hosts"] = list(live_hosts)[:50]  # প্রথম ৫০টি
    result["hosts_by_service"] = host_services
    
    # =====================================================================
    # ২. AI দিয়ে উচ্চ-মূল্যের হোস্ট প্রায়োরিটাইজ
    # =====================================================================
    if router and result["live_hosts"]:
        try:
            prompt = f"""
            Network mapping results for {target} (ASN: {asn}):
            - Total IP ranges: {len(prefixes)}
            - Live hosts found: {len(result['live_hosts'])}
            - Hosts with open ports: {list(host_services.keys())[:10]}
            
            Provide:
            1. Which hosts are most likely critical (web servers, databases)?
            2. Suggested manual enumeration targets.
            3. Potential attack paths (from ASN to host).
            """
            ai_response = router.route("asn_mapping_insights", prompt)
            if ai_response:
                result["ai_insights"] = ai_response
                logger.info("✅ AI mapping insights received")
        except Exception as e:
            logger.warning(f"AI insights failed: {e}")
    
    logger.info(f"✅ Phase 7 complete. Live hosts: {len(result['live_hosts'])}")
    return result

def _check_host(ip: str, timeout: int) -> tuple:
    """
    চেক করে কোনো হোস্ট লাইভ কিনা, এবং কোন পোর্ট খোলা আছে।
    Returns: (is_live, [open_ports])
    """
    open_ports = []
    # পিং চেক (socket create_connection দিয়ে)
    try:
        socket.create_connection((ip, 80), timeout=timeout)
        open_ports.append(80)
    except:
        pass
    try:
        socket.create_connection((ip, 443), timeout=timeout)
        open_ports.append(443)
    except:
        pass
    try:
        socket.create_connection((ip, 22), timeout=timeout)
        open_ports.append(22)
    except:
        pass
    try:
        socket.create_connection((ip, 3389), timeout=timeout)
        open_ports.append(3389)
    except:
        pass
    
    is_live = bool(open_ports) or (socket.gethostbyaddr(ip) if ip else False)
    return is_live, open_ports