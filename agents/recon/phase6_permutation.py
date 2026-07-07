#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 6: Advanced DNS Permutation Attack
- Generates permutations of domain names
- Uses Levenshtein distance, common number/suffix patterns
- No AI needed (purely algorithmic)
- Outputs a list of potential subdomains/domains
"""

import logging
import itertools
from typing import Dict, Any, List, Set

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 6.
    Generates DNS permutations (subdomain takeovers, typos, etc.)
    """
    logger.info(f"🌀 Phase 6 started for: {target}")
    
    config = context.get("config", {})
    max_results = config.get("scan", {}).get("max_subdomains_to_scan", 100)
    
    result = {
        "target": target,
        "permutations": [],
        "total_generated": 0,
        "errors": []
    }
    
    # =====================================================================
    # ১. বেসিক পারমিউটেশন ডিকশনারি
    # =====================================================================
    # সাবডোমেইন প্রিফিক্স
    prefixes = [
        "www", "mail", "webmail", "smtp", "pop", "imap", "ns1", "ns2", "ftp",
        "api", "api2", "api3", "api-dev", "api-test", "api-staging", "api-prod",
        "admin", "administrator", "manage", "manager", "dashboard", "portal",
        "app", "app2", "app-dev", "app-test", "app-staging", "app-prod",
        "dev", "test", "stage", "staging", "qa", "prod", "production",
        "backup", "logs", "monitor", "status", "stats", "analytics",
        "cdn", "static", "assets", "media", "img", "images",
        "docs", "documentation", "wiki", "help", "support",
        "blog", "news", "press", "careers", "jobs",
        "partners", "vendors", "clients", "customer",
        "git", "jenkins", "jira", "confluence", "sonar", "nexus",
        "vpn", "remote", "office", "internal", "external",
        "mobile", "api-mobile", "m", "touch", "wap"
    ]
    
    # সংখ্যা ও সংক্ষিপ্ত ভ্যারিয়েন্ট
    numbers = ["", "1", "2", "3", "4", "5", "01", "02", "10", "20", "100", "200"]
    suffixes = ["", "-backup", "-dev", "-test", "-staging", "-prod", "-cdn", "-media", "-internal"]
    
    # =====================================================================
    # ২. পারমিউটেশন তৈরি
    # =====================================================================
    permutations = set()
    
    # কম্বিনেশন: prefix + target + suffix
    for prefix in prefixes[:30]:  # প্রথম ৩০টি প্রিফিক্স
        for suffix in suffixes[:5]:
            perm = f"{prefix}.{target}"
            permutations.add(perm)
            if suffix:
                perm_suf = f"{prefix}{suffix}.{target}"
                permutations.add(perm_suf)
            # সংখ্যা যোগ
            for num in numbers[:5]:
                permutations.add(f"{prefix}{num}.{target}")
    
    # টাইপো: ডব্লিউ → ডব্লিউডাব্লিউ, ইত্যাদি
    if "www" in target:
        permutations.add(target.replace("www", "ww"))
        permutations.add(target.replace("www", "w3"))
    
    # =====================================================================
    # ৩. ফিল্টার ও লিমিট
    # =====================================================================
    permutations_list = list(permutations)
    
    # 'target' নাম্বার এক্সট্রা ক্লিনিং
    final_permutations = []
    for p in permutations_list:
        # ডুপ্লিকেট বাদ, শর্ট সার্কিট
        if len(p) < 3:
            continue
        # '..' থাকলে বাদ
        if ".." in p:
            continue
        final_permutations.append(p)
    
    # লিমিট (কনফিগ থেকে)
    final_permutations = final_permutations[:max_results]
    result["permutations"] = final_permutations
    result["total_generated"] = len(final_permutations)
    
    logger.info(f"✅ Generated {len(final_permutations)} permutations")
    
    # =====================================================================
    # ৪. (ঐচ্ছিক) AI দিয়ে টপ পারমিউটেশন ফিল্টার
    # =====================================================================
    router = context.get("router")
    if router and final_permutations:
        try:
            prompt = f"""
            Target: {target}
            Generated {len(final_permutations)} DNS permutations.
            
            From this list, select the 10 most likely valid subdomains
            based on common infrastructure patterns.
            
            Permutations (sample): {final_permutations[:20]}
            """
            ai_filter = router.route("permutation_filter", prompt)
            if ai_filter:
                result["ai_filtered"] = ai_filter
                logger.info("✅ AI permutation filter applied")
        except Exception as e:
            logger.warning(f"AI filter failed: {e}")
    
    logger.info(f"✅ Phase 6 complete. Generated {result['total_generated']} permutations")
    return result