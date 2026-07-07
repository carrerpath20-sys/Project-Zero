#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 9: Complete OSINT Recon Pipeline
- Aggregates data from all previous phases
- Creates a unified graph of IPs, domains, emails, subdomains
- Links assets together (e.g., IP -> domains hosted)
- Uses AI to identify hidden relationships and attack paths
"""

import json
import logging
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 9.
    Combines all previous phase results into a comprehensive OSINT graph.
    """
    logger.info(f"🔗 Phase 9 started for: {target}")
    
    router = context.get("router")
    prev_results = context.get("previous_results", {})
    
    # =====================================================================
    # ১. সব ফেজের ডাটা একত্রিত করা
    # =====================================================================
    aggregated = {
        "subdomains": set(),
        "ips": set(),
        "emails": set(),
        "asns": set(),
        "urls": set(),
        "cloud_assets": [],
        "vulnerabilities": [],
        "open_ports": [],
        "github_repos": []
    }
    
    # ফেজ ১: সাবডোমেইন
    phase1 = prev_results.get("phase_1", {})
    if phase1:
        aggregated["subdomains"].update(phase1.get("subdomains", []))
    
    # ফেজ ২: ASN ও IP
    phase2 = prev_results.get("phase_2", {})
    if phase2:
        asn_info = phase2.get("asn_info", {})
        if asn_info.get("asn"):
            aggregated["asns"].add(asn_info["asn"])
        if phase2.get("target_ip"):
            aggregated["ips"].add(phase2["target_ip"])
        aggregated["ips"].update(phase2.get("origin_ips", []))
    
    # ফেজ ৩: GitHub
    phase3 = prev_results.get("phase_3", {})
    if phase3:
        aggregated["github_repos"].extend(phase3.get("repositories", []))
    
    # ফেজ ৪: ওয়েব্যাক URL
    phase4 = prev_results.get("phase_4", {})
    if phase4:
        aggregated["urls"].update(phase4.get("wayback_urls", []))
    
    # ফেজ ৫: ক্লাউড অ্যাসেট
    phase5 = prev_results.get("phase_5", {})
    if phase5:
        aggregated["cloud_assets"].extend(phase5.get("confirmed_public", []))
    
    # ফেজ ৬: পারমিউটেশন
    phase6 = prev_results.get("phase_6", {})
    if phase6:
        aggregated["subdomains"].update(phase6.get("permutations", []))
    
    # ফেজ ৭: লাইভ হোস্ট
    phase7 = prev_results.get("phase_7", {})
    if phase7:
        aggregated["ips"].update(phase7.get("live_hosts", []))
    
    # ফেজ ৮: DNS ব্রুটফোর্স
    phase8 = prev_results.get("phase_8", {})
    if phase8:
        aggregated["subdomains"].update(phase8.get("found_subdomains", []))
    
    # ফেজ ১০: ভলনারেবিলিটি (যদি পরে যোগ হয়)
    # phase10 = prev_results.get("phase_10", {})
    
    # =====================================================================
    # ২. ডাটা ক্লিনিং ও ডিডুপ্লিকেশন
    # =====================================================================
    result = {
        "target": target,
        "subdomains": list(aggregated["subdomains"])[:200],
        "ips": list(aggregated["ips"])[:100],
        "emails": list(aggregated["emails"])[:20],
        "asns": list(aggregated["asns"]),
        "urls": list(aggregated["urls"])[:200],
        "cloud_assets": aggregated["cloud_assets"][:20],
        "github_repos": aggregated["github_repos"][:20],
        "graph": {},
        "ai_insights": None
    }
    
    # =====================================================================
    # ৩. গ্রাফ তৈরি (নোড ও এজ)
    # =====================================================================
    graph = {
        "nodes": [],
        "edges": []
    }
    
    # নোড যোগ
    for sub in result["subdomains"][:30]:
        graph["nodes"].append({"id": sub, "type": "subdomain"})
    for ip in result["ips"][:20]:
        graph["nodes"].append({"id": ip, "type": "ip"})
    for asn in result["asns"]:
        graph["nodes"].append({"id": asn, "type": "asn"})
    for url in result["urls"][:20]:
        graph["nodes"].append({"id": url[:50], "type": "url"})
    
    # এজ (সাবডোমেইন -> IP, ASN -> IP, ইত্যাদি)
    # ডেমো: সাবডোমেইন থেকে IP ম্যাপিং (বাস্তবে DNS রেজলভ করা লাগবে)
    if result["subdomains"] and result["ips"]:
        for i, sub in enumerate(result["subdomains"][:10]):
            ip = result["ips"][i % len(result["ips"])]
            graph["edges"].append({"source": sub, "target": ip, "type": "resolves_to"})
    
    result["graph"] = graph
    
    # =====================================================================
    # ৪. AI দিয়ে ইনসাইট & অ্যাটাক পাথ
    # =====================================================================
    if router:
        try:
            prompt = f"""
            OSINT pipeline results for {target}:
            - Subdomains: {len(result['subdomains'])}
            - IPs: {len(result['ips'])}
            - ASNs: {len(result['asns'])}
            - URLs: {len(result['urls'])}
            - Cloud assets: {len(result['cloud_assets'])}
            - GitHub repos: {len(result['github_repos'])}
            
            Provide:
            1. Top 3 critical assets (most likely high-value).
            2. Suggested attack paths (e.g., subdomain takeover, cloud misconfig).
            3. Overall risk score (1-10) and justification.
            4. Next steps for manual testing.
            """
            ai_response = router.route("osint_insights", prompt)
            if ai_response:
                result["ai_insights"] = ai_response
                logger.info("✅ AI OSINT insights received")
        except Exception as e:
            logger.warning(f"AI insights failed: {e}")
    
    logger.info(f"✅ Phase 9 complete. Graph nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")
    return result