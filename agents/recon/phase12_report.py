#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 PHASE 12 — REPORT GENERATION (Level 5 — God-Tier)
- Aggregates all phases + Evo engines (MCTS, Debate, Symbolic, DNA, Profiler)
- Generates JSON, Markdown, and HTML reports
- HTML is a professional dark-theme dashboard with stats, tables, and alerts
- Includes risk score, critical assets, and actionable recommendations
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry: compiles all results and generates reports.
    """
    logger.info(f"📝 Phase 12 (Level 5) started for: {target}")

    prev_results = context.get("previous_results", {})
    mcts_path = context.get("mcts_path", {})
    debate_rules = context.get("debate_rules", {})
    router = context.get("router")

    # =====================================================================
    # ১. ডাটা অ্যাগ্রিগেশন (সব ফেজ + ইভো)
    # =====================================================================
    aggregated = _aggregate_data(prev_results)

    # ইভো ডাটা
    evo_meta = {
        "mcts": {
            "selected_path": mcts_path.get("selected"),
            "confidence": mcts_path.get("confidence"),
            "utility": mcts_path.get("utility")
        },
        "debate": {
            "verdict": debate_rules.get("verdict"),
            "flaws": debate_rules.get("flaws", [])[:3]
        },
        "dna": {
            "total_vectors": _get_dna_stats()
        }
    }

    # =====================================================================
    # ২. রিস্ক স্কোর (ফাইনাল)
    # =====================================================================
    risk_score = _calculate_risk_score(aggregated)

    # =====================================================================
    # ৩. রেকমেন্ডেশন
    # =====================================================================
    recommendations = _generate_recommendations(aggregated, risk_score)

    # =====================================================================
    # ৪. AI এক্সিকিউটিভ সামারি (যদি রাউটার থাকে)
    # =====================================================================
    ai_summary = None
    if router:
        try:
            prompt = f"""
            Target: {target}
            Subdomains: {len(aggregated.get('subdomains', []))}
            Live hosts: {len(aggregated.get('ips', []))}
            Takeover candidates: {len(aggregated.get('takeover_candidates', []))}
            CORS issues: {len(aggregated.get('cors_misconfigs', []))}
            Open ports: {len(aggregated.get('open_ports', []))}
            Risk score: {risk_score}/100
            MCTS path: {mcts_path.get('selected')}
            Debate verdict: {debate_rules.get('verdict')}

            Provide a 200-word executive summary for a security team.
            """
            ai_resp = router.route("executive_summary_final", prompt)
            if ai_resp:
                ai_summary = ai_resp
        except:
            pass

    # =====================================================================
    # ৫. রিপোর্ট ডাটা তৈরি
    # =====================================================================
    report_data = {
        "meta": {
            "target": target,
            "scan_date": datetime.now().isoformat(),
            "framework": "Zero Recon v2.0",
            "version": "Level 5 (Evo-Delta)"
        },
        "summary": {
            "total_subdomains": len(aggregated.get("subdomains", [])),
            "total_ips": len(aggregated.get("ips", [])),
            "total_takeover": len(aggregated.get("takeover_candidates", [])),
            "total_cors": len(aggregated.get("cors_misconfigs", [])),
            "total_open_ports": len(aggregated.get("open_ports", [])),
            "risk_score": risk_score,
            "critical_assets": len(aggregated.get("critical_assets", []))
        },
        "findings": {
            "subdomains": aggregated.get("subdomains", [])[:50],
            "live_hosts": aggregated.get("ips", [])[:20],
            "takeover_candidates": aggregated.get("takeover_candidates", [])[:10],
            "cors_misconfigs": aggregated.get("cors_misconfigs", [])[:5],
            "open_ports": aggregated.get("open_ports", [])[:10],
            "endpoints": aggregated.get("endpoints", [])[:20],
            "secrets": aggregated.get("secrets", [])[:5]
        },
        "evo": evo_meta,
        "ai_executive_summary": ai_summary,
        "recommendations": recommendations
    }

    # =====================================================================
    # ৬. রিপোর্ট ফাইল লেখা
    # =====================================================================
    output_dir = Path("outputs/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"report_{target}_{timestamp}"

    # JSON
    json_path = output_dir / f"{base_filename}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, default=str)
    logger.info(f"✅ JSON report: {json_path}")

    # Markdown
    md_path = output_dir / f"{base_filename}.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(_generate_markdown(report_data))
    logger.info(f"✅ Markdown report: {md_path}")

    # HTML
    html_path = output_dir / f"{base_filename}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(_generate_html(report_data))
    logger.info(f"✅ HTML report: {html_path}")

    return {
        "target": target,
        "report_files": [str(json_path), str(md_path), str(html_path)],
        "summary": report_data["summary"],
        "status": "complete"
    }


# ============================================================
#  হেল্পার ফাংশন (অ্যাগ্রিগেশন + রিপোর্ট জেনারেশন)
# ============================================================

def _aggregate_data(prev_results: Dict) -> Dict:
    """সব ফেজ থেকে ডাটা একত্রিত করে"""
    aggregated = {
        "subdomains": set(),
        "ips": set(),
        "takeover_candidates": [],
        "cors_misconfigs": [],
        "open_ports": [],
        "endpoints": [],
        "secrets": [],
        "critical_assets": []
    }

    # ফেজ ১: সাবডোমেইন
    p1 = prev_results.get("phase_1", {})
    aggregated["subdomains"].update(p1.get("subdomains", []))
    aggregated["subdomains"].update(p1.get("live_subdomains", []))

    # ফেজ ২: আইপি
    p2 = prev_results.get("phase_2", {})
    if p2.get("target_ip"):
        aggregated["ips"].add(p2["target_ip"])
    aggregated["ips"].update(p2.get("origin_ips", []))

    # ফেজ ৪: এন্ডপয়েন্ট
    p4 = prev_results.get("phase_4", {})
    aggregated["endpoints"].extend(p4.get("endpoints_found", []))
    aggregated["secrets"].extend(p4.get("secrets_found", []))

    # ফেজ ১০: ভলনারেবিলিটি
    p10 = prev_results.get("phase_10", {})
    aggregated["takeover_candidates"] = p10.get("takeover_candidates", [])
    aggregated["cors_misconfigs"] = p10.get("cors_misconfigs", [])
    aggregated["open_ports"] = p10.get("open_ports", [])
    risk_score = p10.get("risk_score", 0)
    if risk_score > 70:
        aggregated["critical_assets"] = p10.get("takeover_candidates", [])[:3]

    # ফেজ ৬ & ৮: পারমিউটেশন
    p6 = prev_results.get("phase_6", {})
    aggregated["subdomains"].update(p6.get("permutations", []))

    # ফেজ ৯: ওএসআইএনটি
    p9 = prev_results.get("phase_9", {})
    aggregated["ips"].update(p9.get("ips", []))

    # ডুপ্লিকেট বাদ
    aggregated["subdomains"] = list(aggregated["subdomains"])[:500]
    aggregated["ips"] = list(aggregated["ips"])[:100]

    return aggregated

def _calculate_risk_score(aggregated: Dict) -> int:
    """ফাইনাল রিস্ক স্কোর"""
    score = 0
    if len(aggregated.get("takeover_candidates", [])) > 0:
        score += min(40, len(aggregated["takeover_candidates"]) * 10)
    if len(aggregated.get("cors_misconfigs", [])) > 0:
        score += min(20, len(aggregated["cors_misconfigs"]) * 5)
    if len(aggregated.get("open_ports", [])) > 0:
        high_risk = sum(1 for p in aggregated["open_ports"] if p.get("port") in [22, 3389, 3306, 6379])
        score += min(30, high_risk * 10)
    if len(aggregated.get("subdomains", [])) > 100:
        score += 10
    return min(100, score)

def _generate_recommendations(aggregated: Dict, risk_score: int) -> List[str]:
    """অ্যাকশনেবল রেকমেন্ডেশন"""
    recs = []
    if aggregated.get("takeover_candidates"):
        recs.append("🔴 PRIORITY: Verify and claim takeover candidates immediately.")
    if aggregated.get("cors_misconfigs"):
        recs.append("🟠 HIGH: Fix CORS misconfigurations to prevent data exfiltration.")
    if any(p.get("port") in [22, 3389, 3306] for p in aggregated.get("open_ports", [])):
        recs.append("🔴 CRITICAL: Secure exposed SSH/RDP/MySQL services.")
    if risk_score > 70:
        recs.append("🔴 IMMEDIATE: The target is at high risk. Conduct manual penetration testing.")
    else:
        recs.append("🟢 LOW: No critical issues found. Continue monitoring.")
    return recs

def _get_dna_stats() -> int:
    """ডিএনএ ভেক্টর সংখ্যা (যদি পাওয়া যায়)"""
    try:
        from evo.dna import DNA
        dna = DNA()
        stats = dna.get_stats()
        return stats.get("total_patterns", 0)
    except:
        return 0

def _generate_markdown(data: Dict) -> str:
    """মার্কডাউন রিপোর্ট"""
    md = f"""# 🔍 Zero Recon Report: {data['meta']['target']}

**Scan Date:** {data['meta']['scan_date']}  
**Framework:** {data['meta']['framework']}  
**Risk Score:** {data['summary']['risk_score']}/100

## 📊 Summary
- Subdomains: {data['summary']['total_subdomains']}
- Live IPs: {data['summary']['total_ips']}
- Takeover Candidates: {data['summary']['total_takeover']}
- CORS Issues: {data['summary']['total_cors']}
- Open Ports: {data['summary']['total_open_ports']}

## 🧠 AI Executive Summary
{data.get('ai_executive_summary', 'No AI summary available.')}

## 🔥 Critical Findings
### Subdomain Takeover
"""
    for tc in data['findings'].get('takeover_candidates', [])[:5]:
        md += f"- `{tc.get('subdomain')}` → {tc.get('service')} (Confidence: {tc.get('confidence')})\n"

    md += "\n### Open Ports (High-Risk)\n"
    for p in data['findings'].get('open_ports', [])[:5]:
        md += f"- {p.get('target')}: {[x['port'] for x in p.get('open_ports', [])]}\n"

    md += "\n## 🛠️ Recommendations\n"
    for rec in data.get('recommendations', []):
        md += f"- {rec}\n"

    md += "\n---\n*Generated by Zero Recon Framework v2.0 (Level 5)*"
    return md

def _generate_html(data: Dict) -> str:
    """এইচটিএমএল রিপোর্ট (প্রফেশনাল ড্যাশবোর্ড)"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zero Recon Report: {data['meta']['target']}</title>
<style>
body {{ background: #0a0a0a; color: #c9d1d9; font-family: 'Segoe UI', monospace; padding: 30px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ color: #58a6ff; border-bottom: 2px solid #58a6ff; }}
.stats {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 20px; margin: 20px 0; }}
.stat-box {{ background: #1a1a1a; padding: 15px; border-radius: 8px; border-left: 4px solid #58a6ff; }}
.stat-box .num {{ font-size: 28px; font-weight: bold; color: #f0f6fc; }}
.stat-box .label {{ color: #8b949e; font-size: 14px; }}
.risk {{ background: { '#f85149' if data['summary']['risk_score'] > 70 else '#d29922' if data['summary']['risk_score'] > 40 else '#238636' }; padding: 10px 20px; border-radius: 8px; display: inline-block; }}
.findings {{ background: #1a1a1a; padding: 20px; border-radius: 8px; margin: 15px 0; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #30363d; }}
th {{ color: #58a6ff; }}
.critical {{ color: #f85149; }}
.high {{ color: #d29922; }}
</style>
</head>
<body>
<div class="container">
<h1>🔍 Zero Recon Report</h1>
<p><strong>Target:</strong> {data['meta']['target']}</p>
<p><strong>Date:</strong> {data['meta']['scan_date']}</p>
<div class="stats">
<div class="stat-box"><div class="num">{data['summary']['total_subdomains']}</div><div class="label">Subdomains</div></div>
<div class="stat-box"><div class="num">{data['summary']['total_ips']}</div><div class="label">Live IPs</div></div>
<div class="stat-box"><div class="num">{data['summary']['total_takeover']}</div><div class="label">Takeover</div></div>
<div class="stat-box"><div class="num">{data['summary']['risk_score']}/100</div><div class="label">Risk Score</div></div>
</div>
<div class="risk">Risk Score: {data['summary']['risk_score']}/100</div>
<h2>🧠 AI Executive Summary</h2>
<div class="findings">{data.get('ai_executive_summary', 'No AI summary available.')}</div>
<h2>🔥 Critical Findings</h2>
<div class="findings">
<table>
<tr><th>Type</th><th>Details</th><th>Risk</th></tr>
"""
    for tc in data['findings'].get('takeover_candidates', [])[:5]:
        html += f"<tr><td>Takeover</td><td>{tc.get('subdomain')} → {tc.get('service')}</td><td class='critical'>Critical</td></tr>"
    for cors in data['findings'].get('cors_misconfigs', [])[:3]:
        html += f"<tr><td>CORS</td><td>{cors.get('host')} ({cors.get('headers')})</td><td class='high'>High</td></tr>"
    html += """</table></div>
<h2>🛠️ Recommendations</h2><ul>"""
    for rec in data.get('recommendations', []):
        html += f"<li>{rec}</li>"
    html += "</ul><hr><p><em>Generated by Zero Recon Framework v2.0 (Level 5)</em></p></div></body></html>"
