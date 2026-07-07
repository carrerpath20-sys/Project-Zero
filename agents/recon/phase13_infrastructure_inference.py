#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 13: Infrastructure Inference & Predictive Permutation
- Groups IPs by ASN / /24 subnets to detect internal networks
- Learns naming patterns from live subdomains (e.g., us-east-1.prod.api)
- Uses AI once to predict new permutations based on pattern
- Entirely offline except 1 AI call for pattern learning
"""

import re
import json
import logging
import ipaddress
from collections import defaultdict
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🏗️ Phase 13 started for: {target}")
    
    router = context.get("router")
    prev_results = context.get("previous_results", {})
    
    # =====================================================================
    # ১. ইনপুট ডাটা সংগ্রহ (সাবডোমেইন ও আইপি)
    # =====================================================================
    all_subdomains = set()
    all_ips = set()
    
    for key in ["phase_1", "phase_6", "phase_8", "phase_9"]:
        data = prev_results.get(key, {})
        if key == "phase_1":
            all_subdomains.update(data.get("subdomains", []))
        elif key == "phase_6":
            all_subdomains.update(data.get("permutations", []))
        elif key == "phase_8":
            all_subdomains.update(data.get("found_subdomains", []))
        elif key == "phase_9":
            all_subdomains.update(data.get("subdomains", []))
    
    phase2 = prev_results.get("phase_2", {})
    phase7 = prev_results.get("phase_7", {})
    if phase2.get("target_ip"): all_ips.add(phase2["target_ip"])
    all_ips.update(phase2.get("origin_ips", []))
    all_ips.update(phase7.get("live_hosts", []))
    
    # DNS রেজলভ করে আরও IP বের করা
    import socket
    for sub in list(all_subdomains)[:20]:
        try:
            ip = socket.gethostbyname(sub)
            all_ips.add(ip)
        except: pass
    
    result = {
        "target": target,
        "internal_networks": [],
        "predicted_subdomains": [],
        "pattern_analysis": None,
        "status": "complete"
    }
    
    # =====================================================================
    # ২. ইন্টারনাল নেটওয়ার্ক গ্রুপিং (অফলাইন অ্যালগরিদম)
    # =====================================================================
    logger.info(f"📡 Grouping {len(all_ips)} IPs into networks...")
    subnet_groups = defaultdict(list)
    
    for ip in all_ips:
        try:
            # /24 সাবনেটে গ্রুপ (Class C)
            net = ipaddress.ip_network(f"{ip}/24", strict=False)
            subnet_groups[str(net)].append(ip)
        except: pass
    
    internal_networks = []
    for subnet, ips in subnet_groups.items():
        if len(ips) >= 2:  # অন্তত ২টি IP থাকলে সাবনেট ধরা হয়
            internal_networks.append({
                "subnet": subnet,
                "ips": ips[:10],  # প্রথম ১০টি IP
                "count": len(ips)
            })
            logger.info(f"🔗 Found internal subnet: {subnet} ({len(ips)} hosts)")
    
    result["internal_networks"] = internal_networks
    
    # =====================================================================
    # ৩. AI-চালিত প্যাটার্ন লার্নিং ও পারমিউটেশন (শুধু ১টি কল)
    # =====================================================================
    if router and all_subdomains:
        try:
            sample_subs = list(all_subdomains)[:30]
            prompt = f"""
            Target: {target}
            Sample subdomains: {sample_subs}
            
            Analyze the naming pattern. For example, if they use 'us-east-1.prod.api', then 'us-west-2.dev.api' should be predicted.
            Look for patterns like: region, environment (prod/dev/test), service (api/db/cdn).
            Generate 20 new, most likely valid subdomains based on this pattern.
            Output only the subdomains, one per line, no extra text.
            """
            ai_response = router.route("pattern_learning", prompt)
            
            if ai_response:
                predicted = []
                for line in ai_response.strip().split("\n"):
                    line = line.strip().lower()
                    if line and '.' in line and target in line and not line.startswith('#'):
                        predicted.append(line)
                
                result["predicted_subdomains"] = predicted[:30]
                result["pattern_analysis"] = "AI-analyzed pattern"
                logger.info(f"🧠 AI predicted {len(predicted)} new subdomains")
        except Exception as e:
            logger.warning(f"AI pattern learning failed: {e}")
    
    # =====================================================================
    # ৪. ফাইনাল রেজাল্ট
    # =====================================================================
    logger.info(f"✅ Phase 13 complete. Internal nets: {len(internal_networks)}, Predictions: {len(result['predicted_subdomains'])}")
    return result