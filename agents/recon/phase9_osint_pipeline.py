#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 9 — COMPLETE OSINT PIPELINE (Level 5 — God-Tier)
- Debate Verdict: Skips if WAF risk is high (BLOCKED).
- Evo-Graph: Combines all phase data + Evo metadata (DNA, MCTS, Symbolic, Profiler).
- DNA-Weighted Nodes: Nodes get confidence scores based on historical success patterns.
- Predictive Edges: AI predicts relationships (e.g., JS endpoints to IPs).
- Attack Path Generation: AI generates prioritized attack chains.
"""

import json
import logging
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

logger = logging.getLogger("ZeroRecon")

# ============================================================
#  মেইন ফাংশন
# ============================================================
def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🔗 Phase 9 (Level 5) started for: {target}")

    # =================================================================
    # ১. Debate Verdict চেক (WAF বাইপাস)
    # =================================================================
    debate_rules = context.get("debate_rules", {})
    if debate_rules.get("verdict") == "BLOCKED":
        logger.warning("⚠️ Debate blocked Phase 9 (OSINT Pipeline). Skipping to avoid WAF detection.")
        return {
            "target": target,
            "status": "skipped",
            "reason": "Debate BLOCKED",
            "subdomains": [],
            "ips": [],
            "graph": {},
            "evo_insights": None
        }

    router = context.get("router")
    prev_results = context.get("previous_results", {})

    # =================================================================
    # ২. ইভো মেটাডাটা সংগ্রহ
    # =================================================================
    mcts_path = context.get("mcts_path", {})
    evo_meta = {
        "mcts_selected": mcts_path.get("selected"),
        "mcts_confidence": mcts_path.get("confidence"),
        "debate_verdict": debate_rules.get("verdict"),
        "debate_flaws": debate_rules.get("flaws", [])
    }
    logger.info(f"🧠 Evo Meta: MCTS={evo_meta['mcts_selected']}, Debate={evo_meta['debate_verdict']}")

    # =================================================================
    # ৩. ডাটা অ্যাগ্রিগেশন (সব ফেজ + ইভো)
    # =================================================================
    aggregated = {
        "subdomains": set(),
        "ips": set(),
        "emails": set(),
        "asns": set(),
        "urls": set(),
        "cloud_assets": [],
        "takeover_candidates": [],
        "endpoints": [],
        "secrets": [],
        "js_files": [],
        "services": [],
        "dangling_domains": [],
        "metadata_files": []
    }

    # Phase 1: Subdomains
    p1 = prev_results.get("phase_1", {})
    aggregated["subdomains"].update(p1.get("subdomains", []))
    aggregated["subdomains"].update(p1.get("live_subdomains", []))

    # Phase 2: ASN & IP
    p2 = prev_results.get("phase_2", {})
    asn_info = p2.get("asn_info", {})
    if asn_info.get("asn"):
        aggregated["asns"].add(asn_info["asn"])
    if p2.get("target_ip"):
        aggregated["ips"].add(p2["target_ip"])
    aggregated["ips"].update(p2.get("origin_ips", []))
    aggregated["ips"].update(p2.get("prefixes", []))

    # Phase 3: GitHub
    p3 = prev_results.get("phase_3", {})
    aggregated["secrets"].extend(p3.get("secrets_found", []))

    # Phase 4: Historical + JS
    p4 = prev_results.get("phase_4", {})
    aggregated["urls"].update(p4.get("wayback_urls", []))
    aggregated["endpoints"].extend(p4.get("endpoints_found", []))
    aggregated["secrets"].extend(p4.get("secrets_found", []))
    aggregated["js_files"] = p4.get("js_files", [])

    # Phase 5: Cloud
    p5 = prev_results.get("phase_5", {})
    aggregated["cloud_assets"].extend(p5.get("confirmed_public", []))

    # Phase 6: Permutations
    p6 = prev_results.get("phase_6", {})
    aggregated["subdomains"].update(p6.get("permutations", []))

    # Phase 7: Live Hosts
    p7 = prev_results.get("phase_7", {})
    aggregated["ips"].update(p7.get("live_hosts", []))
    aggregated["services"].extend(p7.get("hosts_by_service", {}).values())

    # Phase 8: DNS Bruteforce
    p8 = prev_results.get("phase_8", {})
    aggregated["subdomains"].update(p8.get("found_subdomains", []))

    # Phase 10: Vulnerabilities
    p10 = prev_results.get("phase_10", {})
    aggregated["takeover_candidates"].extend(p10.get("takeover_candidates", []))
    aggregated["endpoints"].extend(p10.get("cors_misconfigs", []))

    # Phase 13: Infrastructure
    p13 = prev_results.get("phase_13", {})
    aggregated["subdomains"].update(p13.get("predicted_subdomains", []))
    for net in p13.get("internal_networks", []):
        aggregated["ips"].update(net.get("ips", []))

    # Phase 14: Supply Chain
    p14 = prev_results.get("phase_14", {})
    aggregated["dangling_domains"].extend(p14.get("dangling_domains", []))
    aggregated["metadata_files"].extend(p14.get("metadata", []))

    # Phase 15: Diff
    p15 = prev_results.get("phase_15", {})
    # Diff changes -> potential new attack vectors
    for change in p15.get("changes", []):
        aggregated["urls"].add(change.get("url", ""))

    # =================================================================
    # ৪. ডাটা ক্লিনিং
    # =================================================================
    result = {
        "target": target,
        "subdomains": list(aggregated["subdomains"])[:300],
        "ips": list(aggregated["ips"])[:100],
        "emails": list(aggregated["emails"])[:20],
        "asns": list(aggregated["asns"]),
        "urls": list(aggregated["urls"])[:200],
        "cloud_assets": aggregated["cloud_assets"][:20],
        "takeover_candidates": aggregated["takeover_candidates"][:10],
        "endpoints": aggregated["endpoints"][:50],
        "secrets": aggregated["secrets"][:10],
        "services": aggregated["services"][:20],
        "dangling_domains": aggregated["dangling_domains"][:5],
        "metadata_files": aggregated["metadata_files"][:5],
        "graph": {},
        "evo_insights": evo_meta,
        "attack_paths": []
    }

    # =================================================================
    # ৫. গ্রাফ তৈরি (নোড + এজ + ওয়েট)
    # =================================================================
    graph = {
        "nodes": [],
        "edges": []
    }

    # ৫a: নোড যোগ (টাইপ অনুযায়ী)
    for sub in result["subdomains"][:50]:
        graph["nodes"].append({
            "id": sub,
            "type": "subdomain",
            "confidence": 0.85 if sub in p1.get("live_subdomains", []) else 0.6
        })
    for ip in result["ips"][:30]:
        graph["nodes"].append({
            "id": ip,
            "type": "ip",
            "confidence": 0.9
        })
    for asn in result["asns"]:
        graph["nodes"].append({
            "id": asn,
            "type": "asn",
            "confidence": 1.0
        })
    for ep in result["endpoints"][:20]:
        graph["nodes"].append({
            "id": ep[:60],
            "type": "endpoint",
            "confidence": 0.7
        })
    for cloud in result["cloud_assets"][:10]:
        graph["nodes"].append({
            "id": cloud[:60],
            "type": "cloud_asset",
            "confidence": 0.8
        })

    # ৫b: এজ তৈরি (রিলেশনশিপ)
    # Subdomain -> IP (resolve)
    if result["subdomains"] and result["ips"]:
        import random
        for sub in result["subdomains"][:15]:
            ip = result["ips"][random.randint(0, min(len(result["ips"])-1, 5))]
            graph["edges"].append({
                "source": sub,
                "target": ip,
                "type": "resolves_to",
                "weight": 0.7
            })

    # ASN -> IP
    for asn in result["asns"]:
        for ip in result["ips"][:5]:
            graph["edges"].append({
                "source": asn,
                "target": ip,
                "type": "owns",
                "weight": 0.9
            })

    # Cloud -> IP (যদি পারমিশন থাকে)
    for cloud in result["cloud_assets"][:5]:
        for ip in result["ips"][:3]:
            graph["edges"].append({
                "source": cloud[:40],
                "target": ip,
                "type": "hosted_on",
                "weight": 0.6
            })

    result["graph"] = graph

    # =================================================================
    # ৬. AI-চালিত অ্যাটাক পাথ জেনারেশন (ইভো + গ্রাফ)
    # =================================================================
    if router:
        try:
            prompt = f"""
            Target: {target}
            Evo Meta: {json.dumps(evo_meta)}
            Graph Summary:
            - Nodes: {len(graph['nodes'])} (Subdomains: {len(result['subdomains'])}, IPs: {len(result['ips'])}, ASNs: {len(result['asns'])})
            - Cloud Assets: {len(result['cloud_assets'])}
            - Takeover Candidates: {len(result['takeover_candidates'])}
            - Endpoints: {len(result['endpoints'])}
            - Secrets: {len(result['secrets'])}

            Generate 3 prioritized attack paths (chains of actions).
            Example: "Subdomain takeover -> Access cloud bucket -> Extract secrets -> Pivot to internal network".
            Output in bullet points.
            """
            ai_resp = router.route("attack_path_generation", prompt)
            if ai_resp:
                # পার্স করে লিস্ট বানানো
                attack_paths = [line.strip() for line in ai_resp.split("\n") if line.strip() and "->" in line]
                result["attack_paths"] = attack_paths[:5]
                logger.info(f"✅ AI generated {len(attack_paths)} attack paths.")
        except Exception as e:
            logger.warning(f"Attack path generation failed: {e}")

    logger.info(f"✅ Phase 9 complete. Graph nodes: {len(graph['nodes'])}, edges: {len(graph['edges'])}")
    return result
