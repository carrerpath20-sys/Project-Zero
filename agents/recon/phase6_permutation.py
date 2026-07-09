#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 6 — ADVANCED DNS PERMUTATION (Level 5 — God-Tier)
- Debate Verdict: Skips if WAF risk is high (BLOCKED).
- MCTS Integration: Uses predicted permutation patterns from DNA.
- AI-Driven Dynamic Permutation: Learns naming patterns from live subdomains.
- Adaptive Wordlist: Generates permutations based on observed patterns.
- Multiple Strategies: Prefix/Suffix, Number Variations, Typos, Environment Tags.
"""

import re
import logging
import itertools
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

# ============================================================
#  মেইন ফাংশন
# ============================================================
def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🌀 Phase 6 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক (WAF বাইপাস)
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked Phase 6 (Permutation). Skipping to avoid WAF detection.")
        return {
            "target": target,
            "status": "skipped",
            "reason": "Debate BLOCKED",
            "permutations": [],
            "total_generated": 0,
            "mcts_used": False,
            "ai_patterns": []
        }

    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    max_results = scan_config.get("max_subdomains_to_scan", 200)

    # =================================================================
    # ২. আগের ফেজ থেকে লাইভ সাবডোমেইন সংগ্রহ (প্যাটার্ন শেখার জন্য)
    # =================================================================
    prev_results = context.get("previous_results", {})
    phase1 = prev_results.get("phase_1", {})
    live_subdomains = phase1.get("live_subdomains", [])
    all_subdomains = phase1.get("subdomains", [])

    # =================================================================
    # ৩. প্যাটার্ন অ্যানালাইসিস (AI + Heuristic)
    # =================================================================
    patterns = []
    mcts_patterns = []

    # ৩a: Heuristic Pattern Extraction (অফলাইন)
    if live_subdomains:
        patterns = _extract_heuristic_patterns(live_subdomains, target)
        logger.info(f"🧠 Heuristic patterns: {len(patterns)} patterns extracted.")

    # ৩b: MCTS Pattern Learning (যদি থাকে)
    mcts_path = context.get("mcts_path", {})
    mcts_patterns = mcts_path.get("metadata", {}).get("permutation_patterns", [])
    if mcts_patterns:
        logger.info(f"🧠 MCTS provided {len(mcts_patterns)} permutation patterns.")

    # ৩c: AI Pattern Learning (যদি রাউটার থাকে)
    ai_patterns = []
    if router and live_subdomains:
        try:
            sample = live_subdomains[:10]
            prompt = f"""
            Target: {target}
            Live subdomains: {sample}
            Generate 5 naming patterns (e.g., region-env-service, service-env-number).
            Output only the patterns, one per line.
            """
            ai_resp = router.route("permutation_patterns", prompt)
            if ai_resp:
                for line in ai_resp.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ai_patterns.append(line)
                logger.info(f"🧠 AI generated {len(ai_patterns)} patterns.")
        except Exception as e:
            logger.warning(f"AI pattern learning failed: {e}")

    # =================================================================
    # ৪. পারমিউটেশন জেনারেশন (মাল্টি-স্ট্র্যাটেজি)
    # =================================================================
    permutations = set()

    # ৪a: Heuristic পারমিউটেশন (কমন প্রিফিক্স/সাফিক্স)
    prefixes = [
        "www", "mail", "smtp", "pop", "imap", "ns1", "ns2", "ftp", "api",
        "admin", "manage", "dashboard", "portal", "app", "dev", "test",
        "stage", "staging", "qa", "prod", "production", "backup", "logs",
        "monitor", "status", "cdn", "static", "assets", "media", "img",
        "docs", "wiki", "blog", "news", "press", "careers", "jobs",
        "git", "jenkins", "jira", "confluence", "sonar", "nexus",
        "vpn", "remote", "office", "internal", "external"
    ]
    suffixes = ["", "-backup", "-dev", "-test", "-staging", "-prod", "-cdn", "-media", "-internal"]

    for prefix in prefixes[:50]:
        for suffix in suffixes:
            perm = f"{prefix}.{target}"
            permutations.add(perm)
            if suffix:
                permutations.add(f"{prefix}{suffix}.{target}")
            for num in ["01", "02", "03", "04", "05", "1", "2", "3", "4", "5"]:
                permutations.add(f"{prefix}{num}.{target}")

    # ৪b: Heuristic Pattern-Based (লাইভ সাবডোমেইন থেকে শেখা)
    for pattern in patterns:
        try:
            # প্যাটার্নে থাকা প্লেসহোল্ডার পূরণ করা
            if "{env}" in pattern:
                for env in ["dev", "test", "staging", "prod", "qa"]:
                    permutations.add(pattern.replace("{env}", env).format(target=target))
            elif "{region}" in pattern:
                for region in ["us-east", "us-west", "eu-west", "ap-south", "us-central"]:
                    permutations.add(pattern.replace("{region}", region).format(target=target))
            else:
                # সরাসরি ফরম্যাট
                try:
                    permutations.add(pattern.format(target=target))
                except:
                    pass
        except Exception as e:
            logger.debug(f"Pattern render error: {e}")

    # ৪c: MCTS Pattern-Based
    for pattern in mcts_patterns:
        try:
            if "{env}" in pattern:
                for env in ["dev", "test", "staging", "prod", "qa"]:
                    permutations.add(pattern.replace("{env}", env).format(target=target))
            else:
                permutations.add(pattern.format(target=target))
        except Exception as e:
            logger.debug(f"MCTS pattern error: {e}")

    # ৪d: AI Pattern-Based
    for pattern in ai_patterns:
        try:
            if "{env}" in pattern:
                for env in ["dev", "test", "staging", "prod", "qa"]:
                    permutations.add(pattern.replace("{env}", env).format(target=target))
            else:
                permutations.add(pattern.format(target=target))
        except Exception as e:
            logger.debug(f"AI pattern error: {e}")

    # ৪e: টাইপো ভ্যারিয়েন্ট
    if "www" in target:
        permutations.add(target.replace("www", "ww"))
        permutations.add(target.replace("www", "w3"))
        permutations.add(target.replace("www", "wwww"))

    # =================================================================
    # ৫. ফিল্টারিং (ডুপ্লিকেট, শর্ট, ইনভ্যালিড)
    # =================================================================
    filtered = []
    for p in permutations:
        if len(p) < 3: continue
        if ".." in p: continue
        if p.count(".") > 2: continue  # বেশি ডট থাকলে বাদ
        if p.startswith(".") or p.endswith("."): continue
        filtered.append(p)

    # লিমিট
    final_permutations = filtered[:max_results]

    # =================================================================
    # ৬. AI-চালিত ফিল্টার (যদি রাউটার থাকে)
    # =================================================================
    ai_filtered = []
    if router and final_permutations:
        try:
            sample = final_permutations[:20]
            prompt = f"""
            Target: {target}
            Generated {len(final_permutations)} DNS permutations.
            Sample: {sample}
            Return only the 10 most likely valid subdomains from the list.
            Output only the subdomains, one per line.
            """
            ai_resp = router.route("permutation_filter", prompt)
            if ai_resp:
                for line in ai_resp.strip().split("\n"):
                    line = line.strip().lower()
                    if line and line in final_permutations:
                        ai_filtered.append(line)
                logger.info(f"🧠 AI filtered to {len(ai_filtered)} high-probability permutations.")
        except Exception as e:
            logger.warning(f"AI filter failed: {e}")

    # =================================================================
    # ৭. ফলাফল
    # =================================================================
    result = {
        "target": target,
        "permutations": final_permutations[:200],
        "total_generated": len(final_permutations),
        "ai_filtered": ai_filtered[:20] if ai_filtered else [],
        "patterns_used": {
            "heuristic": len(patterns),
            "mcts": len(mcts_patterns),
            "ai": len(ai_patterns)
        },
        "mcts_used": bool(mcts_patterns),
        "ai_used": bool(ai_patterns or ai_filtered)
    }

    # =================================================================
    # ৮. AI সারাংশ (যদি পারমিউটেশন পাওয়া যায়)
    # =================================================================
    if router and final_permutations:
        try:
            prompt = f"""
            DNS Permutation results for {target}:
            - Total generated: {len(final_permutations)}
            - Patterns used: Heuristic({len(patterns)}), MCTS({len(mcts_patterns)}), AI({len(ai_patterns)})
            - AI-filtered: {len(ai_filtered)}
            
            Provide a short summary of the most promising permutations.
            """
            ai_summary = router.route("permutation_summary", prompt)
            if ai_summary:
                result["ai_summary"] = ai_summary
                logger.info("✅ AI permutation summary received.")
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")

    logger.info(f"✅ Phase 6 complete. Generated {len(final_permutations)} permutations, AI-filtered: {len(ai_filtered)}")
    return result


# ============================================================
#  হেল্পার ফাংশন
# ============================================================

def _extract_heuristic_patterns(subdomains: List[str], target: str) -> List[str]:
    """
    লাইভ সাবডোমেইন থেকে নেমিং প্যাটার্ন এক্সট্রাক্ট করে।
    যেমন: us-east-1.prod.api → region-env-service
    """
    patterns = set()
    for sub in subdomains[:30]:
        # টার্গেট বাদ
        if sub == target:
            continue
        # ডট দিয়ে স্প্লিট
        parts = sub.replace(f".{target}", "").split(".")
        if len(parts) >= 2:
            # প্যাটার্ন: region-env-service
            if len(parts) >= 3:
                patterns.add("{region}-{env}.{service}.{target}")
                patterns.add("{env}-{region}.{service}.{target}")
            elif len(parts) == 2:
                patterns.add("{env}.{service}.{target}")
                patterns.add("{service}-{env}.{target}")
            elif len(parts) == 1:
                patterns.add("{service}.{target}")
                patterns.add("{service}-{env}.{target}")
        # হাইফেন দিয়ে স্প্লিট
        elif "-" in sub:
            parts = sub.replace(f".{target}", "").split("-")
            if len(parts) >= 2:
                patterns.add("{env}-{service}.{target}")
                patterns.add("{service}-{env}.{target}")
    return list(patterns)[:10]
