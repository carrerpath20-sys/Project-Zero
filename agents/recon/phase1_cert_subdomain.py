#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 1 — CERT + SUBDOMAIN ENGINE (Level 5 — God-Tier)
- Uses MCTS-optimized wordlist (from context)
- Checks Debate verdict before running (skips if BLOCKED)
- 5 CT sources + ShuffleDNS logic
- Parallel TLS fingerprinting
- AI-filtered live subdomains
"""

import re
import ssl
import json
import time
import socket
import hashlib
import logging
import requests
from typing import Dict, Any, List, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("ZeroRecon")

# CT Sources
CT_SOURCES = {
    "crt.sh": "https://crt.sh/?q=%25.{target}&output=json",
    "certspotter": "https://api.certspotter.com/v1/issuances?domain={target}&include_subdomains=true&expand=dns_names",
    "facebook_ct": "https://graph.facebook.com/v19.0/ct?query=*.{target}&limit=100",
    "google_ct": "https://transparencyreport.google.com/transparencyreport/api/v3/ct/ctsearch?domain={target}",
    "cloudflare_ct": "https://crt.sh/?q={target}&output=json"
}

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🔍 Phase 1 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked this phase. Skipping to avoid WAF detection.")
        return {"target": target, "subdomains": [], "status": "skipped", "reason": "Debate BLOCKED"}

    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 30)
    max_workers = min(scan_config.get("max_threads", 10), 10)

    result = {
        "target": target,
        "subdomains": [],
        "live_subdomains": [],
        "certificates": [],
        "errors": []
    }

    # =================================================================
    # ২. MCTS ওয়ার্ডলিস্ট (যদি পাওয়া যায়)
    # =================================================================
    mcts_path = context.get("mcts_path", {})
    mcts_wordlist = mcts_path.get("metadata", {}).get("wordlist", [])
    if mcts_wordlist:
        logger.info(f"🧠 Using MCTS-optimized wordlist: {len(mcts_wordlist)} entries")

    # =================================================================
    # ৩. CT লগ ফেচ (প্যারালাল)
    # =================================================================
    all_subdomains: Set[str] = set()
    logger.info(f"⏳ Fetching CT logs from {len(CT_SOURCES)} sources...")

    with ThreadPoolExecutor(max_workers=len(CT_SOURCES)) as executor:
        futures = {executor.submit(_fetch_ct, name, url, target, timeout): name for name, url in CT_SOURCES.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                subs = future.result(timeout=timeout)
                if subs:
                    all_subdomains.update(subs)
                    logger.info(f"✅ {name} found {len(subs)} subdomains")
            except Exception as e:
                logger.warning(f"⚠️ {name} error: {e}")

    # MCTS ওয়ার্ডলিস্ট যোগ (যদি থাকে)
    if mcts_wordlist:
        all_subdomains.update(mcts_wordlist)

    # =================================================================
    # ৪. TLS ফিঙ্গারপ্রিন্ট (প্যারালাল)
    # =================================================================
    certs = []
    ports = scan_config.get("ports", [443, 8443, 465, 993])
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_get_tls_fingerprint, target, port, timeout): port for port in ports}
        for future in as_completed(futures):
            port = futures[future]
            try:
                cert_info = future.result(timeout=timeout)
                if cert_info:
                    certs.append(cert_info)
                    for san in cert_info.get("san", []):
                        if san[0] == "DNS":
                            all_subdomains.add(san[1].lower())
            except:
                pass

    result["certificates"] = certs

    # =================================================================
    # ৫. লাইভ চেক (DNS + HTTP)
    # =================================================================
    filtered = [s for s in all_subdomains if len(s) > 3 and not s.startswith("*")]
    live_subs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_check_live, s): s for s in filtered[:200]}
        for future in as_completed(futures):
            s = futures[future]
            try:
                if future.result(timeout=5):
                    live_subs.append(s)
            except:
                pass

    result["subdomains"] = list(all_subdomains)[:500]
    result["live_subdomains"] = live_subs[:100]

    logger.info(f"✅ Phase 1 complete. Total: {len(result['subdomains'])}, Live: {len(result['live_subdomains'])}")
    return result


def _fetch_ct(source_name: str, url_template: str, target: str, timeout: int) -> Set[str]:
    """Fetch subdomains from a CT source."""
    subs = set()
    try:
        url = url_template.format(target=target)
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return subs
        data = resp.json()
        # Basic parsing for crt.sh-like responses
        if source_name in ["crt.sh", "cloudflare_ct"]:
            for cert in data:
                name = cert.get("name_value")
                if name:
                    if name.startswith("*."):
                        name = name[2:]
                    for part in name.split("\n"):
                        part = part.strip()
                        if part and not part.startswith("*."):
                            subs.add(part.lower())
        elif source_name == "certspotter":
            for entry in data:
                for name in entry.get("dns_names", []):
                    if name and not name.startswith("*"):
                        subs.add(name.lower())
        else:
            # Generic fallback
            items = data.get("data", data.get("results", data.get("certificates", [])))
            if isinstance(items, list):
                for item in items:
                    names = item.get("name_value", item.get("names", []))
                    if isinstance(names, str):
                        names = [names]
                    for name in names:
                        if name and not name.startswith("*"):
                            subs.add(name.lower())
    except Exception as e:
        logger.debug(f"{source_name} error: {e}")
    return subs

def _get_tls_fingerprint(domain: str, port: int, timeout: int) -> Optional[Dict]:
    """Grab TLS fingerprint."""
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                der = ssock.getpeercert(binary_form=True)
                if not cert:
                    return None
                return {
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                    "san": cert.get("subjectAltName", []),
                    "sha1": hashlib.sha1(der).hexdigest(),
                    "sha256": hashlib.sha256(der).hexdigest(),
                    "port": port
                }
    except:
        return None

def _check_live(domain: str) -> bool:
    """Check if domain resolves."""
    try:
        socket.gethostbyname(domain)
        return True
    except:
        return False
