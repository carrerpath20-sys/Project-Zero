#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 8: MassDNS and DNS Bruteforce
- Uses MassDNS (if installed) for high-speed DNS bruteforce
- Python fallback with dnspython if MassDNS not available
- Uses subdomain wordlist from config or built-in
- AI helps optimize wordlist for target
"""

import os
import re
import time
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 8.
    Brute-forces subdomains using DNS.
    """
    logger.info(f"🔍 Phase 8 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 5)
    
    result = {
        "target": target,
        "found_subdomains": [],
        "method_used": "none",
        "ai_optimized_wordlist": [],
        "errors": []
    }
    
    # =====================================================================
    # ১. ওয়ার্ডলিস্ট তৈরি / লোড
    # =====================================================================
    # বিল্ট-ইন ওয়ার্ডলিস্ট (শীর্ষ ৫০টি সাবডোমেইন)
    wordlist = [
        "www", "mail", "webmail", "smtp", "pop", "imap", "ns1", "ns2", "ftp",
        "api", "admin", "manage", "dashboard", "portal", "app", "dev", "test",
        "staging", "qa", "prod", "backup", "logs", "monitor", "status",
        "cdn", "static", "assets", "media", "img", "images", "docs", "wiki",
        "blog", "news", "press", "careers", "jobs", "partners", "vendors",
        "clients", "customer", "git", "jenkins", "jira", "confluence",
        "vpn", "remote", "office", "internal", "external"
    ]
    
    # AI দিয়ে অপটিমাইজড ওয়ার্ডলিস্ট (যদি রাউটার থাকে)
    if router:
        try:
            prompt = f"Generate 30 most likely subdomain names for '{target}' based on common infrastructure patterns. Output only the names, one per line."
            ai_wordlist = router.route("wordlist_gen", prompt)
            if ai_wordlist:
                for line in ai_wordlist.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        result["ai_optimized_wordlist"].append(line)
                logger.info(f"✅ AI generated {len(result['ai_optimized_wordlist'])} wordlist entries")
                # AI-র ওয়ার্ডলিস্টকে প্রাধান্য দিই
                combined_wordlist = list(set(wordlist + result["ai_optimized_wordlist"]))
                wordlist = combined_wordlist
        except Exception as e:
            logger.warning(f"AI wordlist generation failed: {e}")
    
    # =====================================================================
    # ২. MassDNS চেষ্টা (যদি ইনস্টল থাকে)
    # =====================================================================
    found_subdomains = set()
    massdns_path = _find_massdns()
    
    if massdns_path:
        logger.info("💨 MassDNS found — using high-speed mode")
        result["method_used"] = "massdns"
        
        # টেম্প ওয়ার্ডলিস্ট ফাইল তৈরি
        temp_wordlist = Path("temp_wordlist.txt")
        with open(temp_wordlist, 'w') as f:
            for sub in wordlist:
                f.write(f"{sub}.{target}\n")
        
        try:
            # MassDNS রান
            cmd = [massdns_path, "-r", "resolvers.txt", "-t", "A", "-o", "S", "-w", "massdns_results.txt", temp_wordlist]
            # রেজলভার ফাইল না থাকলে তৈরি করি
            if not Path("resolvers.txt").exists():
                with open("resolvers.txt", 'w') as f:
                    f.write("8.8.8.8\n1.1.1.1\n9.9.9.9\n")
            
            subprocess.run(cmd, timeout=30, capture_output=True)
            
            # ফলাফল পার্স
            if Path("massdns_results.txt").exists():
                with open("massdns_results.txt", 'r') as f:
                    for line in f:
                        if " A " in line:
                            sub = line.split(" ")[0].rstrip('.')
                            if sub != target:
                                found_subdomains.add(sub)
                logger.info(f"✅ MassDNS found {len(found_subdomains)} subdomains")
                
                # ক্লিনআপ
                os.remove("massdns_results.txt")
            else:
                logger.warning("MassDNS produced no output")
        except subprocess.TimeoutExpired:
            logger.warning("MassDNS timed out")
        except Exception as e:
            logger.warning(f"MassDNS error: {e}")
        finally:
            temp_wordlist.unlink(missing_ok=True)
    else:
        # =====================================================================
        # ৩. Python ফ্যালব্যাক (dnspython)
        # =====================================================================
        logger.info("🐍 MassDNS not found — using Python fallback (dnspython)")
        result["method_used"] = "python_fallback"
        
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.timeout = timeout
            resolver.lifetime = timeout
            
            for sub in wordlist[:50]:  # প্রথম ৫০টি
                domain = f"{sub}.{target}"
                try:
                    answers = resolver.resolve(domain, 'A')
                    if answers:
                        found_subdomains.add(domain)
                        logger.debug(f"✅ Found: {domain}")
                except dns.resolver.NXDOMAIN:
                    pass
                except dns.resolver.Timeout:
                    logger.debug(f"Timeout: {domain}")
                except Exception as e:
                    logger.debug(f"DNS error for {domain}: {e}")
                time.sleep(0.05)  # রেট লিমিট এভয়েড
        except ImportError:
            logger.warning("dnspython not installed. Using socket fallback.")
            # সকেট ফ্যালব্যাক (অত্যন্ত ধীর)
            import socket
            for sub in wordlist[:20]:
                domain = f"{sub}.{target}"
                try:
                    socket.gethostbyname(domain)
                    found_subdomains.add(domain)
                except:
                    pass
    
    result["found_subdomains"] = list(found_subdomains)[:100]
    
    # =====================================================================
    # ৪. ফলাফল এআই-তে পাঠানো (যদি রাউটার থাকে)
    # =====================================================================
    if router and result["found_subdomains"]:
        try:
            prompt = f"""
            DNS bruteforce results for {target}:
            - Method: {result['method_used']}
            - Subdomains found: {len(result['found_subdomains'])}
            - Sample: {result['found_subdomains'][:10]}
            
            Provide:
            1. Which subdomains are most interesting (admin, internal, api)?
            2. Suggest further enumeration targets.
            """
            ai_response = router.route("dns_summary", prompt)
            if ai_response:
                result["ai_analysis"] = ai_response
                logger.info("✅ AI DNS analysis received")
        except Exception as e:
            logger.warning(f"AI DNS analysis failed: {e}")
    
    logger.info(f"✅ Phase 8 complete. Found {len(result['found_subdomains'])} subdomains")
    return result

def _find_massdns() -> Optional[str]:
    """MassDNS বাইনারির পাথ খোঁজে (Windows/Linux)"""
    # Windows-এ massdns.exe খোঁজা
    paths = [
        "massdns",
        "massdns.exe",
        "./massdns",
        "./massdns.exe",
        "../massdns/massdns",
        "../massdns/massdns.exe"
    ]
    for path in paths:
        if Path(path).exists() or os.system(f"where {path} >nul 2>&1") == 0:
            return path
    return None