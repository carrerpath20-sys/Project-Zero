#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 12: Conclusion and Best Practices
- Generates final report in JSON, Markdown, and HTML
- Includes all findings from previous phases
- Executive summary and remediation recommendations
- Saves to outputs/reports/ directory
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("ZeroRecon")

def run(target: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for Phase 12.
    Compiles all previous results and generates beautiful reports.
    """
    logger.info(f"📝 Phase 12 started for: {target}")
    
    router = context.get("router")
    prev_results = context.get("previous_results", {})
    
    # =====================================================================
    # ১. ফাইনাল ডাটা স্ট্রাকচার তৈরি
    # =====================================================================
    report_data = {
        "meta": {
            "target": target,
            "scan_date": datetime.now().isoformat(),
            "tool": "Zero Recon Framework v1.0.0",
            "author": "Zero Labs"
        },
        "summary": {
            "total_phases_run": len(prev_results),
            "total_subdomains": 0,
            "total_ips": 0,
            "total_vulnerabilities": 0,
            "critical_assets": 0
        },
        "findings": {},
        "ai_executive_summary": None,
        "recommendations": []
    }
    
    # =====================================================================
    # ২. সব ফেজ থেকে ডাটা নেওয়া
    # =====================================================================
    # ফেজ ১: সাবডোমেইন
    phase1 = prev_results.get("phase_1", {})
    report_data["findings"]["subdomains"] = phase1.get("subdomains", [])
    report_data["summary"]["total_subdomains"] += len(phase1.get("subdomains", []))
    
    # ফেজ ২: ASN
    phase2 = prev_results.get("phase_2", {})
    report_data["findings"]["asn"] = phase2.get("asn_info", {})
    if phase2.get("origin_ips"):
        report_data["findings"]["origin_ips"] = phase2.get("origin_ips")
        report_data["summary"]["total_ips"] += len(phase2.get("origin_ips", []))
    
    # ফেজ ৩: GitHub
    phase3 = prev_results.get("phase_3", {})
    report_data["findings"]["github"] = {
        "repos": phase3.get("repositories", []),
        "secrets": phase3.get("secrets_found", [])
    }
    
    # ফেজ ৪: ঐতিহাসিক
    phase4 = prev_results.get("phase_4", {})
    report_data["findings"]["historical"] = {
        "wayback_urls": phase4.get("wayback_urls", [])[:10],
        "endpoints": phase4.get("endpoints_found", [])[:10]
    }
    
    # ফেজ ৫: ক্লাউড
    phase5 = prev_results.get("phase_5", {})
    report_data["findings"]["cloud"] = phase5.get("confirmed_public", [])
    report_data["summary"]["total_vulnerabilities"] += len(phase5.get("confirmed_public", []))
    
    # ফেজ ৬: পারমিউটেশন
    phase6 = prev_results.get("phase_6", {})
    report_data["findings"]["permutations"] = phase6.get("permutations", [])[:20]
    
    # ফেজ ৭: ASN ম্যাপ
    phase7 = prev_results.get("phase_7", {})
    report_data["findings"]["live_hosts"] = phase7.get("live_hosts", [])
    report_data["summary"]["total_ips"] += len(phase7.get("live_hosts", []))
    
    # ফেজ ৮: DNS ব্রুটফোর্স
    phase8 = prev_results.get("phase_8", {})
    report_data["findings"]["dns_found"] = phase8.get("found_subdomains", [])
    report_data["summary"]["total_subdomains"] += len(phase8.get("found_subdomains", []))
    
    # ফেজ ৯: OSINT পাইপলাইন
    phase9 = prev_results.get("phase_9", {})
    report_data["findings"]["osint_graph"] = phase9.get("graph", {})
    
    # ফেজ ১০: ভলনারেবিলিটি
    phase10 = prev_results.get("phase_10", {})
    report_data["findings"]["takeover_candidates"] = phase10.get("takeover_candidates", [])
    report_data["findings"]["cors_misconfigs"] = phase10.get("cors_misconfigs", [])
    report_data["summary"]["total_vulnerabilities"] += len(phase10.get("takeover_candidates", []))
    report_data["summary"]["total_vulnerabilities"] += len(phase10.get("cors_misconfigs", []))
    
    # ফেজ ১১: অ্যাটাক সারফেস
    phase11 = prev_results.get("phase_11", {})
    report_data["findings"]["critical_assets"] = phase11.get("assets_by_priority", {}).get("critical", [])
    report_data["summary"]["critical_assets"] = len(report_data["findings"]["critical_assets"])
    
    # AI সামারি
    if phase11.get("ai_executive_summary"):
        report_data["ai_executive_summary"] = phase11["ai_executive_summary"]
    
    # =====================================================================
    # ৩. রেকমেন্ডেশন তৈরি (AI/ফলাফলের ভিত্তিতে)
    # =====================================================================
    recommendations = []
    if report_data["findings"].get("takeover_candidates"):
        recommendations.append("🔴 Prioritize checking subdomain takeover candidates (found {len(...)}).")
    if report_data["findings"].get("cors_misconfigs"):
        recommendations.append("🔴 Fix CORS misconfigurations to prevent data leaks.")
    if report_data["findings"].get("cloud"):
        recommendations.append("🟡 Review public cloud storage permissions.")
    if not recommendations:
        recommendations.append("✅ No critical issues found. Conduct manual verification.")
    
    report_data["recommendations"] = recommendations
    
    # =====================================================================
    # ৪. রিপোর্ট সেভ করা
    # =====================================================================
    output_dir = Path("outputs/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"report_{target}_{timestamp}"
    
    # JSON
    json_path = output_dir / f"{base_filename}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, default=str)
    logger.info(f"✅ JSON report saved: {json_path}")
    
    # Markdown
    md_path = output_dir / f"{base_filename}.md"
    md_content = _generate_markdown(report_data, target)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    logger.info(f"✅ Markdown report saved: {md_path}")
    
    # HTML
    html_path = output_dir / f"{base_filename}.html"
    html_content = _generate_html(report_data, target)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"✅ HTML report saved: {html_path}")
    
    # =====================================================================
    # ৫. রিটার্ন
    # =====================================================================
    result = {
        "target": target,
        "report_files": {
            "json": str(json_path),
            "markdown": str(md_path),
            "html": str(html_path)
        },
        "summary": report_data["summary"],
        "status": "complete"
    }
    logger.info(f"✅ Phase 12 complete. Reports generated.")
    return result


def _generate_markdown(data: Dict, target: str) -> str:
    """মার্কডাউন রিপোর্ট জেনারেট করে"""
    md = f"""# 🔍 Zero Recon Report: {target}

**Scan Date:** {data['meta']['scan_date']}  
**Tool:** {data['meta']['tool']}

## 📊 Executive Summary
{data.get('ai_executive_summary', 'No AI summary available.')}

## 📈 Statistics
- **Total Subdomains:** {data['summary']['total_subdomains']}
- **Total IPs:** {data['summary']['total_ips']}
- **Total Vulnerabilities:** {data['summary']['total_vulnerabilities']}
- **Critical Assets:** {data['summary']['critical_assets']}

## 📌 Key Findings

### Subdomains (Sample)
{', '.join(data['findings'].get('subdomains', [])[:10]) if data['findings'].get('subdomains') else 'None found'}

### ASN Information
- **ASN:** {data['findings'].get('asn', {}).get('asn', 'N/A')}
- **Organization:** {data['findings'].get('asn', {}).get('org', 'N/A')}

### 🛡️ Vulnerabilities
- **Subdomain Takeover Candidates:** {len(data['findings'].get('takeover_candidates', []))}
- **CORS Misconfigurations:** {len(data['findings'].get('cors_misconfigs', []))}
- **Public Cloud Assets:** {len(data['findings'].get('cloud', []))}

### 📡 Live Hosts
{', '.join(data['findings'].get('live_hosts', [])[:5]) if data['findings'].get('live_hosts') else 'None found'}

## 🔧 Recommendations
"""
    for rec in data.get('recommendations', []):
        md += f"- {rec}\n"
    
    md += "\n---\n*Report generated by Zero Recon Framework v1.0.0*"
    return md


def _generate_html(data: Dict, target: str) -> str:
    """HTML রিপোর্ট জেনারেট করে (প্রফেশনাল স্টাইল)"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zero Recon Report: {target}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0d1117; color: #c9d1d9; padding: 30px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: #161b22; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
        h1, h2, h3 {{ color: #58a6ff; }}
        .stats {{ display: flex; gap: 20px; flex-wrap: wrap; margin: 20px 0; }}
        .stat-box {{ background: #0d1117; padding: 15px 25px; border-radius: 8px; border-left: 4px solid #58a6ff; flex: 1; }}
        .stat-box .number {{ font-size: 28px; font-weight: bold; color: #f0f6fc; }}
        .stat-box .label {{ color: #8b949e; }}
        .vuln-critical {{ color: #f85149; }}
        .vuln-high {{ color: #d29922; }}
        .vuln-medium {{ color: #e3b341; }}
        .vuln-low {{ color: #58a6ff; }}
        .findings-section {{ background: #0d1117; padding: 20px; border-radius: 8px; margin: 15px 0; }}
        pre {{ background: #0d1117; padding: 15px; border-radius: 6px; overflow-x: auto; border: 1px solid #30363d; }}
        .footer {{ margin-top: 30px; text-align: center; color: #8b949e; border-top: 1px solid #30363d; padding-top: 20px; }}
        .badge {{ display: inline-block; background: #238636; padding: 2px 10px; border-radius: 12px; font-size: 12px; color: #fff; margin-left: 5px; }}
    </style>
</head>
<body>
<div class="container">
    <h1>🔍 Zero Recon Report</h1>
    <p><strong>Target:</strong> {target} <span class="badge">Scan Complete</span></p>
    <p><strong>Date:</strong> {data['meta']['scan_date']}</p>
    
    <div class="stats">
        <div class="stat-box"><div class="number">{data['summary']['total_subdomains']}</div><div class="label">Total Subdomains</div></div>
        <div class="stat-box"><div class="number">{data['summary']['total_ips']}</div><div class="label">Total IPs</div></div>
        <div class="stat-box"><div class="number">{data['summary']['total_vulnerabilities']}</div><div class="label">Vulnerabilities</div></div>
        <div class="stat-box"><div class="number">{data['summary']['critical_assets']}</div><div class="label">Critical Assets</div></div>
    </div>
    
    <h2>📌 Executive Summary</h2>
    <div class="findings-section">
        <p>{data.get('ai_executive_summary', 'No AI summary available.')}</p>
    </div>
    
    <h2>🛡️ Key Findings</h2>
    <div class="findings-section">
        <h3>Subdomain Takeover</h3>
        <p>Candidates: {len(data['findings'].get('takeover_candidates', []))}</p>
        <ul>
        {''.join([f'<li><span class="vuln-critical">{item["subdomain"]}</span> - {item.get("details", {}).get("reason", "Potential")}</li>' for item in data['findings'].get('takeover_candidates', [])[:5]]) if data['findings'].get('takeover_candidates') else '<li>None found</li>'}
        </ul>
        
        <h3>CORS Misconfigurations</h3>
        <ul>
        {''.join([f'<li><span class="vuln-high">{item["host"]}</span> - ACAO: {item["acao"]}</li>' for item in data['findings'].get('cors_misconfigs', [])[:5]]) if data['findings'].get('cors_misconfigs') else '<li>None found</li>'}
        </ul>
        
        <h3>Public Cloud Assets</h3>
        <ul>
        {''.join([f'<li>{item}</li>' for item in data['findings'].get('cloud', [])[:5]]) if data['findings'].get('cloud') else '<li>None found</li>'}
        </ul>
    </div>
    
    <h2>🔧 Recommendations</h2>
    <div class="findings-section">
        <ul>
        {''.join([f'<li>{rec}</li>' for rec in data.get('recommendations', [])])}
        </ul>
    </div>
    
    <div class="footer">
        Generated by Zero Recon Framework v1.0.0 | Zero Labs
    </div>
</div>
</body>
</html>"""
    return html