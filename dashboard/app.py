#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 DASHBOARD APP (Level 5 — God-Tier Live Recon Interface)
- Flask + SocketIO server (port 5000 by default).
- Live logs, phase status, system metrics (CPU/Memory), and Evo metadata.
- Auto-detects project root, reads state/session.json and outputs/logs/.
- Self-contained: serves an embedded dark-theme HTML dashboard.
- Threaded monitor pushes updates to connected clients every 2 seconds.
"""

import os
import sys
import json
import time
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

import psutil
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit

logger = logging.getLogger("ZeroRecon")

# ------------------------------------------------------------
#  কনফিগ
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
STATE_DIR = PROJECT_ROOT / "state"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
LOGS_DIR = OUTPUT_DIR / "logs"
REPORTS_DIR = OUTPUT_DIR / "reports"

# Flask অ্যাপ
app = Flask(__name__)
app.config['SECRET_KEY'] = 'zero-recon-dashboard-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ------------------------------------------------------------
#  ডাটা ফেচার ফাংশন
# ------------------------------------------------------------
def get_session_data() -> Dict:
    """Read current session data from state/session.json."""
    session_file = STATE_DIR / "session.json"
    if not session_file.exists():
        return {"status": "No active session", "target": "N/A"}
    try:
        with open(session_file, 'r') as f:
            data = json.load(f)
        # Latest session
        sessions = data.get("sessions", [])
        if not sessions:
            return {"status": "No sessions", "target": "N/A"}
        latest = sessions[-1]
        return {
            "status": latest.get("status", "unknown"),
            "target": latest.get("target", "N/A"),
            "session_id": latest.get("session_id", "N/A"),
            "current_phase": latest.get("current_phase", 0),
            "completed_phases": latest.get("completed_phases", []),
            "phases": latest.get("phases", []),
            "start_time": latest.get("start_time", "N/A"),
            "evo_meta": latest.get("evo_meta", {})
        }
    except:
        return {"status": "Error reading session", "target": "N/A"}

def get_latest_logs(lines: int = 50) -> List[str]:
    """Tail the latest log file."""
    if not LOGS_DIR.exists():
        return ["No logs found."]
    log_files = sorted(LOGS_DIR.glob("zero_recon_*.log"), key=os.path.getmtime, reverse=True)
    if not log_files:
        return ["No log files found."]
    latest_log = log_files[0]
    try:
        with open(latest_log, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except:
        return ["Error reading log file."]

def get_system_stats() -> Dict:
    """Get CPU, Memory, Disk stats."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "cpu": cpu,
            "memory_percent": mem.percent,
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        }
    except:
        return {"cpu": 0, "memory_percent": 0, "disk_percent": 0}

def get_recent_reports() -> List[Dict]:
    """List latest reports."""
    if not REPORTS_DIR.exists():
        return []
    reports = []
    for f in sorted(REPORTS_DIR.glob("report_*.json"), key=os.path.getmtime, reverse=True)[:5]:
        reports.append({
            "name": f.name,
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    return reports

# ------------------------------------------------------------
#  ব্যাকগ্রাউন্ড মনিটর থ্রেড (SocketIO Push)
# ------------------------------------------------------------
monitor_thread = None
stop_monitor = False

def background_monitor():
    """Continuously push updates to connected clients."""
    global stop_monitor
    while not stop_monitor:
        try:
            session = get_session_data()
            logs = get_latest_logs(30)
            stats = get_system_stats()
            reports = get_recent_reports()
            
            socketio.emit('status_update', {
                'session': session,
                'logs': logs,
                'stats': stats,
                'reports': reports,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            socketio.emit('error', {'msg': f"Monitor error: {str(e)}"})
        time.sleep(2)  # 2-second interval

# ------------------------------------------------------------
#  সকেট ইভেন্ট হ্যান্ডলার
# ------------------------------------------------------------
@socketio.on('connect')
def handle_connect():
    """Client connected — start monitor if not already running."""
    global monitor_thread, stop_monitor
    print(f"🔌 Client connected: {request.sid}")
    if monitor_thread is None or not monitor_thread.is_alive():
        stop_monitor = False
        monitor_thread = threading.Thread(target=background_monitor, daemon=True)
        monitor_thread.start()
        print("🔄 Monitor thread started.")
    emit('connected', {'msg': 'Connected to Zero Recon Dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"🔌 Client disconnected: {request.sid}")

# ------------------------------------------------------------
#  ফ্লাস্ক রুট (REST API + HTML)
# ------------------------------------------------------------
@app.route('/')
def index():
    """Serve the embedded HTML dashboard."""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zero Recon Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', monospace; background: #0a0a0a; color: #c9d1d9; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #58a6ff; border-bottom: 2px solid #58a6ff; padding-bottom: 10px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card { background: #161b22; padding: 15px; border-radius: 8px; border-left: 4px solid #58a6ff; }
        .card .num { font-size: 24px; font-weight: bold; color: #f0f6fc; }
        .card .label { color: #8b949e; font-size: 12px; text-transform: uppercase; }
        .flex { display: flex; gap: 20px; flex-wrap: wrap; }
        .flex > div { flex: 1; min-width: 300px; }
        .log-box { background: #0d1117; padding: 15px; border-radius: 8px; max-height: 400px; overflow-y: auto; font-size: 12px; border: 1px solid #30363d; white-space: pre-wrap; word-break: break-all; }
        .log-box::-webkit-scrollbar { width: 6px; }
        .log-box::-webkit-scrollbar-track { background: #161b22; }
        .log-box::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
        .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; background: #238636; color: #fff; margin-left: 5px; }
        .badge.warn { background: #d29922; }
        .badge.danger { background: #f85149; }
        .badge.info { background: #58a6ff; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #30363d; }
        th { color: #58a6ff; }
        .footer { margin-top: 30px; color: #8b949e; font-size: 12px; text-align: center; border-top: 1px solid #30363d; padding-top: 15px; }
        .status-running { color: #58a6ff; }
        .status-completed { color: #238636; }
        .status-failed { color: #f85149; }
    </style>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
</head>
<body>
<div class="container">
    <h1>🔍 Zero Recon — Live Dashboard <span style="font-size:14px; color:#8b949e;">(Level 5)</span></h1>
    
    <div class="grid" id="stats-grid">
        <div class="card"><div class="num" id="target">N/A</div><div class="label">Target</div></div>
        <div class="card"><div class="num" id="phase">0/15</div><div class="label">Phase</div></div>
        <div class="card"><div class="num" id="cpu">0%</div><div class="label">CPU Usage</div></div>
        <div class="card"><div class="num" id="memory">0%</div><div class="label">Memory</div></div>
    </div>
    
    <div class="flex">
        <div>
            <h3>📊 Status & Reports</h3>
            <div id="status-box" style="background:#161b22; padding:15px; border-radius:8px; min-height:100px; font-size:14px;">
                Waiting for data...
            </div>
            <div id="reports-box" style="margin-top:15px; background:#161b22; padding:15px; border-radius:8px;">
                <h4 style="color:#8b949e;">📁 Recent Reports</h4>
                <div id="report-list">No reports yet.</div>
            </div>
        </div>
        <div>
            <h3>📜 Live Logs</h3>
            <div class="log-box" id="log-box">Connecting to server...</div>
        </div>
    </div>
    <div class="footer">Zero Recon Framework v2.0 — Dashboard updates every 2 seconds</div>
</div>

<script>
    const socket = io();
    const logBox = document.getElementById('log-box');
    const targetEl = document.getElementById('target');
    const phaseEl = document.getElementById('phase');
    const cpuEl = document.getElementById('cpu');
    const memoryEl = document.getElementById('memory');
    const statusBox = document.getElementById('status-box');
    const reportList = document.getElementById('report-list');

    socket.on('connect', () => {
        logBox.innerHTML = '✅ Connected to server. Waiting for updates...';
    });

    socket.on('status_update', (data) => {
        // Stats
        const session = data.session || {};
        const stats = data.stats || {};
        targetEl.textContent = session.target || 'N/A';
        const current = session.current_phase || 0;
        const total = session.phases ? session.phases.length : 15;
        phaseEl.textContent = `${current}/${total}`;
        cpuEl.textContent = `${Math.round(stats.cpu || 0)}%`;
        memoryEl.textContent = `${Math.round(stats.memory_percent || 0)}%`;

        // Status Box
        let statusText = `<strong>Session:</strong> ${session.session_id || 'N/A'}<br>`;
        statusText += `<strong>Status:</strong> <span class="status-${session.status || 'running'}">${session.status || 'unknown'}</span><br>`;
        statusText += `<strong>Start:</strong> ${session.start_time || 'N/A'}<br>`;
        statusText += `<strong>Completed Phases:</strong> ${(session.completed_phases || []).join(', ') || 'None'}<br>`;
        if (session.evo_meta && Object.keys(session.evo_meta).length > 0) {
            statusText += `<strong>🧬 Evo:</strong> MCTS: ${session.evo_meta.mcts_selected || 'N/A'}, Debate: ${session.evo_meta.debate_verdict || 'N/A'}`;
        }
        statusBox.innerHTML = statusText;

        // Reports
        if (data.reports && data.reports.length > 0) {
            let html = '<table><tr><th>File</th><th>Size</th><th>Modified</th></tr>';
            data.reports.forEach(r => {
                html += `<tr><td>${r.name}</td><td>${(r.size/1024).toFixed(1)}KB</td><td>${r.modified}</td></tr>`;
            });
            html += '</table>';
            reportList.innerHTML = html;
        } else {
            reportList.innerHTML = 'No reports yet.';
        }

        // Logs
        if (data.logs && data.logs.length > 0) {
            // Use raw string to avoid escape sequence warnings
            logBox.innerHTML = data.logs.join('').replace(/\[[^\]]+\]/g, '');
            logBox.scrollTop = logBox.scrollHeight;
        }
    });

    socket.on('error', (data) => {
        logBox.innerHTML = `⚠️ ${data.msg}`;
    });

    socket.on('disconnect', () => {
        logBox.innerHTML = '❌ Disconnected from server. Reconnecting...';
    });
</script>
</body>
</html>
    """
    return render_template_string(html)

# ------------------------------------------------------------
#  এন্ট্রি পয়েন্ট
# ------------------------------------------------------------
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  🔥 Zero Recon Dashboard (Level 5)                   ║
    ║  URL: http://localhost:5000                          ║
    ║  Press Ctrl+C to stop.                              ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
