#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGGRESSIVE CLOUD SCANNER — S3 / GCS / Azure Public Bucket Discovery
- Scans 200+ dynamically generated bucket names (patterns + AI + permutations)
- Detects public buckets (200 OK) and listing-enabled buckets (XML/JSON)
- Uses StealthSession to avoid WAF/rate limits
- Fully Windows-native (no boto3 required, pure HTTP checks)
"""
import re
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from .http_client import StealthSession

logger = logging.getLogger("ZeroRecon")

class CloudScanner:
    def __init__(self, target: str, max_workers: int = 15):
        self.target = target
        self.session = StealthSession()
        self.max_workers = max_workers
        self.results = []
        self.cache_dir = Path("state/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "cloud_cache.json"
        self._load_cache()
        
    def _load_cache(self):
        """২৪ ঘন্টার ক্যাশ লোড করে (বারবার একই নাম চেক না করতে)"""
        self.cache = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    # ক্যাশ ভ্যালিডিটি চেক (২৪ ঘন্টা)
                    if data.get("timestamp", 0) > time.time() - 86400:
                        self.cache = data.get("entries", {})
                        logger.info(f"📦 Loaded {len(self.cache)} cached cloud entries")
            except: pass
    
    def _save_cache(self):
        """ক্যাশ সেভ করে"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    "timestamp": time.time(),
                    "entries": self.cache
                }, f, indent=2)
        except: pass

    def generate_bucket_names(self, custom_names: List[str] = None) -> Set[str]:
        """বাকেট নাম জেনারেট করে (আক্রমনাত্মক)"""
        base = self.target.replace('.', '-').replace('_', '-')
        patterns = set()
        
        # ১. কমন প্যাটার্ন (৫০+)
        common_prefixes = ["", "cdn-", "static-", "media-", "assets-", "files-", "data-", 
                          "backup-", "logs-", "uploads-", "download-", "temp-", "tmp-",
                          "dev-", "test-", "qa-", "stage-", "staging-", "prod-", "production-",
                          "internal-", "external-", "public-", "private-", "secure-",
                          "app-", "api-", "web-", "www-", "ftp-", "sftp-"]
        
        common_suffixes = ["", "-backup", "-logs", "-data", "-cdn", "-media", "-assets", 
                          "-static", "-files", "-uploads", "-temp", "-dev", "-test", "-prod"]
        
        for pref in common_prefixes:
            for suff in common_suffixes:
                name = f"{pref}{base}{suff}"
                if len(name) >= 3:
                    patterns.add(name)
        
        # ২. নম্বর ভ্যারিয়েন্ট (01-20)
        for i in range(1, 21):
            patterns.add(f"{base}-{i:02d}")
            patterns.add(f"cdn-{base}-{i:02d}")
        
        # ৩. ওয়াইল্ডকার্ড টাইপ (*.s3.amazonaws.com থেকে আইডিয়া)
        patterns.add(base)
        patterns.add(f"{base}-static")
        patterns.add(f"{base}-media")
        
        # ৪. যদি কাস্টম নাম (AI-র) থাকে, তা যোগ করি
        if custom_names:
            for name in custom_names:
                clean = name.replace('.', '-').replace('_', '-')
                patterns.add(clean)
        
        # ৫. মিনিমাম লেন্থ ফিল্টার
        valid = {p for p in patterns if 3 <= len(p) <= 63}
        logger.info(f"🌀 Generated {len(valid)} unique bucket names for scanning")
        return valid

    def scan_bucket(self, name: str) -> Dict:
        """একটি বাকেট স্ক্যান করে (S3/GCS/Azure)"""
        result = {"name": name, "provider": None, "url": None, "status": "not_found", "listing": False}
        
        # এড়িয়ে চলা (ইতিমধ্যে ক্যাশে থাকলে)
        cache_key = name
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # S3 (প্রথম পছন্দ)
        s3_url = f"https://{name}.s3.amazonaws.com"
        try:
            resp = self.session.get(s3_url, timeout=8)
            if resp.status_code == 200:
                result["provider"] = "aws_s3"
                result["url"] = s3_url
                result["status"] = "public"
                # XML পার্স করে লিস্টিং চেক (আরো ভালো)
                if "ListBucketResult" in resp.text or "Contents" in resp.text:
                    result["listing"] = True
                self.cache[cache_key] = result
                return result
            elif resp.status_code == 403:
                result["provider"] = "aws_s3"
                result["url"] = s3_url
                result["status"] = "private"
                self.cache[cache_key] = result
                return result
        except: pass

        # GCS (দ্বিতীয় পছন্দ)
        gcs_url = f"https://storage.googleapis.com/{name}"
        try:
            resp = self.session.get(gcs_url, timeout=8)
            if resp.status_code == 200:
                result["provider"] = "google_gcs"
                result["url"] = gcs_url
                result["status"] = "public"
                if "xmlns" in resp.text or "Contents" in resp.text:
                    result["listing"] = True
                self.cache[cache_key] = result
                return result
            elif resp.status_code == 403:
                result["provider"] = "google_gcs"
                result["url"] = gcs_url
                result["status"] = "private"
                self.cache[cache_key] = result
                return result
        except: pass

        # Azure (তৃতীয় পছন্দ)
        azure_url = f"https://{name}.blob.core.windows.net"
        try:
            resp = self.session.get(azure_url, timeout=8)
            if resp.status_code == 200:
                result["provider"] = "azure_blob"
                result["url"] = azure_url
                result["status"] = "public"
                if "EnumerationResults" in resp.text:
                    result["listing"] = True
                self.cache[cache_key] = result
                return result
            elif resp.status_code == 403:
                result["provider"] = "azure_blob"
                result["url"] = azure_url
                result["status"] = "private"
                self.cache[cache_key] = result
                return result
        except: pass

        # কিছুই পাওয়া যায়নি
        self.cache[cache_key] = result
        return result

    def scan_all(self, custom_names: List[str] = None) -> List[Dict]:
        """সমান্তরালে সব বাকেট স্ক্যান করে (আক্রমনাত্মক থ্রেডিং)"""
        names = self.generate_bucket_names(custom_names)
        logger.info(f"🚀 Scanning {len(names)} buckets with {self.max_workers} threads...")
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.scan_bucket, name): name for name in names}
            for future in as_completed(futures):
                try:
                    res = future.result()
                    if res["status"] == "public":
                        logger.info(f"📦 PUBLIC BUCKET: {res['name']} ({res['provider']}) - Listing: {res['listing']}")
                    elif res["status"] == "private":
                        logger.debug(f"🔒 Private bucket: {res['name']} ({res['provider']})")
                    results.append(res)
                except Exception as e:
                    logger.debug(f"Scan error: {e}")
        
        # ক্যাশ সেভ
        self._save_cache()
        
        # ফিল্টার: শুধু পাবলিক বা প্রাইভেট (ন্যাচারালি ফাউন্ড)
        public_results = [r for r in results if r["status"] in ["public", "private"]]
        logger.info(f"✅ Found {len(public_results)} accessible buckets ({len([r for r in public_results if r['status']=='public'])} public)")
        return results


def scan_cloud_buckets(target: str, custom_names: List[str] = None, max_workers: int = 15) -> List[Dict]:
    """গ্লোবাল ফাংশন — ফেজ ৫ ও ১৪ থেকে কল করা যাবে"""
    scanner = CloudScanner(target, max_workers)
    return scanner.scan_all(custom_names)