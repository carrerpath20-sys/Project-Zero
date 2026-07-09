#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 4 — HISTORICAL DATA + GOD-TIER JS ANALYSIS (Level 5)
- Fetches 5000+ historical URLs from Wayback Machine (CDX API)
- Parallel JS/CSS/JSON download (ThreadPool: 10 workers)
- Auto-detects and downloads Source Maps (.map)
- Invokes Symbolic Engine (AST + Taint) for deep code analysis
- Caches results to avoid re-downloading across runs
- AI-powered executive summary of all discovered endpoints/params
"""

import re
import os
import json
import time
import hashlib
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("ZeroRecon")

# ------------------------------------------------------------
#  স্ট্যাটিক ডিপেন্ডেন্সি (ফোল্ডার)
# ------------------------------------------------------------
CACHE_DIR = Path("state/cache/js_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Level 5 Phase 4: Historical Data + JS God-Mode Analysis.
    """
    logger.info(f"📜 Phase 4 (Level 5) started for: {target}")

    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 30)
    max_workers = min(scan_config.get("max_threads", 10), 10)

    result = {
        "target": target,
        "wayback_urls": [],
        "js_files": [],
        "source_maps": [],
        "endpoints_found": [],
        "parameters_found": [],
        "secrets_found": [],
        "ai_analysis": None,
        "errors": []
    }

    # =====================================================================
    # ১. ওয়েব্যাক সিডিএক্স এপিআই (৫০০০ ইউআরএল)
    # =====================================================================
    wayback_urls = []
    try:
        url = f"https://web.archive.org/cdx/search/cdx?url=*.{target}/*&output=json&fl=original,timestamp&limit=5000"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 1:
                # প্রথম লাইন হেডার, বাকি ডাটা
                wayback_urls = [row[0] for row in data[1:]]
                logger.info(f"✅ Found {len(wayback_urls)} historical URLs")
            else:
                logger.warning("No historical URLs found")
        else:
            logger.warning(f"Wayback API returned {resp.status_code}")
    except Exception as e:
        err_msg = f"Wayback fetch failed: {e}"
        logger.error(err_msg)
        result["errors"].append(err_msg)

    result["wayback_urls"] = wayback_urls

    # =====================================================================
    # ২. স্মার্ট ফিল্টার (JS/JSON/TS/MAP)
    # =====================================================================
    js_urls = []
    map_urls = []
    for url in wayback_urls:
        ext = Path(url).suffix.lower()
        if ext in ['.js', '.mjs', '.ts']:
            js_urls.append(url)
        elif ext == '.map':
            map_urls.append(url)
        elif ext in ['.json', '.jsonp']:
            # আরও অ্যানালাইসিসের জন্য পাঠান
            js_urls.append(url)

    logger.info(f"📦 Found {len(js_urls)} JS/JSON files and {len(map_urls)} source maps.")

    # =====================================================================
    # ৩. জেএস অ্যানালাইসিস ইঞ্জিন লোড
    # =====================================================================
    js_analyzer = None
    symbolic_engine = None
    try:
        from tools.js_analyzer import JSAnalyzer
        from evo.symbolic import SymbolicEngine
        js_analyzer = JSAnalyzer(config)
        symbolic_engine = SymbolicEngine(config)
        logger.info("🧠 JSAnalyzer & SymbolicEngine loaded successfully.")
    except ImportError as e:
        logger.warning(f"⚠️ Advanced JS modules not loaded: {e}. Falling back to regex.")

    # =====================================================================
    # ৪. প্যারালাল জেএস ডাউনলোড ও অ্যানালাইসিস (আইকনিক)
    # =====================================================================
    endpoints = set()
    params = set()
    secrets = set()
    processed_js = []

    # সোর্স ম্যাপগুলোকে প্রায়োরিটি দিচ্ছি (কারণ এগুলোতে আসল কোড থাকে)
    urls_to_fetch = map_urls[:10] + js_urls[:30]  # মোট ৪০টি ফাইল

    if js_analyzer and symbolic_engine:
        logger.info(f"🚀 Analyzing {len(urls_to_fetch)} JS/map files in parallel...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(_analyze_js_file, url, target, js_analyzer, symbolic_engine, timeout): url for url in urls_to_fetch}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result_js = future.result(timeout=timeout+20)
                    if result_js:
                        processed_js.append(result_js)
                        endpoints.update(result_js.get("endpoints", []))
                        params.update(result_js.get("parameters", []))
                        secrets.update(result_js.get("secrets", []))
                        # সোর্স ম্যাপের রেজাল্ট আলাদা
                        if ".map" in url:
                            result["source_maps"].append(url)
                except Exception as e:
                    logger.debug(f"JS analysis error for {url}: {e}")
    else:
        # ফ্যালব্যাক: রেগেক্স
        logger.info("⚙️ Using fallback regex analysis...")
        for url in urls_to_fetch[:10]:
            try:
                resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    content = resp.text
                    ep = re.findall(r'["\'](/[^\s"\']+)["\']', content)
                    endpoints.update(ep)
                    sec = re.findall(r'(sk_live_|AKIA|ghp_|-----BEGIN)', content)
                    secrets.update(sec)
            except:
                pass

    result["js_files"] = processed_js
    result["endpoints_found"] = list(endpoints)[:100]
    result["parameters_found"] = list(params)[:50]
    result["secrets_found"] = list(secrets)[:20]

    logger.info(f"🔗 Extracted {len(endpoints)} endpoints, {len(params)} params, {len(secrets)} secrets from JS.")

    # =====================================================================
    # ৫. AI-চালিত সারাংশ (এক্সিকিউটিভ সামারি)
    # =====================================================================
    if router and (result["endpoints_found"] or result["parameters_found"]):
        try:
            prompt = f"""
            Historical JS analysis for {target}:
            - JS files scanned: {len(processed_js)}
            - Endpoints: {len(result['endpoints_found'])}
            - Parameters: {len(result['parameters_found'])}
            - Secrets: {len(result['secrets_found'])}
            Sample endpoints: {result['endpoints_found'][:10]}
            
            Provide:
            1. Top 5 critical hidden endpoints (admin, backup, internal).
            2. Any sensitive parameters (IDOR, Privesc risks).
            3. Immediate manual testing suggestions.
            """
            ai_response = router.route("historical_ai_summary", prompt)
            if ai_response:
                result["ai_analysis"] = ai_response
                logger.info("✅ AI historical summary received.")
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")

    logger.info(f"✅ Phase 4 complete. JS: {len(processed_js)}, Endpoints: {len(result['endpoints_found'])}")
    return result


# ============================================================
#  হেল্পার ফাংশন: জেএস অ্যানালাইসিস (প্যারালাল-রেডি)
# ============================================================
def _analyze_js_file(url: str, target: str, js_analyzer, symbolic_engine, timeout: int) -> Dict:
    """
    Individual JS file analysis with caching.
    """
    # ক্যাশ চেক
    cache_key = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
                logger.debug(f"💾 Cache hit for {url[:60]}...")
                return cached
        except:
            pass

    # ডাউনলোড
    fetch_result = js_analyzer.fetch(url, target)
    if fetch_result.get("error"):
        return {"url": url, "error": fetch_result["error"]}

    content = fetch_result.get("content", "")
    map_data = fetch_result.get("map")

    # সিম্বলিক অ্যানালাইসিস
    analysis = {"url": url, "endpoints": [], "parameters": [], "secrets": []}
    if content and symbolic_engine:
        try:
            # যদি সোর্স ম্যাপ থাকে, তবে আনমিনিফাইড কোড ব্যবহার করো
            if map_data and "sourcesContent" in map_data:
                # ম্যাপ থেকে আসল সোর্স বের করো
                sources = map_data.get("sourcesContent", [])
                if sources:
                    # প্রথম সোর্সটা নিয়ে কাজ করো (বেশিরভাগ ক্ষেত্রেই প্রধান ফাইল)
                    content = sources[0]
            # সিম্বলিক ইঞ্জিন চালাও
            sym_result = symbolic_engine.analyze(content, ast=None)  # এএসটি বাদ দিলেও চলে
            analysis["endpoints"] = sym_result.get("endpoints", [])
            analysis["parameters"] = sym_result.get("parameters", [])
            analysis["secrets"] = sym_result.get("secrets", [])
        except Exception as e:
            logger.debug(f"Symbolic analysis error for {url}: {e}")

    # ক্যাশে সেভ
    try:
        with open(cache_file, 'w') as f:
            json.dump(analysis, f, indent=2)
    except:
        pass

    return analysis
