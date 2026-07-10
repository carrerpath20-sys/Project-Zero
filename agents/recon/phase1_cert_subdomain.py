#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 1 — CERT + SUBDOMAIN ENGINE (Level 5 — Robust Fallback)
- Configurable CT sources with per-source timeout.
- Sequential fallback: tries each source until one succeeds.
- If all fail, skips phase gracefully.
- MCTS-optimized wordlist integration.
- Parallel TLS fingerprinting and live checks.
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

# ডিফল্ট CT সোর্স (যদি config-এ না থাকে)
DEFAULT_SOURCES = [
    {"name": "certspotter", "url": "https://api.certspotter.com/v1/issuances?domain={target}&include_subdomains=true&expand=dns_names", "timeout": 20},
    {"name": "crt.sh_primary", "url": "https://crt.sh/?q={target}&output=json", "timeout": 25},
    {"name": "crt.sh_wildcard", "url": "https://crt.sh/?q=%25.{target}&output=json", "timeout": 25},
    {"name": "facebook_ct", "url": "https://graph.facebook.com/v19.0/ct?query=*.{target}&limit=100", "timeout": 15},
    {"name": "google_ct", "url": "https://transparencyreport.google.com/transparencyreport/api/v3/ct/ctsearch?domain={target}", "timeout": 15}
]

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🔍 Phase 1 (Robust Fallback) started for: {target}")

    # Debate verdict check
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
        "errors": [],
        "status": "complete"
    }

    # -----------------------------------------------------------------
    # ১. ফ্যালব্যাক সোর্স লিস্ট তৈরি (config থেকে অথবা ডিফল্ট)
    # -----------------------------------------------------------------
    fallback_config = config.get("service_fallback", {})
    sources = fallback_config.get("ct_sources", DEFAULT_SOURCES)
    skip_on_all_fail = fallback_config.get("skip_phase_on_all_fail", True)

    # -----------------------------------------------------------------
    # ২. এমসিটিএস ওয়ার্ডলিস্ট (যদি থাকে)
    # -----------------------------------------------------------------
    mcts_path = context.get("mcts_path", {})
    mcts_wordlist = mcts_path.get("metadata", {}).get("wordlist", [])
    if mcts_wordlist:
        logger.info(f"🧠 Using MCTS-optimized wordlist: {len(mcts_wordlist)} entries")

    # -----------------------------------------------------------------
    # ৩. সিকোয়েনশিয়াল ফ্যালব্যাক: প্রতিটি সোর্স চেষ্টা করো
    # -----------------------------------------------------------------
    all_subdomains: Set[str] = set()
    success = False

    for source in sources:
        name = source.get("name", "unknown")
        url_template = source.get("url")
        src_timeout = source.get("timeout", timeout)
        if not url_template:
            continue

        try:
            url = url_template.format(target=target)
            logger.info(f"⏳ Trying CT source: {name} (timeout: {src_timeout}s)")
            resp = requests.get(url, timeout=src_timeout)
            if resp.status_code != 200:
                logger.warning(f"⚠️ {name} returned {resp.status_code}. Trying next source.")
                continue

            # পার্স করার চেষ্টা
            data = resp.json()
            subs = _parse_ct_response(name, data)
            if subs:
                all_subdomains.update(subs)
                logger.info(f"✅ {name} found {len(subs)} subdomains")
                success = True
                break  # সফল হলে লুপ থেকে বেরিয়ে যাও
            else:
                logger.warning(f"⚠️ {name} returned empty data. Trying next source.")
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ {name} timed out. Trying next source.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ {name} request error: {e}. Trying next source.")
        except json.JSONDecodeError:
            logger.warning(f"⚠️ {name} returned invalid JSON. Trying next source.")
        except Exception as e:
            logger.warning(f"⚠️ {name} unexpected error: {e}. Trying next source.")

    # যদি কোনো সোর্স সফল না হয়
    if not success:
        logger.error(f"❌ All CT sources failed for {target}.")
        result["errors"].append("All CT sources failed.")
        if skip_on_all_fail:
            result["status"] = "skipped"
            logger.info("⏭️ Skipping Phase 1 due to all sources failing.")
            return result

    # MCTS ওয়ার্ডলিস্ট যোগ (যদি থাকে)
    if mcts_wordlist:
        all_subdomains.update(mcts_wordlist)

    # -----------------------------------------------------------------
    # ৪. TLS ফিঙ্গারপ্রিন্ট (প্যারালাল)
    # -----------------------------------------------------------------
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
            except Exception as e:
                logger.debug(f"TLS scan error on port {port}: {e}")

    result["certificates"] = certs

    # -----------------------------------------------------------------
    # ৫. লাইভ চেক (DNS + HTTP)
    # -----------------------------------------------------------------
    filtered = [s for s in all_subdomains if len(s) > 3 and not s.startswith("*")]
    live_subs = []
    if filtered:
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
    result["status"] = "complete"

    logger.info(f"✅ Phase 1 complete. Total: {len(result['subdomains'])}, Live: {len(result['live_subdomains'])}")
    return result


def _parse_ct_response(source_name: str, data: Any) -> Set[str]:
    """পার্স CT রেসপন্স (বিভিন্ন ফরম্যাটে) এবং সাবডোমেইন বের করে"""
    subs = set()
    try:
        if source_name in ["crt.sh_primary", "crt.sh_wildcard", "crt.sh"]:
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
            # generic fallback
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
        logger.debug(f"Parsing error for {source_name}: {e}")
    return subs


def _get_tls_fingerprint(domain: str, port: int, timeout: int) -> Optional[Dict]:
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
    try:
        socket.gethostbyname(domain)
        return True
    except:
        return False
