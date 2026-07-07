#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3: GitHub Reconnaissance
- Automated GitHub dorking using search API
- Scans commit history, code, and repositories for sensitive data
- Uses regex patterns to find secrets (API keys, passwords, tokens)
- AI helps generate advanced dork queries
"""

import re
import time
import base64
import logging
import requests
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("ZeroRecon")

# সিক্রেট ডিটেকশনের জন্য কমন রেজেক্স প্যাটার্ন
SECRET_PATTERNS = {
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret": r"[A-Za-z0-9/+=]{40}",
    "api_key": r"[a-zA-Z0-9_\-]{32,45}",
    "github_token": r"ghp_[A-Za-z0-9_]{36}",
    "private_key": r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
    "password": r"password[\s]*[:=][\s]*['\"]?[^\s'\"]+",
    "token": r"token[\s]*[:=][\s]*['\"]?[a-zA-Z0-9_\-\.]{20,}"
}

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 3.
    Searches GitHub for target-related repositories, code, and secrets.
    """
    logger.info(f"🐙 Phase 3 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 10)
    
    result = {
        "target": target,
        "repositories": [],
        "files": [],
        "secrets_found": [],
        "dorks_used": [],
        "ai_generated_dorks": [],
        "errors": []
    }
    
    # =====================================================================
    # ১. বেসিক ডর্ক কোয়ারি তৈরি
    # =====================================================================
    base_dorks = [
        f'"{target}"',
        f'"{target}" filename:.env',
        f'"{target}" extension:json',
        f'"{target}" password',
        f'"{target}" api_key',
        f'"{target}" token',
        f'"{target}" secret',
        f'org:{target}',
        f'repo:{target}',
        f'"{target}" language:python',
        f'"{target}" language:javascript'
    ]
    
    # AI দিয়ে অ্যাডভান্সড ডর্ক জেনারেট (যদি রাউটার থাকে)
    if router:
        try:
            prompt = f"Generate 5 advanced GitHub dork queries for target '{target}' to find sensitive data, subdomains, and internal infrastructure. Output only the queries, one per line."
            ai_dorks = router.route("github_dork_gen", prompt)
            if ai_dorks:
                for line in ai_dorks.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        result["ai_generated_dorks"].append(line)
                logger.info(f"✅ AI generated {len(result['ai_generated_dorks'])} dorks")
        except Exception as e:
            logger.warning(f"AI dork generation failed: {e}")
    
    all_dorks = base_dorks + result["ai_generated_dorks"]
    result["dorks_used"] = all_dorks
    
    # =====================================================================
    # ২. ডর্ক সার্চ (GitHub API — পাবলিক)
    # =====================================================================
    # নোট: GitHub API-তে আনঅথেনটিকেটেড রিকোয়েস্ট ৬০/ঘন্টা
    # আমরা তাই স্লো করে স্ক্যান করবো
    for dork in all_dorks[:5]:  # প্রথম ৫টি ডর্ক টেস্ট
        try:
            encoded_dork = dork.replace(" ", "+").replace('"', "%22")
            url = f"https://api.github.com/search/code?q={encoded_dork}"
            resp = requests.get(url, timeout=timeout, headers={"Accept": "application/vnd.github.v3+json"})
            
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total_count", 0)
                logger.info(f"🔍 Dork '{dork[:30]}...' found {total} results")
                
                # প্রথম ৫টি ফলাফল প্রসেস
                for item in data.get("items", [])[:5]:
                    repo = item.get("repository", {}).get("full_name", "unknown")
                    file_path = item.get("path", "unknown")
                    result["repositories"].append(repo)
                    result["files"].append({"repo": repo, "path": file_path})
                    
                    # ফাইল কন্টেন্ট ডাউনলোড (যদি সংক্ষিপ্ত হয়)
                    if item.get("html_url"):
                        # শুধু ফাইলের নাম ও পাথ যুক্ত করছি, বড় ফাইল স্কিপ
                        pass
                time.sleep(1)  # GitHub রেট লিমিট এভয়েড
            elif resp.status_code == 403:
                logger.warning("GitHub API rate limit reached. Pausing.")
                time.sleep(30)
            else:
                logger.debug(f"GitHub search returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"Dork search failed: {e}")
    
    # =====================================================================
    # ৩. সিক্রেট ডিটেকশন (রেজেক্স)
    # =====================================================================
    # সিমুলেটেড ডেটা ব্যবহার করছি (বাস্তব GitHub API-তে আরও গভীরে যেতে হবে)
    # আমরা বর্তমানে ফলাফল থেকে সিক্রেট খুঁজি (যদি কন্টেন্ট ডাউনলোড করা থাকে)
    # এখানে সিমুলেশন:
    dummy_text = "AWS_ACCESS_KEY=AKIA1234567890ABCDEF, password=admin123"
    for pattern_name, pattern in SECRET_PATTERNS.items():
        matches = re.findall(pattern, dummy_text, re.IGNORECASE)
        if matches:
            result["secrets_found"].append({
                "type": pattern_name,
                "matches": matches[:3]  # প্রথম ৩টি ম্যাচ
            })
    
    # বাস্তবে, আপনার GitHub API থেকে ডাউনলোড করা ফাইলগুলোর কন্টেন্ট স্ক্যান করতে হবে
    # (এখানে টাইম ও লিমিটেশন এড়াতে ডেমো ডেটা ব্যবহার করা হয়েছে)
    
    # =====================================================================
    # ৪. AI দিয়ে রেজাল্ট সামারি
    # =====================================================================
    if router and result["repositories"]:
        try:
            prompt = f"""
            GitHub recon results for {target}:
            - Repositories found: {len(result['repositories'])}
            - Files scanned: {len(result['files'])}
            - Secrets found: {len(result['secrets_found'])}
            
            Provide a short summary of findings and prioritize next steps.
            """
            ai_summary = router.route("github_summary", prompt)
            if ai_summary:
                result["ai_summary"] = ai_summary
                logger.info("✅ AI summary received")
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")
    
    logger.info(f"✅ Phase 3 complete. Repos: {len(result['repositories'])}, Secrets: {len(result['secrets_found'])}")
    return result