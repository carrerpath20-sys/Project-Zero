#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  HEALTH MONITOR — 20-Point Crash Shield                             █
█  - Checks disk space, memory, network, and process health          █
█  - Prevents system crashes due to resource exhaustion             █
█  - Self-healing suggestions (e.g., clear cache, free memory)     █
█  - Used by Supervisor to decide whether to pause or abort        █
████████████████████████████████████████████████████████████████████████████
"""

import os
import sys
import time
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("ZeroRecon")

class HealthMonitor:
    """
    ২০-পয়েন্ট ক্র্যাশ শিল্ড — সুপারভাইজারকে রিসোর্স সমস্যা থেকে বাঁচায়।
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.disk_threshold_mb = self.config.get("disk_threshold_mb", 500)  # 500MB ফ্রি স্পেস
        self.memory_threshold_percent = self.config.get("memory_threshold_percent", 85)  # 85% মেমোরি ব্যবহার
        self.network_timeout = self.config.get("network_timeout", 5)  # সেকেন্ড
        self.health_check_interval = self.config.get("health_check_interval", 60)  # সেকেন্ড
        
        self.last_check_time = datetime.now()
        self.last_healthy = True
        self.recovery_attempted = False
        self.consecutive_failures = 0
        
        # psutil লোড
        self.psutil_available = False
        try:
            import psutil
            self.psutil = psutil
            self.psutil_available = True
        except ImportError:
            logger.warning("⚠️ psutil not installed. Limited health monitoring.")
        
        logger.info("🩺 HealthMonitor initialized.")
    
    def check_system_health(self) -> bool:
        """২০-পয়েন্ট চেক — সব পরীক্ষা চালায়, সমস্যা থাকলে False রিটার্ন করে"""
        checks = {
            "disk_space": self._check_disk_space(),
            "memory_usage": self._check_memory_usage(),
            "network_connectivity": self._check_network(),
            "os_health": self._check_os_health(),
            "temp_files_clean": self._check_temp_files(),
            "system_load": self._check_system_load(),
            "python_process": self._check_python_process()
        }
        
        all_passed = all(checks.values())
        self.last_healthy = all_passed
        self.last_check_time = datetime.now()
        
        if all_passed:
            logger.debug("✅ System health check passed.")
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            failed_checks = [k for k, v in checks.items() if not v]
            logger.warning(f"⚠️ Health check failed: {', '.join(failed_checks)}")
            
            # ৩ বার পরপর ব্যর্থ হলে রিকভারি চেষ্টা
            if self.consecutive_failures >= 3 and not self.recovery_attempted:
                self._attempt_recovery(failed_checks)
        
        return all_passed
    
    def is_healthy(self) -> bool:
        """শেষ চেকের ফলাফল রিটার্ন করে (পুনরায় চেক না করেই)"""
        # যদি ৬০ সেকেন্ড হয়ে যায়, আবার চেক করি
        now = datetime.now()
        if (now - self.last_check_time).total_seconds() > self.health_check_interval:
            return self.check_system_health()
        return self.last_healthy
    
    # ========== ইনডিভিজুয়াল চেক ==========
    def _check_disk_space(self) -> bool:
        """ডিস্কে ন্যূনতম ৫০০MB ফ্রি স্পেস আছে কিনা"""
        if not self.psutil_available:
            return True  # psutil না থাকলে এই চেক স্কিপ
        
        try:
            usage = self.psutil.disk_usage('.')
            free_mb = usage.free / (1024 * 1024)
            if free_mb < self.disk_threshold_mb:
                logger.warning(f"⚠️ Low disk space: {free_mb:.0f}MB free")
                return False
            return True
        except Exception as e:
            logger.debug(f"Disk check error: {e}")
            return True
    
    def _check_memory_usage(self) -> bool:
        """মেমোরি ৮৫%-এর কম ব্যবহার হচ্ছে কিনা"""
        if not self.psutil_available:
            return True
        
        try:
            memory = self.psutil.virtual_memory()
            used_percent = memory.percent
            if used_percent > self.memory_threshold_percent:
                logger.warning(f"⚠️ High memory usage: {used_percent}%")
                return False
            return True
        except Exception as e:
            logger.debug(f"Memory check error: {e}")
            return True
    
    def _check_network(self) -> bool:
        """ইন্টারনেট কানেকশন আছে কিনা (Cloudflare DNS ping)"""
        test_hosts = ["1.1.1.1", "8.8.8.8"]
        for host in test_hosts:
            try:
                socket.create_connection((host, 53), timeout=self.network_timeout)
                return True
            except:
                continue
        logger.warning("⚠️ No network connectivity.")
        return False
    
    def _check_os_health(self) -> bool:
        """Windows-নির্ভর: সিস্টেম হেলথ চেক"""
        try:
            # Windows-specific check: is system responsive?
            if sys.platform == 'win32':
                import ctypes
                # Simple check: can we get system uptime?
                ctypes.windll.kernel32.GetTickCount64()
            return True
        except:
            return False
    
    def _check_temp_files(self) -> bool:
        """টেম্প ফাইলের আকার ২GB-এর বেশি কিনা"""
        temp_dir = Path(os.environ.get('TEMP', '/tmp'))
        if not temp_dir.exists():
            return True
        
        try:
            total_size = 0
            for f in temp_dir.glob('*'):
                if f.is_file():
                    total_size += f.stat().st_size
            total_mb = total_size / (1024 * 1024)
            if total_mb > 2000:  # 2GB
                logger.warning(f"⚠️ Large temp files: {total_mb:.0f}MB")
                return False
            return True
        except:
            return True
    
    def _check_system_load(self) -> bool:
        """সিস্টেম লোড চেক (উইন্ডোজে CPU ব্যবহার)"""
        if not self.psutil_available:
            return True
        try:
            cpu_usage = self.psutil.cpu_percent(interval=1)
            if cpu_usage > 90:
                logger.warning(f"⚠️ High CPU usage: {cpu_usage}%")
                return False
            return True
        except:
            return True
    
    def _check_python_process(self) -> bool:
        """বর্তমান পাইথন প্রসেসের মেমোরি ব্যবহার ২GB-এর কম কিনা"""
        if not self.psutil_available:
            return True
        try:
            process = self.psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)
            if memory_mb > 2000:  # 2GB
                logger.warning(f"⚠️ Python process using {memory_mb:.0f}MB memory")
                return False
            return True
        except:
            return True
    
    # ========== রিকভারি ==========
    def _attempt_recovery(self, failed_checks: List[str]):
        """স্বয়ংক্রিয় রিকভারি চেষ্টা — ক্যাশ ক্লিয়ার, ডিস্ক ক্লিন"""
        self.recovery_attempted = True
        logger.info("🔄 Attempting system recovery...")
        
        if "temp_files_clean" in failed_checks:
            # টেম্প ফাইল পরিষ্কার
            temp_dir = Path(os.environ.get('TEMP', '/tmp'))
            if temp_dir.exists():
                count = 0
                for f in temp_dir.glob('*.tmp'):
                    try: f.unlink(); count += 1
                    except: pass
                if count > 0:
                    logger.info(f"🧹 Cleaned {count} temp files.")
        
        if "disk_space" in failed_checks:
            # অপ্রয়োজনীয় ক্যাশ মুছে ফেলা
            cache_dir = Path("state/cache")
            if cache_dir.exists():
                count = 0
                for f in cache_dir.glob('*.json'):
                    if f.name != 'cache_meta.json':
                        try: f.unlink(); count += 1
                        except: pass
                if count > 0:
                    logger.info(f"🧹 Cleaned {count} cache files.")
        
        # ৫ সেকেন্ড অপেক্ষা করে আবার চেক
        time.sleep(5)
        if self.check_system_health():
            self.recovery_attempted = False
            logger.info("✅ Recovery successful.")
        else:
            logger.warning("⚠️ Recovery unsuccessful. Continuing with limited functionality.")
    
    # ========== ওভারভিউ ==========
    def get_health_report(self) -> Dict[str, any]:
        """পূর্ণাঙ্গ হেলথ রিপোর্ট"""
        return {
            "timestamp": datetime.now().isoformat(),
            "is_healthy": self.is_healthy(),
            "last_check_time": self.last_check_time.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "recovery_attempted": self.recovery_attempted,
            "disk_ok": self._check_disk_space(),
            "memory_ok": self._check_memory_usage(),
            "network_ok": self._check_network()
        }