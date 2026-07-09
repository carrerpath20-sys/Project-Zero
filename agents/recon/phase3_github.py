#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 3 — GITHUB RECONNAISSANCE (Level 5 — God-Tier)
- Debate Verdict: Skips if WAF risk is high (BLOCKED).
- MCTS Integration: Uses AI-predicted dork queries for targeted search.
- AI-Generated Advanced Dorks (if router available).
- GitHub API Search (code + repos).
- Advanced Secret Detection: AWS keys, tokens, private keys, passwords.
- Rate Limit Handling: Auto-sleep on 403/429 responses.
- Parallel: Searches multiple dorks in sequence with smart delays.
"""

import re
import time
import logging
import requests
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("ZeroRecon")

# ============================================================
#  অ্যাডভান্সড সিক্রেট ডিটেকশন প্যাটার্নস
# ============================================================
SECRET_PATTERNS = {
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret": r"[A-Za-z0-9/+=]{40}",
    "github_token": r"ghp_[A-Za-z0-9_]{36}",
    "github_old_token": r"gho_[A-Za-z0-9_]{36}",
    "private_key": r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
    "api_key": r"(?i)(api_key|apikey|secret_key|secret)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]{20,45}['\"]?",
    "password": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
    "token": r"(?i)(token|access_token|auth_token)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]{20,}['\"]?",
    "jwt": r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    "slack_webhook": r"https://hooks.slack.com/services/[A-Z0-9]+/[A-Z0-9]+/[A-Za-z0-9]+",
    "discord_webhook": r"https://discord.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]+",
    "mongodb_uri": r"mongodb(?:\+srv)?://[^:]+:[^@]+@[^/]+",
    "mysql_uri": r"mysql://[^:]+:[^@]+@[^/]+",
    "postgres_uri": r"postgres(?:ql)?://[^:]+:[^@]+@[^/]+",
    "redis_uri": r"redis://[^:]+:[^@]+@[^/]+"
}

# ============================================================
#  মেইন ফাংশন
# ============================================================
def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🐙 Phase 3 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক (WAF বাইপাস)
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked Phase 3 (GitHub). Skipping to avoid WAF detection.")
        return {
            "target": target,
            "status": "skipped",
            "reason": "Debate BLOCKED",
            "repositories": [],
            "secrets_found": [],
            "dorks_used": [],
            "mcts_used": False,
            "errors": []
        }

    router = context.get("router")
    config = context.get("config", {})
    scan_config = config.get("scan", {})
    timeout = scan_config.get("timeout", 10)

    # =================================================================
    # ২. MCTS থেকে প্রেডিক্টেড ডর্ক কোয়ারি
    # =================================================================
    mcts_path = context.get("mcts_path", {})
    mcts_dorks = mcts_path.get("metadata", {}).get("github_dorks", [])
    if mcts_dorks:
        logger.info(f"🧠 MCTS provided {len(mcts_dorks)} custom dork queries.")

    # =================================================================
    # ৩. বেসিক ডর্ক কোয়ারি
    # =================================================================
    base_dorks = [
        f'"{target}"',
        f'"{target}" filename:.env',
        f'"{target}" extension:json',
        f'"{target}" password',
        f'"{target}" api_key',
        f'"{target}" token',
        f'"{target}" secret',
        f'"{target}" key',
        f'"{target}" admin',
        f'"{target}" internal',
        f'org:{target}',
        f'repo:{target}'
    ]

    # =================================================================
    # ৪. AI-জেনারেটেড অ্যাডভান্সড ডর্ক
    # =================================================================
    ai_dorks = []
    if router:
        try:
            prompt = f"Generate 8 advanced GitHub dork queries for target '{target}' to find sensitive data, subdomains, and internal infrastructure. Output only the queries, one per line."
            ai_resp = router.route("github_advanced_dorks", prompt)
            if ai_resp:
                for line in ai_resp.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ai_dorks.append(line)
                logger.info(f"✅ AI generated {len(ai_dorks)} advanced dorks.")
        except Exception as e:
            logger.warning(f"AI dork generation failed: {e}")

    # =================================================================
    # ৫. ডর্ক লিস্ট তৈরি (MCTS -> AI -> Base)
    # =================================================================
    all_dorks = list(dict.fromkeys(mcts_dorks + ai_dorks + base_dorks))
    logger.info(f"📋 Total dorks: {len(all_dorks)} (MCTS: {len(mcts_dorks)}, AI: {len(ai_dorks)}, Base: {len(base_dorks)})")

    # =================================================================
    # ৬. GitHub API অনুসন্ধান (রেট-লিমিট সহ)
    # =================================================================
    found_repos: Set[str] = set()
    found_secrets: List[Dict] = []
    dorks_executed = []
    errors = []

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ZeroRecon-Framework"
    }

    for dork in all_dorks[:15]:  # প্রথম ১৫টি ডর্ক চেক (রেট লিমিটের জন্য)
        dorks_executed.append(dork)
        encoded_dork = dork.replace(" ", "+").replace('"', "%22")
        url = f"https://api.github.com/search/code?q={encoded_dork}&per_page=10"

        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            
            # রেট লিমিট হ্যান্ডলিং
            if resp.status_code == 403:
                if "rate limit" in resp.text.lower():
                    logger.warning("⚠️ GitHub API rate limit reached. Pausing 60s...")
                    time.sleep(60)
                    continue
                else:
                    logger.warning(f"⚠️ GitHub API 403: {resp.text[:100]}")
                    break

            if resp.status_code != 200:
                logger.debug(f"GitHub search returned {resp.status_code} for dork: {dork[:30]}...")
                continue

            data = resp.json()
            total_count = data.get("total_count", 0)
            if total_count > 0:
                logger.info(f"🔍 Dork '{dork[:40]}...' found {total_count} results")

                # ফাইল ও রিপো সংগ্রহ
                for item in data.get("items", [])[:10]:
                    repo = item.get("repository", {}).get("full_name", "unknown")
                    path = item.get("path", "unknown")
                    html_url = item.get("html_url", "")
                    found_repos.add(repo)

                    # =================================================================
                    # ৭. সিক্রেট ডিটেকশন (যদি ফাইলের কন্টেন্ট ছোট হয়)
                    # =================================================================
                    # রেট লিমিট এড়াতে আমরা শুধু প্রথম ৫টি ফাইলের কন্টেন্ট চেক করি
                    if len(found_secrets) < 10:
                        try:
                            # ফাইল কন্টেন্ট ডাউনলোড (raw)
                            raw_url = item.get("url", "").replace("https://api.github.com/repos", "https://raw.githubusercontent.com")
                            if raw_url:
                                # URL ট্রান্সফর্ম: /repos/user/repo/contents/path -> /user/repo/raw/path
                                raw_parts = raw_url.split("/contents/")
                                if len(raw_parts) == 2:
                                    raw_url = raw_parts[0].replace("api.github.com/repos", "raw.githubusercontent.com") + "/" + raw_parts[1]
                                    resp_content = requests.get(raw_url, timeout=timeout, headers=headers)
                                    if resp_content.status_code == 200:
                                        content = resp_content.text[:5000]  # প্রথম ৫০০০ অক্ষর
                                        for secret_type, pattern in SECRET_PATTERNS.items():
                                            matches = re.findall(pattern, content, re.IGNORECASE)
                                            if matches:
                                                found_secrets.append({
                                                    "type": secret_type,
                                                    "file": path,
                                                    "repo": repo,
                                                    "match": matches[0][:50] if isinstance(matches[0], str) else str(matches[0])[:50]
                                                })
                                                logger.warning(f"🔐 Secret found in {repo}/{path}: {secret_type}")
                                                break  # ফাইল প্রতি ১টি সিক্রেট লগ করলেই যথেষ্ট
                        except Exception as e:
                            logger.debug(f"File content fetch error: {e}")

            # GitHub API রেট লিমিট: ১ সেকেন্ড ডিলে
            time.sleep(1)

        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout for dork: {dork[:30]}...")
            continue
        except Exception as e:
            errors.append(f"Dork error: {e}")
            logger.debug(f"Error in dork {dork[:30]}: {e}")

    # =================================================================
    # ৮. ফলাফল
    # =================================================================
    result = {
        "target": target,
        "repositories": list(found_repos)[:50],
        "secrets_found": found_secrets[:20],
        "dorks_used": dorks_executed,
        "mcts_used": bool(mcts_dorks),
        "ai_dorks_used": bool(ai_dorks),
        "total_results": len(found_repos),
        "errors": errors
    }

    # =================================================================
    # ৯. AI সারাংশ (যদি সিক্রেট বা রিপো পাওয়া যায়)
    # =================================================================
    if router and (found_repos or found_secrets):
        try:
            prompt = f"""
            GitHub recon results for {target}:
            - Repositories found: {len(found_repos)}
            - Secrets found: {len(found_secrets)}
            - Sample secrets: {found_secrets[:3]}
            
            Provide:
            1. Most critical secrets (if any).
            2. Repositories that require immediate manual review.
            3. Suggested next steps.
            """
            ai_summary = router.route("github_summary", prompt)
            if ai_summary:
                result["ai_summary"] = ai_summary
                logger.info("✅ AI GitHub summary received.")
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")

    logger.info(f"✅ Phase 3 complete. Repos: {len(found_repos)}, Secrets: {len(found_secrets)}")
    return result
