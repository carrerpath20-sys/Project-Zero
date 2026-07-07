#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mapper Agent — Phase 0: WAF / Firewall / Cloudflare Detection.
"""
import logging
import requests
from .base_agent import BaseAgent

logger = logging.getLogger("ZeroRecon")

class MapperAgent(BaseAgent):
    """WAF, Cloudflare, এবং অন্যান্য সুরক্ষা স্তর শনাক্ত করে"""
    
    def __init__(self):
        super().__init__("MapperAgent")
    
    def run(self, target: str, context: dict = None) -> dict:
        self._log_start()
        result = {
            "target": target,
            "waf_detected": False,
            "cloudflare_detected": False,
            "security_headers": {},
            "status": "complete",
            "errors": []
        }
        
        try:
            # HTTP রিকোয়েস্ট (HTTPS)
            resp = requests.get(f"https://{target}", timeout=10, allow_redirects=True, verify=False)
            headers = resp.headers
            result["security_headers"] = dict(headers)
            
            # Cloudflare চেক
            if "cf-ray" in headers:
                result["cloudflare_detected"] = True
                logger.info(f"☁️ Cloudflare detected on {target}")
            
            # WAF চেক (সাধারণ ইন্ডিকেটর)
            waf_indicators = ["cloudflare", "akamai", "aws waf", "sucuri", "incapsula", "mod_security"]
            server_header = headers.get("server", "").lower()
            if any(ind in server_header for ind in waf_indicators):
                result["waf_detected"] = True
                logger.info(f"🛡️ WAF detected: {server_header}")
            
            # সহজ স্ট্যাটাস কোড
            result["status_code"] = resp.status_code
            
        except requests.exceptions.SSLError:
            # HTTP-তে ফ্যালব্যাক
            try:
                resp = requests.get(f"http://{target}", timeout=10, allow_redirects=True)
                result["security_headers"] = dict(resp.headers)
                result["note"] = "Used HTTP (SSL error)"
            except Exception as e:
                result["errors"].append(str(e))
        except Exception as e:
            result["errors"].append(str(e))
            self._log_error(str(e))
        
        self._log_complete(result)
        return result