#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 14: Supply Chain & Third-Party Asset Tracking + Metadata Harvester
- Scans DNS records (CNAME, TXT, SPF) to detect Vercel, Supabase, Shopify, AWS
- Checks dangling CNAMEs (404/503) for takeover alerts
- Downloads public PDF/DOCX/XLSX files from Wayback/Live site
- Extracts metadata (Author, OS, Software) using local libraries
- 0 API calls (all local processing + HTTP/DNS requests)
"""

import os
import re
import socket
import logging
import requests
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple

logger = logging.getLogger("ZeroRecon")

# Third-party service detection patterns (CNAME/TXT)
SERVICE_PATTERNS = {
    "vercel": ["cname.vercel-dns.com", "vercel-dns.com"],
    "supabase": ["supabase.co", "supabase.in"],
    "shopify": ["shopify.com", "myshopify.com"],
    "netlify": ["netlify.com", "netlify.app"],
    "aws_cloudfront": ["cloudfront.net"],
    "github_pages": ["github.io"],
    "heroku": ["herokuapp.com"],
    "azure": ["azurewebsites.net"],
    "fastly": ["fastly.net"]
}

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🔗 Phase 14 started for: {target}")
    
    router = context.get("router")
    config = context.get("config", {})
    timeout = config.get("scan", {}).get("timeout", 10)
    
    prev_results = context.get("previous_results", {})
    phase4_urls = prev_results.get("phase_4", {}).get("wayback_urls", [])
    
    result = {
        "target": target,
        "detected_services": [],
        "dangling_domains": [],
        "metadata": [],
        "ai_summary": None,
        "errors": []
    }
    
    # =====================================================================
    # ১. DNS রেকর্ড অ্যানালাইসিস (CNAME, TXT, SPF)
    # =====================================================================
    dns_services = []
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        
        # CNAME চেক
        try:
            answers = resolver.resolve(target, 'CNAME')
            for rdata in answers:
                cname = str(rdata.target).rstrip('.')
                for service, patterns in SERVICE_PATTERNS.items():
                    if any(p in cname for p in patterns):
                        dns_services.append({"type": service, "record": "CNAME", "value": cname})
                        logger.info(f"🔍 Detected {service} via CNAME: {cname}")
        except: pass
        
        # TXT রেকর্ড চেক
        try:
            answers = resolver.resolve(target, 'TXT')
            for rdata in answers:
                txt_value = str(rdata).lower()
                if "spf" in txt_value:
                    if "google" in txt_value: 
                        dns_services.append({"type": "gmail_workspace", "record": "TXT", "value": txt_value[:50]})
                    if "amazon" in txt_value:
                        dns_services.append({"type": "aws_ses", "record": "TXT", "value": txt_value[:50]})
        except: pass
    except ImportError:
        logger.warning("dnspython not installed. Skipping DNS analysis.")
        result["errors"].append("dnspython not installed")
    
    result["detected_services"] = dns_services
    
    # =====================================================================
    # ২. ড্যাংলিং চেক (CNAME + HTTP ৪০৪/৫০৩)
    # =====================================================================
    dangling = []
    for service in dns_services:
        if service["record"] == "CNAME":
            cname = service["value"]
            try:
                resp = requests.get(f"https://{cname}", timeout=timeout, verify=False)
                if resp.status_code in [404, 503, 403]:
                    dangling.append({
                        "domain": cname,
                        "service": service["type"],
                        "status": resp.status_code,
                        "alert": "Possible takeover vulnerability"
                    })
                    logger.warning(f"⚠️ Dangling CNAME detected: {cname} -> {resp.status_code}")
            except requests.exceptions.ConnectionError:
                dangling.append({
                    "domain": cname,
                    "service": service["type"],
                    "status": 0,
                    "alert": "No server responding (takeover likely)"
                })
                logger.warning(f"⚠️ Dangling CNAME: {cname} (no server)")
            except: pass
    
    result["dangling_domains"] = dangling
    
    # =====================================================================
    # ৩. মেটাডেটা হার্ভেস্ট (PDF/DOCX/XLSX)
    # =====================================================================
    metadata_results = []
    file_extensions = ['.pdf', '.docx', '.xlsx', '.doc', '.xls']
    target_urls = []
    
    # লাইভ সাইট থেকে ফাইল লিংক খোঁজা (বা Wayback থেকে)
    for url in phase4_urls[:100]:
        for ext in file_extensions:
            if ext in url.lower():
                target_urls.append(url)
                break
    
    target_urls = target_urls[:10]  # প্রথম ১০টি ফাইল
    logger.info(f"📁 Downloading and analyzing {len(target_urls)} files...")
    
    for file_url in target_urls:
        try:
            resp = requests.get(file_url, timeout=timeout, stream=True, verify=False)
            if resp.status_code != 200: continue
            
            # ফাইল সাইজ লিমিট (২MB)
            content = resp.content
            if len(content) > 2 * 1024 * 1024: continue
            
            # টেম্প ফাইল
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_url).suffix) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            # এক্সট্রাক্ট
            meta = _extract_metadata(tmp_path, Path(file_url).suffix)
            if meta:
                metadata_results.append({
                    "url": file_url[:100],
                    "filename": Path(file_url).name,
                    "metadata": meta
                })
                logger.info(f"📄 Extracted metadata from {Path(file_url).name}")
            
            os.unlink(tmp_path)
        except Exception as e:
            logger.debug(f"Metadata extraction failed for {file_url}: {e}")
    
    result["metadata"] = metadata_results
    
    # =====================================================================
    # ৪. AI সারাংশ (যদি রাউটার থাকে)
    # =====================================================================
    if router and (dangling or metadata_results):
        try:
            prompt = f"""
            Supply chain analysis for {target}:
            - Services: {[s['type'] for s in dns_services]}
            - Dangling domains: {len(dangling)}
            - Metadata extracted from files: {len(metadata_results)}
            
            Provide a short summary (150 words) prioritizing:
            1. Most critical takeover risks.
            2. Any sensitive data leaked in metadata (usernames, software versions).
            3. Recommended immediate actions.
            """
            ai_summary = router.route("supply_chain_summary", prompt)
            if ai_summary:
                result["ai_summary"] = ai_summary
                logger.info("✅ AI supply chain summary received")
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")
    
    logger.info(f"✅ Phase 14 complete. Services: {len(dns_services)}, Metadata: {len(metadata_results)}")
    return result

def _extract_metadata(file_path: str, ext: str) -> Dict:
    """স্থানীয় লাইব্রেরি দিয়ে মেটাডেটা বের করে"""
    meta = {}
    try:
        if ext == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    info = reader.metadata
                    if info:
                        for k, v in info.items():
                            if v:
                                meta[k] = str(v)
            except ImportError: pass
        elif ext in ['.docx', '.doc']:
            try:
                import docx
                doc = docx.Document(file_path)
                core_props = doc.core_properties
                if core_props:
                    for prop in ['author', 'last_modified_by', 'created', 'modified', 'company']:
                        val = getattr(core_props, prop, None)
                        if val:
                            meta[prop] = str(val)
            except ImportError: pass
        elif ext in ['.xlsx', '.xls']:
            try:
                from openpyxl import load_workbook
                wb = load_workbook(file_path, data_only=True)
                props = wb.properties
                if props:
                    for prop in ['creator', 'lastModifiedBy', 'created', 'modified', 'company']:
                        val = getattr(props, prop, None)
                        if val:
                            meta[prop] = str(val)
            except ImportError: pass
    except Exception as e:
        logger.debug(f"Metadata library error: {e}")
    return meta