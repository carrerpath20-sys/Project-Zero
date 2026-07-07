#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 15: Continuous Diff Recon (Content Change Tracking)
- Stores SHA256 + size snapshot of critical assets (homepage, robots, sitemap, JS/CSS)
- On next run, compares current with previous snapshot
- Flags new files, changed sizes, and modified content
- Uses AI only ONCE to summarize significant changes
"""

import os
import json
import hashlib
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

# ডিফল্ট অ্যাসেট চেক
DEFAULT_ASSETS = ["/", "/robots.txt", "/sitemap.xml", "/favicon.ico", "/manifest.json"]

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🔄 Phase 15 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    timeout = config.get("scan", {}).get("timeout", 10)
    
    prev_results = context.get("previous_results", {})
    phase4_urls = prev_results.get("phase_4", {}).get("wayback_urls", [])
    
    # জেএস/সিএসএস ফাইল খোঁজা (ওয়েব্যাক থেকে)
    js_css_urls = [u for u in phase4_urls if any(u.endswith(ext) for ext in ['.js', '.css', '.json'])]
    top_assets = list(DEFAULT_ASSETS) + js_css_urls[:5]
    
    result = {
        "target": target,
        "changes": [],
        "new_assets": [],
        "ai_summary": None,
        "status": "complete"
    }
    
    # =====================================================================
    # ১. স্ন্যাপশট ফাইল লোকেশন
    # =====================================================================
    snapshot_dir = Path("state/snapshots")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshot_dir / f"{target}.json"
    
    current_snapshot = {}
    for url in top_assets[:10]:
        try:
            full_url = url if url.startswith("http") else f"https://{target}{url}"
            resp = requests.get(full_url, timeout=timeout, verify=False)
            if resp.status_code == 200:
                content = resp.content
                current_snapshot[full_url] = {
                    "size": len(content),
                    "hash": hashlib.sha256(content).hexdigest(),
                    "status": resp.status_code
                }
                logger.debug(f"📸 Snapshot: {full_url} ({len(content)} bytes)")
        except Exception as e:
            logger.debug(f"Snapshot error for {url}: {e}")
    
    # =====================================================================
    # ২. আগের স্ন্যাপশটের সাথে তুলনা
    # =====================================================================
    changes = []
    new_assets = []
    
    if snapshot_file.exists():
        try:
            with open(snapshot_file, 'r') as f:
                previous_snapshot = json.load(f)
            
            # ডিফ চেক
            prev_urls = set(previous_snapshot.keys())
            curr_urls = set(current_snapshot.keys())
            
            # নতুন অ্যাসেট
            for url in curr_urls - prev_urls:
                new_assets.append({"url": url, "size": current_snapshot[url]["size"]})
                logger.info(f"🆕 New asset detected: {url}")
            
            # চেঞ্জ ডিটেক্ট
            for url in curr_urls & prev_urls:
                prev = previous_snapshot[url]
                curr = current_snapshot[url]
                if prev["hash"] != curr["hash"]:
                    changes.append({
                        "url": url,
                        "prev_size": prev["size"],
                        "curr_size": curr["size"],
                        "size_diff": curr["size"] - prev["size"],
                        "status": "content_modified"
                    })
                    logger.warning(f"🔄 Content changed: {url} ({prev['size']} -> {curr['size']} bytes)")
                elif prev["size"] != curr["size"]:
                    # হ্যাশ একই কিন্তু সাইজ ভিন্ন (কার্যত অসম্ভব, তবু)
                    pass
        except Exception as e:
            logger.warning(f"Snapshot comparison failed: {e}")
    
    # =====================================================================
    # ৩. নতুন স্ন্যাপশট সেভ
    # =====================================================================
    try:
        with open(snapshot_file, 'w') as f:
            json.dump(current_snapshot, f, indent=2)
        logger.info(f"💾 Snapshot saved: {snapshot_file}")
    except Exception as e:
        logger.warning(f"Snapshot save failed: {e}")
    
    result["changes"] = changes
    result["new_assets"] = new_assets
    
    # =====================================================================
    # ৪. AI সারাংশ (যদি কিছু পরিবর্তন পাওয়া যায়)
    # =====================================================================
    if router and (changes or new_assets):
        try:
            prompt = f"""
            Diff scan results for {target}:
            - New assets found: {len(new_assets)}
            - Modified assets: {len(changes)}
            - Sample changes: {changes[:3]}
            
            Provide a short summary (150 words):
            1. What type of changes are most significant?
            2. Could these changes introduce new attack vectors?
            3. Recommend manual review priorities.
            """
            ai_summary = router.route("diff_summary", prompt)
            if ai_summary:
                result["ai_summary"] = ai_summary
                logger.info("✅ AI diff summary received")
        except Exception as e:
            logger.warning(f"AI diff summary failed: {e}")
    
    logger.info(f"✅ Phase 15 complete. Changes: {len(changes)}, New: {len(new_assets)}")
    return result