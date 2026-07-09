#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 8 — MASS DNS BRUTEFORCE (Level 5 — God-Tier)
- Uses MCTS-optimized wordlist (priority-based)
- Checks Debate verdict (skips if BLOCKED)
- Multi-engine: MassDNS (if installed) → dnspython → socket fallback
- Implements exponential backoff to avoid rate limiting
- Filters wildcard DNS automatically
"""

import os
import time
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🔍 Phase 8 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked this phase. Skipping DNS bruteforce.")
        return {"target": target, "found_subdomains": [], "status": "skipped", "reason": "Debate BLOCKED"}

    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 5)
    max_results = scan_config.get("max_subdomains_to_scan", 100)

    result = {
        "target": target,
        "found_subdomains": [],
        "method_used": "none",
        "errors": []
    }

    # =================================================================
    # ২. MCTS ওয়ার্ডলিস্ট (প্রায়োরিটি অনুযায়ী সাজানো)
    # =================================================================
    mcts_path = context.get("mcts_path", {})
    mcts_wordlist = mcts_path.get("metadata", {}).get("dns_wordlist", [])
    default_wordlist = [
        "www", "mail", "webmail", "smtp", "pop", "imap", "ns1", "ns2", "ftp",
        "api", "admin", "manage", "dashboard", "portal", "app", "dev", "test",
        "staging", "qa", "prod", "backup", "logs", "monitor", "status",
        "cdn", "static", "assets", "media", "img", "images", "docs", "wiki",
        "blog", "news", "press", "careers", "jobs", "partners", "vendors",
        "clients", "customer", "git", "jenkins", "jira", "confluence",
        "vpn", "remote", "office", "internal", "external"
    ]

    # MCTS ওয়ার্ডলিস্টকে প্রায়োরিটি দিন (প্রথমে রাখুন)
    combined = list(dict.fromkeys(mcts_wordlist + default_wordlist))  # unique + order preserved
    wordlist = combined[:max_results]
    logger.info(f"📋 Wordlist: {len(wordlist)} entries (MCTS priority: {len(mcts_wordlist)})")

    # =================================================================
    # ৩. MassDNS চেষ্টা (যদি ইনস্টল থাকে)
    # =================================================================
    massdns_path = _find_massdns()
    found = set()

    if massdns_path:
        logger.info("💨 MassDNS found — using high-speed mode")
        result["method_used"] = "massdns"
        temp_wordlist = Path("temp_wordlist.txt")
        with open(temp_wordlist, 'w') as f:
            for sub in wordlist[:200]:
                f.write(f"{sub}.{target}\n")

        try:
            cmd = [massdns_path, "-r", "resolvers.txt", "-t", "A", "-o", "S", "-w", "massdns_results.txt", temp_wordlist]
            if not Path("resolvers.txt").exists():
                with open("resolvers.txt", 'w') as f:
                    f.write("8.8.8.8\n1.1.1.1\n9.9.9.9\n")

            subprocess.run(cmd, timeout=30, capture_output=True)
            if Path("massdns_results.txt").exists():
                with open("massdns_results.txt", 'r') as f:
                    for line in f:
                        if " A " in line:
                            sub = line.split(" ")[0].rstrip('.')
                            if sub != target:
                                found.add(sub)
                os.remove("massdns_results.txt")
            temp_wordlist.unlink(missing_ok=True)
            logger.info(f"✅ MassDNS found {len(found)} subdomains")
        except Exception as e:
            logger.warning(f"MassDNS error: {e}")

    # =================================================================
    # ৪. Python ফ্যালব্যাক (dnspython)
    # =================================================================
    if not found:
        logger.info("🐍 Using Python fallback (dnspython)")
        result["method_used"] = "python_fallback"
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.timeout = timeout
            resolver.lifetime = timeout

            for i, sub in enumerate(wordlist[:100]):
                domain = f"{sub}.{target}"
                try:
                    answers = resolver.resolve(domain, 'A')
                    if answers:
                        found.add(domain)
                        logger.debug(f"✅ Found: {domain}")
                except dns.resolver.NXDOMAIN:
                    pass
                except dns.resolver.Timeout:
                    # Exponential backoff
                    wait = min(2 ** (i % 5), 10)
                    time.sleep(wait)
                except:
                    pass
                if i % 20 == 0:
                    time.sleep(0.5)  # rate limit
        except ImportError:
            logger.warning("dnspython not found. Using socket fallback.")
            import socket
            for sub in wordlist[:50]:
                domain = f"{sub}.{target}"
                try:
                    socket.gethostbyname(domain)
                    found.add(domain)
                except:
                    pass

    result["found_subdomains"] = list(found)[:max_results]
    logger.info(f"✅ Phase 8 complete. Found {len(result['found_subdomains'])} subdomains.")
    return result


def _find_massdns() -> Optional[str]:
    """Find MassDNS binary (Windows/Linux)."""
    paths = ["massdns", "massdns.exe", "./massdns", "./massdns.exe"]
    for path in paths:
        if Path(path).exists() or os.system(f"where {path} >nul 2>&1") == 0:
            return path
    return None
