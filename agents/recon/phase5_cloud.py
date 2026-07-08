#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5: Cloud Asset Discovery
- AWS S3 bucket discovery (public buckets)
- Google Cloud Storage (GCS) bucket discovery
- Azure Blob Storage discovery
- Uses common naming patterns + AI-generated guesses
- Checks for public access via HTTP requests
"""

import time
import logging
import requests
from typing import Dict, Any, List, Set

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 5.
    Discovers public cloud storage buckets using naming patterns.
    """
    logger.info(f"☁️ Phase 5 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    timeout = config.get("scan", {}).get("timeout", 10)
    
    result = {
        "target": target,
        "s3_buckets": [],
        "gcs_buckets": [],
        "azure_containers": [],
        "confirmed_public": [],
        "ai_generated_names": [],
        "errors": []
    }
    
    # =====================================================================
    # ১. নাম তৈরি করা (কমন প্যাটার্ন)
    # =====================================================================
    base_name = target.replace(".", "-").replace("_", "-")
    patterns = [
        base_name,
        f"{base_name}-backup",
        f"{base_name}-dev",
        f"{base_name}-test",
        f"{base_name}-prod",
        f"{base_name}-static",
        f"{base_name}-assets",
        f"{base_name}-media",
        f"{base_name}-files",
        f"{base_name}-data",
        f"assets.{target}",
        f"static.{target}",
        f"media.{target}",
        f"{target}-cdn",
        f"{target}-logs",
        f"{target}-uploads",
        f"{target}-temp",
        f"{target}-staging"
    ]
    
    # AI দিয়ে আরও নাম জেনারেট
    if router:
        try:
            prompt = f"Generate 10 possible S3 bucket names for target '{target}'. Use patterns like: backups, logs, static, media, cdn, dev, test, prod, internal. Output only the names, one per line."
            ai_names = router.route("bucket_names", prompt)
            if ai_names:
                for line in ai_names.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # URL-সেফ করা
                        clean = line.replace(".", "-").replace("_", "-")
                        result["ai_generated_names"].append(clean)
                logger.info(f"✅ AI generated {len(result['ai_generated_names'])} bucket names")
        except Exception as e:
            logger.warning(f"AI bucket name generation failed: {e}")
    
    all_names = list(set(patterns + result["ai_generated_names"]))
    
    # =====================================================================
    # ২. S3 বাকেট চেক
    # =====================================================================
    for name in all_names[:20]:  # প্রথম ২০টি চেক
        # S3: bucket-name.s3.amazonaws.com
        s3_url = f"https://{name}.s3.amazonaws.com"
        try:
            resp = requests.get(s3_url, timeout=timeout)
            if resp.status_code == 200:
                result["s3_buckets"].append({"name": name, "url": s3_url, "status": "public"})
                result["confirmed_public"].append(s3_url)
                logger.info(f"📦 Public S3 bucket: {name}")
            elif resp.status_code == 403:
                # Bucket exists but not public
                result["s3_buckets"].append({"name": name, "url": s3_url, "status": "private"})
                logger.debug(f"🔒 S3 bucket exists (private): {name}")
            elif resp.status_code == 404:
                pass  # Doesn't exist
        except Exception as e:
            logger.debug(f"S3 check error for {name}: {e}")
        
        # GCS: storage.googleapis.com/bucket-name
        gcs_url = f"https://storage.googleapis.com/{name}"
        try:
            resp = requests.get(gcs_url, timeout=timeout)
            if resp.status_code == 200:
                result["gcs_buckets"].append({"name": name, "url": gcs_url, "status": "public"})
                result["confirmed_public"].append(gcs_url)
                logger.info(f"📦 Public GCS bucket: {name}")
            elif resp.status_code == 403:
                result["gcs_buckets"].append({"name": name, "url": gcs_url, "status": "private"})
        except:
            pass
        
        # Azure: bucket-name.blob.core.windows.net
        azure_url = f"https://{name}.blob.core.windows.net"
        try:
            resp = requests.get(azure_url, timeout=timeout)
            if resp.status_code == 200:
                result["azure_containers"].append({"name": name, "url": azure_url, "status": "public"})
                result["confirmed_public"].append(azure_url)
                logger.info(f"📦 Public Azure container: {name}")
            elif resp.status_code == 403:
                result["azure_containers"].append({"name": name, "url": azure_url, "status": "private"})
        except:
            pass
        
        time.sleep(0.5)  # রেট লিমিট এভয়েড
    
    # =====================================================================
    # ৩. AI সারাংশ (যদি কিছু পাওয়া যায়)
    # =====================================================================
    if router and result["confirmed_public"]:
        try:
            prompt = f"""
            Cloud asset discovery for {target}:
            - Public S3 buckets: {len(result['s3_buckets'])}
            - Public GCS buckets: {len(result['gcs_buckets'])}
            - Public Azure containers: {len(result['azure_containers'])}
            - URLs: {result['confirmed_public'][:3]}
            
            Provide:
            1. Which assets are most likely sensitive?
            2. Suggested manual verification steps.
            3. Potential impact (data exposure, takeover).
            """
            ai_response = router.route("cloud_analysis", prompt)
            if ai_response:
                result["ai_analysis"] = ai_response
                logger.info("✅ AI cloud analysis completed")
        except Exception as e:
            logger.warning(f"AI cloud analysis failed: {e}")
    
    logger.info(f"✅ Phase 5 complete. Public assets found: {len(result['confirmed_public'])}")
    return result
