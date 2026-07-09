#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 15 — CONTINUOUS DIFF RECON (Level 5 — Smart & Lightweight)
- Uses state/snapshots/ folder for persistent storage.
- Tracks changes only for CRITICAL assets (from Phase 11).
- MCTS confidence boosts priority assets.
- Debate Verdict: Skips if BLOCKED.
- Lightweight: Only checks top 10 critical assets + homepage/robots.
- Auto-creates state/snapshots/ if missing.
"""

import os
import json
import hashlib
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set, Optional

from tools.http_client import stealth_request

logger = logging.getLogger("ZeroRecon")

# ডিফল্ট অ্যাসেট (সর্বদা চেক)
DEFAULT_ASSETS = ["/", "/robots.txt", "/sitemap.xml", "/favicon.ico", "/manifest.json"]

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🔄 Phase 15 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked Phase 15 (Diff). Skipping to avoid WAF.")
        return {
            "target": target,
            "status": "skipped",
            "reason": "Debate BLOCKED",
            "changes": [],
            "new_assets": [],
            "snapshot_path": None
        }

    config = context.get("config", {})
    timeout = config.get("scan", {}).get("timeout", 10)
    
    # =================================================================
    # ২. MCTS / Phase 11 থেকে ক্রিটিক্যাল অ্যাসেট সংগ্রহ
    # =================================================================
    prev_results = context.get("previous_results", {})
    phase11 = prev_results.get("phase_11", {})
    critical_assets = phase11.get("assets_by_priority", {}).get("critical", [])
    
    # Critical assets থেকে URL তৈরি
    critical_urls = []
    for sub in critical_assets[:5]:  # প্রথম ৫টি ক্রিটিক্যাল
        critical_urls.append(f"https://{sub}")
        critical_urls.append(f"https://{sub}/robots.txt")
        critical_urls.append(f"https://{sub}/sitemap.xml")
    
    # ডিফল্ট অ্যাসেট যোগ
    for default in DEFAULT_ASSETS:
        critical_urls.append(f"https://{target}{default}")
    
    # ডুপ্লিকেট বাদ, লিমিট (max 15 টি URL)
    url_list = list(set(critical_urls))[:15]
    logger.info(f"📸 Snapshotting {len(url_list)} critical assets...")

    # =================================================================
    # ৩. স্ন্যাপশট ডিরেক্টরি নিশ্চিতকরণ
    # =================================================================
    snapshot_dir = Path("state/snapshots")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshot_dir / f"{target}.json"

    # =================================================================
    # ৪. বর্তমান স্ন্যাপশট নেওয়া
    # =================================================================
    current_snapshot = {}
    for url in url_list:
        try:
            resp = stealth_request(url, timeout=timeout, verify=False)
            if resp.status_code == 200:
                content = resp.content
                current_snapshot[url] = {
                    "size": len(content),
                    "hash": hashlib.sha256(content).hexdigest(),
                    "status": resp.status_code,
                    "timestamp": datetime.now().isoformat()
                }
                logger.debug(f"📸 Snapshot: {url} ({len(content)} bytes)")
            else:
                # 404/403/500 - স্ট্যাটাস পরিবর্তন ট্র্যাক
                current_snapshot[url] = {
                    "size": 0,
                    "hash": "",
                    "status": resp.status_code,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.debug(f"Snapshot error for {url}: {e}")
            current_snapshot[url] = {
                "size": 0,
                "hash": "",
                "status": 0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    # =================================================================
    # ৫. আগের স্ন্যাপশটের সাথে তুলনা (ডিফ চেক)
    # =================================================================
    changes = []
    new_assets = []
    deleted_assets = []

    if snapshot_file.exists():
        try:
            with open(snapshot_file, 'r') as f:
                previous_snapshot = json.load(f)

            prev_urls = set(previous_snapshot.keys())
            curr_urls = set(current_snapshot.keys())

            # নতুন অ্যাসেট
            for url in curr_urls - prev_urls:
                if current_snapshot[url].get("status") == 200:
                    new_assets.append({
                        "url": url,
                        "size": current_snapshot[url]["size"],
                        "timestamp": current_snapshot[url]["timestamp"]
                    })
                    logger.info(f"🆕 New asset: {url}")

            # ডিলিটেড অ্যাসেট
            for url in prev_urls - curr_urls:
                deleted_assets.append({
                    "url": url,
                    "last_seen": previous_snapshot[url].get("timestamp", "unknown")
                })
                logger.warning(f"🗑️ Asset deleted: {url}")

            # পরিবর্তিত অ্যাসেট
            for url in curr_urls & prev_urls:
                prev = previous_snapshot[url]
                curr = current_snapshot[url]
                # স্ট্যাটাস পরিবর্তন (যেমন: ২০০ → ৪০৪)
                if prev.get("status") != curr.get("status"):
                    changes.append({
                        "url": url,
                        "change_type": "status_change",
                        "prev_status": prev.get("status"),
                        "curr_status": curr.get("status"),
                        "timestamp": curr.get("timestamp")
                    })
                    if curr.get("status") in [404, 503] and prev.get("status") == 200:
                        logger.warning(f"⚠️ Asset went down: {url} ({prev.get('status')} -> {curr.get('status')})")
                # কন্টেন্ট পরিবর্তন (হ্যাশ)
                elif prev.get("hash") and curr.get("hash") and prev.get("hash") != curr.get("hash"):
                    changes.append({
                        "url": url,
                        "change_type": "content_modified",
                        "prev_size": prev.get("size"),
                        "curr_size": curr.get("size"),
                        "size_diff": curr.get("size", 0) - prev.get("size", 0),
                        "timestamp": curr.get("timestamp")
                    })
                    if abs(curr.get("size", 0) - prev.get("size", 0)) > 1024:
                        logger.info(f"🔄 Content changed significantly: {url} ({prev.get('size')} -> {curr.get('size')} bytes)")

        except Exception as e:
            logger.warning(f"Snapshot comparison failed: {e}")

    # =================================================================
    # ৬. নতুন স্ন্যাপশট সেভ
    # =================================================================
    try:
        with open(snapshot_file, 'w') as f:
            json.dump(current_snapshot, f, indent=2, default=str)
        logger.info(f"💾 Snapshot saved: {snapshot_file}")
    except Exception as e:
        logger.warning(f"Snapshot save failed: {e}")

    # =================================================================
    # ৭. AI সারাংশ (যদি গুরুতর পরিবর্তন পাওয়া যায়)
    # =================================================================
    ai_summary = None
    router = context.get("router")
    if router and (changes or new_assets):
        try:
            prompt = f"""
            Diff scan results for {target}:
            - New assets: {len(new_assets)}
            - Deleted assets: {len(deleted_assets)}
            - Modified assets: {len(changes)}
            - Sample changes: {changes[:3]}
            
            Provide a short summary (150 words):
            1. What type of changes are most significant?
            2. Could these changes introduce new attack vectors?
            3. Recommend manual review priorities.
            """
            ai_resp = router.route("diff_summary", prompt)
            if ai_resp:
                ai_summary = ai_resp
                logger.info("✅ AI diff summary received.")
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")

    # =================================================================
    # ৮. রেজাল্ট
    # =================================================================
    result = {
        "target": target,
        "snapshot_file": str(snapshot_file),
        "total_assets": len(current_snapshot),
        "changes": changes[:10],
        "new_assets": new_assets[:10],
        "deleted_assets": deleted_assets[:10],
        "ai_summary": ai_summary,
        "status": "complete"
    }

    logger.info(f"✅ Phase 15 complete. Changes: {len(changes)}, New: {len(new_assets)}")
    return result
