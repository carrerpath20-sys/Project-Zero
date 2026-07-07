#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGGRESSIVE ASN LOOKUP — ipinfo.io + ip-api.com + WHOIS Fallback
- Primary: ipinfo.io (free, 1000/day, no key required)
- Fallback 1: ip-api.com (free, highly generous)
- Fallback 2: subprocess whois (Windows-native via sysinternals or cygwin, but mostly fails, so we keep it optional)
- Aggressive caching: 7 days to avoid hitting limits
"""
import os
import re
import json
import time
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger("ZeroRecon")

# ক্যাশ ডিরেক্টরি
CACHE_DIR = Path("state/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ASN_CACHE_FILE = CACHE_DIR / "asn_cache.json"

def _load_asn_cache() -> Dict:
    """ASN ক্যাশ লোড করে (৭ দিনের জন্য বৈধ)"""
    if not ASN_CACHE_FILE.exists():
        return {}
    try:
        with open(ASN_CACHE_FILE, 'r') as f:
            data = json.load(f)
            if data.get("timestamp", 0) > time.time() - (7 * 86400):  # ৭ দিন
                return data.get("entries", {})
    except: pass
    return {}

def _save_asn_cache(cache: Dict):
    """ASN ক্যাশ সেভ করে"""
    try:
        with open(ASN_CACHE_FILE, 'w') as f:
            json.dump({
                "timestamp": time.time(),
                "entries": cache
            }, f, indent=2)
    except: pass

def get_asn(ip: str) -> Dict:
    """
    একটি আইপি-র ASN ইনফো বের করে (আক্রমনাত্মক ক্যাশিং + ফ্যালব্যাক)
    রিটার্ন: {"asn": "AS13335", "org": "Cloudflare, Inc.", "country": "US", "city": "San Francisco"}
    """
    # ১. ক্যাশ চেক
    cache = _load_asn_cache()
    if ip in cache:
        logger.debug(f"✅ ASN cache hit for {ip}")
        return cache[ip]
    
    result = {"ip": ip, "asn": None, "org": None, "country": None, "city": None}
    
    # ২. ipinfo.io (প্রথম পছন্দ)
    try:
        resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            org = data.get("org", "")
            asn = org.split(" ")[0] if org and " " in org else None
            result.update({
                "asn": asn,
                "org": org,
                "country": data.get("country"),
                "city": data.get("city"),
                "region": data.get("region"),
                "hostname": data.get("hostname")
            })
            # ক্যাশে সেভ
            cache[ip] = result
            _save_asn_cache(cache)
            logger.info(f"🌐 ASN for {ip}: {asn} ({org})")
            return result
    except Exception as e:
        logger.debug(f"ipinfo.io failed for {ip}: {e}")

    # ৩. ip-api.com (ফ্যালব্যাক ১)
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                asn = data.get("as")
                result.update({
                    "asn": asn,
                    "org": data.get("isp") or data.get("org"),
                    "country": data.get("countryCode"),
                    "city": data.get("city"),
                    "region": data.get("regionName")
                })
                cache[ip] = result
                _save_asn_cache(cache)
                logger.info(f"🌐 (Fallback) ASN for {ip}: {asn}")
                return result
    except Exception as e:
        logger.debug(f"ip-api.com failed for {ip}: {e}")

    # ৪. WHOIS ফ্যালব্যাক (Windows-native - limited)
    try:
        if os.name == 'nt':
            # Windows-এ whois নেই ডিফল্ট, তাই আমরা socket গেটওয়ে ব্যবহার করি
            # অথবা আমরা এই অংশ স্কিপ করি, কারণ বেশিরভাগ উইন্ডোজে whois ইনস্টল নেই
            pass
        else:
            # Linux/Mac - whois কমান্ড
            output = subprocess.check_output(["whois", ip], text=True, timeout=5)
            for line in output.split("\n"):
                if "origin:" in line.lower() or "asn:" in line.lower():
                    asn = re.search(r'(AS\d+)', line)
                    if asn:
                        result["asn"] = asn.group(1)
                        break
    except Exception as e:
        logger.debug(f"WHOIS fallback failed: {e}")

    # শেষ পর্যন্ত কিছু না পেলে
    if not result["asn"]:
        logger.warning(f"⚠️ Could not retrieve ASN for {ip}. Returning empty.")
    
    cache[ip] = result
    _save_asn_cache(cache)
    return result

def get_prefixes(asn: str) -> List[str]:
    """
    একটি ASN-র সব IPv4 প্রিফিক্স বের করে (bgpview.io দিয়ে)
    """
    if not asn:
        return []
    
    asn_clean = asn.replace("AS", "")
    cache_key = f"prefix_{asn_clean}"
    cache = _load_asn_cache()
    
    if cache_key in cache:
        logger.debug(f"✅ Prefix cache hit for {asn}")
        return cache[cache_key]
    
    prefixes = []
    try:
        url = f"https://api.bgpview.io/asn/{asn_clean}/prefixes"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "ok":
                for item in data.get("data", {}).get("ipv4_prefixes", []):
                    prefix = item.get("prefix")
                    if prefix:
                        prefixes.append(prefix)
                logger.info(f"📡 Found {len(prefixes)} prefixes for ASN {asn}")
    except Exception as e:
        logger.warning(f"⚠️ BGPView prefix fetch failed: {e}")
    
    # ক্যাশে সেভ
    cache[cache_key] = prefixes
    _save_asn_cache(cache)
    return prefixes

def resolve_target_asn(domain: str) -> Dict:
    """
    ডোমেইন রেজলভ করে তার আইপি-র ASN বের করার শর্টকাট
    """
    try:
        ip = socket.gethostbyname(domain)
        return get_asn(ip)
    except Exception as e:
        logger.error(f"Domain resolution failed for {domain}: {e}")
        return {"error": str(e)}