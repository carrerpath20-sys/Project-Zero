#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1: Certificate Transparency Logs + TLS Fingerprinting + Subdomain Enumeration
- Fetches historical and current certificates from crt.sh
- Extracts subdomains from Subject Alternative Names (SAN)
- Grabs TLS fingerprints (SHA1, SHA256) and issuer details from ports 443, 8443
- Uses AI to analyze certificate chain for misconfigurations
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

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 1.
    context contains: router, config, previous_results (if any)
    """
    logger.info(f"🔍 Phase 1 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 10)
    retries = scan_config.get("retries", 3)
    ports = scan_config.get("ports", [443, 8443])
    
    result = {
        "target": target,
        "subdomains": [],
        "certificates": [],
        "fingerprints": [],
        "ai_analysis": None,
        "errors": []
    }
    
    # =====================================================================
    # ১. CT লগ ফেচ (crt.sh)
    # =====================================================================
    subdomains: Set[str] = set()
    try:
        url = f"https://crt.sh/?q=%25.{target}&output=json"
        for attempt in range(retries):
            try:
                resp = requests.get(url, timeout=timeout)
                if resp.status_code == 200:
                    certs = resp.json()
                    for cert in certs:
                        name = cert.get("name_value")
                        if name:
                            # ওয়াইল্ডকার্ড (*.example.com) -> .example.com
                            if name.startswith("*."):
                                name = name[2:]
                            for part in name.split("\n"):
                                part = part.strip()
                                if part and not part.startswith("*."):
                                    subdomains.add(part.lower())
                    logger.info(f"✅ Found {len(subdomains)} subdomains from crt.sh")
                    break
                else:
                    logger.warning(f"crt.sh attempt {attempt+1} failed: {resp.status_code}")
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"crt.sh attempt {attempt+1} error: {e}")
                time.sleep(2 ** attempt)
    except Exception as e:
        err_msg = f"CT log fetch failed: {e}"
        logger.error(err_msg)
        result["errors"].append(err_msg)
    
    result["subdomains"] = list(subdomains)
    
    # =====================================================================
    # ২. TLS ফিঙ্গারপ্রিন্ট + সার্টিফিকেট ডাউনলোড
    # =====================================================================
    for port in ports:
        cert_info = _get_tls_fingerprint(target, port, timeout)
        if cert_info:
            result["certificates"].append(cert_info)
            # SAN থেকে সাবডোমেইন বের করা
            for san in cert_info.get("san", []):
                if san[0] == "DNS":
                    subdomains.add(san[1].lower())
    
    # আপডেট করা সাবডোমেইন
    result["subdomains"] = list(subdomains)
    
    # =====================================================================
    # ৩. AI অ্যানালাইসিস (যদি রাউটার থাকে ও সার্টিফিকেট পাওয়া যায়)
    # =====================================================================
    if router and result["certificates"]:
        try:
            cert_sample = result["certificates"][0]
            prompt = f"""
            Analyze this TLS certificate for {target}:
            Issuer: {cert_sample.get('issuer', {})}
            SAN: {cert_sample.get('san', [])}
            SHA256: {cert_sample.get('sha256', '')}
            
            Provide a short security analysis (200 words max):
            1. Any misconfigurations?
            2. Hidden subdomains or internal IPs?
            3. Suggest attack vectors (SSL stripping, subdomain takeover).
            """
            ai_response = router.route("cert_analysis", prompt)
            if ai_response:
                result["ai_analysis"] = ai_response
                logger.info("✅ AI certificate analysis completed")
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
    
    logger.info(f"✅ Phase 1 complete. Subdomains: {len(result['subdomains'])}, Certs: {len(result['certificates'])}")
    return result


def _get_tls_fingerprint(domain: str, port: int, timeout: int) -> Optional[Dict]:
    """ডাউনলোড করে TLS সার্টিফিকেটের ফিঙ্গারপ্রিন্ট ও বিস্তারিত বের করে"""
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                der_cert = ssock.getpeercert(binary_form=True)
                
                if not cert:
                    return None
                
                return {
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                    "san": cert.get("subjectAltName", []),
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "sha1": hashlib.sha1(der_cert).hexdigest(),
                    "sha256": hashlib.sha256(der_cert).hexdigest(),
                    "port": port,
                    "version": ssock.version()
                }
    except Exception as e:
        logger.debug(f"TLS fingerprint failed on {domain}:{port} - {e}")
        return None
