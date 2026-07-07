#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNS Resolver — Windows Native (dnspython + socket fallback)
- Primary: dnspython (fast, reliable)
- Fallback: socket.gethostbyname_ex (threaded)
- Wildcard DNS detection (filter out fake results)
"""
import socket
import logging
import concurrent.futures
from typing import List, Set, Optional, Union

logger = logging.getLogger("ZeroRecon")

# গ্লোবাল উইল্ডকার্ড ডিটেক্টর
_wildcard_cache = {}

def resolve_dns(domain: str, record_type: str = "A") -> Optional[List[str]]:
    """
    DNS রেজলভ করে (dnspython দিয়ে)।
    রেকর্ড টাইপ: A, CNAME, TXT, MX, NS
    """
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5
        
        try:
            answers = resolver.resolve(domain, record_type)
            results = []
            for rdata in answers:
                if record_type == "A":
                    results.append(rdata.address)
                elif record_type == "CNAME":
                    results.append(str(rdata.target).rstrip('.'))
                else:
                    results.append(str(rdata))
            return results
        except dns.resolver.NXDOMAIN:
            return None
        except dns.resolver.Timeout:
            logger.debug(f"DNS timeout for {domain}")
            return None
        except Exception as e:
            logger.debug(f"DNS error: {e}")
            return None
    except ImportError:
        # dnspython না থাকলে socket ফ্যালব্যাক
        logger.debug("dnspython not found, using socket fallback")
        return _resolve_socket_fallback(domain)


def _resolve_socket_fallback(domain: str) -> Optional[List[str]]:
    """socket.gethostbyname_ex দিয়ে ফ্যালব্যাক (Windows-native)"""
    try:
        # gethostbyname_ex রিটার্ন করে (hostname, aliaslist, ipaddrlist)
        hostname, aliases, ip_list = socket.gethostbyname_ex(domain)
        return ip_list
    except socket.gaierror:
        return None
    except Exception as e:
        logger.debug(f"Socket resolution error: {e}")
        return None


def resolve_bulk(domains: List[str], max_workers: int = 10) -> Dict[str, Optional[List[str]]]:
    """
    একাধিক ডোমেইন সমান্তরালে রেজলভ করে (থ্রেডেড)
    """
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_domain = {executor.submit(resolve_dns, d): d for d in domains}
        for future in concurrent.futures.as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                results[domain] = future.result()
            except Exception as e:
                logger.debug(f"Bulk resolve error for {domain}: {e}")
                results[domain] = None
    return results


def check_wildcard(domain: str) -> bool:
    """
    Wildcard DNS ডিটেক্ট করে।
    এলোমেলো সাবডোমেইন রেজলভ করে দেখে — IP ফিরলে Wildcard।
    """
    import random
    import string
    
    if domain in _wildcard_cache:
        return _wildcard_cache[domain]
    
    # এলোমেলো ১০টি অক্ষরের সাবডোমেইন
    random_sub = ''.join(random.choices(string.ascii_lowercase, k=10))
    test_domain = f"{random_sub}.{domain}"
    
    try:
        ips = resolve_dns(test_domain)
        is_wildcard = ips is not None and len(ips) > 0
    except:
        is_wildcard = False
    
    _wildcard_cache[domain] = is_wildcard
    if is_wildcard:
        logger.info(f"🌐 Wildcard DNS detected for: {domain}")
    return is_wildcard


def filter_wildcard(domains: List[str], base_domain: str) -> List[str]:
    """
    Wildcard ডিটেক্ট করে, সেই প্যাটার্নের সাথে মিলে যায় এমন ডোমেইন ফিল্টার করে বাদ দেয়।
    """
    if not check_wildcard(base_domain):
        return domains  # Wildcard নেই, সব ঠিক
    
    # এলোমেলো সাবডোমেইনের IP বের করি
    import random, string
    random_sub = ''.join(random.choices(string.ascii_lowercase, k=10))
    test_domain = f"{random_sub}.{base_domain}"
    wildcard_ips = resolve_dns(test_domain)
    
    if not wildcard_ips:
        return domains
    
    wildcard_set = set(wildcard_ips)
    filtered = []
    for d in domains:
        ips = resolve_dns(d)
        if ips:
            # যদি এই ডোমেইনের IP Wildcard IP-গুলোর সাথে মেলে, বাদ দাও
            if not set(ips).issubset(wildcard_set):
                filtered.append(d)
        else:
            filtered.append(d)
    
    logger.info(f"🧹 Filtered {len(domains) - len(filtered)} wildcard domains")
    return filtered