#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 AGGRESSIVE INSTALLER (Level 5 — Windows Package Managers + GitHub Fallback)
- Checks if required tools (massdns, subfinder) are in PATH
- Tries winget → choco → scoop → GitHub download (as last resort)
- Never crashes the framework; always returns a fallback path or None
"""

import os
import sys
import shutil
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger("ZeroRecon")

# ============================================================
#  টুল ইনস্টল কমান্ড (Windows Package Managers)
# ============================================================
INSTALL_COMMANDS = {
    "massdns": {
        "winget": "winget install massdns",
        "choco": "choco install massdns",
        "scoop": "scoop install massdns",
        "github_repo": "blechschmidt/massdns",
        "binary": "massdns.exe",
        "fallback": "dnspython"
    },
    "subfinder": {
        "winget": "winget install subfinder",
        "choco": "choco install subfinder",
        "scoop": "scoop install subfinder",
        "github_repo": "projectdiscovery/subfinder",
        "binary": "subfinder.exe",
        "fallback": "crt_api"
    }
}

def ensure_tool(tool_name: str, auto_install: bool = True) -> Optional[str]:
    """
    টুল খোঁজে, না পেলে ইনস্টল/ফ্যালব্যাক করে।
    রিটার্ন: পাথ (স্ট্রিং) অথবা None (ফ্যালব্যাক ইঙ্গিত)
    """
    # ১. পাথে আছে?
    existing_path = shutil.which(tool_name)
    if existing_path:
        logger.info(f"✅ {tool_name} found at: {existing_path}")
        return existing_path

    logger.warning(f"⚠️ {tool_name} not found in PATH.")
    
    if not auto_install:
        logger.info(f"⏭️ Auto-install disabled. Using fallback for {tool_name}.")
        return None

    # ২. Windows Package Managers দিয়ে ইনস্টল (সরাসরি CMD কমান্ড)
    logger.info(f"📦 Attempting to install {tool_name} via package managers...")
    
    tool_info = INSTALL_COMMANDS.get(tool_name)
    if not tool_info:
        logger.warning(f"⚠️ No install info for {tool_name}")
        return None

    # প্যাকেজ ম্যানেজার অর্ডার: winget → choco → scoop
    managers = ["winget", "choco", "scoop"]
    for manager in managers:
        cmd = tool_info.get(manager)
        if cmd and shutil.which(manager):
            try:
                logger.info(f"🔧 Trying {manager} install: {cmd}")
                subprocess.run(cmd, shell=True, check=True, timeout=120, capture_output=True)
                # ইনস্টল হয়ে গেলে আবার পাথে খোঁজ
                new_path = shutil.which(tool_name)
                if new_path:
                    logger.info(f"✅ Installed {tool_name} via {manager}")
                    return new_path
            except subprocess.TimeoutExpired:
                logger.warning(f"⏱️ {manager} install timed out for {tool_name}")
            except subprocess.CalledProcessError as e:
                logger.debug(f"{manager} install failed: {e}")
            except Exception as e:
                logger.debug(f"{manager} error: {e}")

    # ৩. শেষ চেষ্টা: সরাসরি GitHub থেকে Download (যদি package manager না থাকে)
    logger.info(f"🌐 No package manager found. Trying GitHub download for {tool_name}...")
    downloaded_path = install_tool_from_github(tool_name)
    if downloaded_path:
        return downloaded_path

    # ৪. সব ব্যর্থ → ফ্যালব্যাক (None রিটার্ন)
    logger.warning(f"❌ Could not install {tool_name}. Using Python fallback.")
    return None


def install_tool_from_github(tool_name: str) -> Optional[str]:
    """
    GitHub API রিলিজ থেকে সরাসরি Windows বাইনারি ডাউনলোড করে।
    (শুধুমাত্র শেষ উপায় হিসেবে ব্যবহার করা হয়)
    """
    import requests
    import zipfile
    import io

    tool_info = INSTALL_COMMANDS.get(tool_name)
    if not tool_info:
        return None

    repo = tool_info["github_repo"]
    binary_name = tool_info["binary"]
    
    # GitHub API থেকে রিলিজ লিস্ট আনা
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"GitHub API error: {resp.status_code}")
            return None
        
        data = resp.json()
        assets = data.get("assets", [])
        
        # Windows বাইনারি খোঁজা (`.exe` বা `.zip` যা `.exe` ধারণ করে)
        target_url = None
        for asset in assets:
            name = asset["name"].lower()
            if "windows" in name or "win64" in name or "amd64" in name:
                if name.endswith(".exe"):
                    target_url = asset["browser_download_url"]
                    break
                elif name.endswith(".zip"):
                    target_url = asset["browser_download_url"]
                    break
        
        if not target_url:
            logger.warning(f"No Windows binary found in GitHub release for {tool_name}")
            return None

        # ডাউনলোড
        logger.info(f"⬇️ Downloading from: {target_url}")
        resp = requests.get(target_url, stream=True, timeout=30)
        if resp.status_code != 200:
            return None

        content = resp.content

        # ইউজারের Temp-এ সেভ
        temp_dir = Path(tempfile.gettempdir()) / "zero_recon_tools"
        temp_dir.mkdir(parents=True, exist_ok=True)

        if target_url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                exe_files = [f for f in zf.namelist() if f.endswith(".exe")]
                if not exe_files:
                    logger.warning("No .exe found in zip")
                    return None
                exe_name = exe_files[0]
                extracted_path = temp_dir / exe_name
                with open(extracted_path, 'wb') as f:
                    f.write(zf.read(exe_name))
                extracted_path.chmod(0o755)
                logger.info(f"✅ Extracted {exe_name} to {extracted_path}")
                return str(extracted_path)
        else:
            exe_path = temp_dir / binary_name
            with open(exe_path, 'wb') as f:
                f.write(content)
            exe_path.chmod(0o755)
            logger.info(f"✅ Downloaded {binary_name} to {exe_path}")
            return str(exe_path)

    except Exception as e:
        logger.error(f"GitHub download failed: {e}")
        return None
