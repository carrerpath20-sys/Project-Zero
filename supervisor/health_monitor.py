#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  HEALTH MONITOR — Level 5: Added DNA folder disk check             █
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
    Level 5: DNA folder space check added.
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
        
        logger.info("🩺 HealthMonitor (Level 5) initialized.")
    
    def check_system_health(self) -> bool:
        """২০-পয়েন্ট চেক — সব পরীক্ষা চালায়, সমস্যা থাকলে False রিটার্ন করে"""
        checks = {
            "disk_space": self._check_disk_space(),
            "memory_usage": self._check_memory_usage(),
            "network_connectivity": self._check_network(),
            "os_health": self._check_os_health(),
            "temp_files_clean": self._check_temp_files(),
            "system_load": self._check_system_load(),
            "python_process": self._check_python_process(),
            "dna_disk_space": self._check_dna_disk_space()  # নতুন
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
            
            if self.consecutive_failures >= 3 and not self.recovery_attempted:
                self._attempt_recovery(failed_checks)
        
        return all_passed
    
    def is_healthy(self) -> bool:
        """শেষ চেকের ফলাফল রিটার্ন করে (পুনরায় চেক না করেই)"""
        now = datetime.now()
        if (now - self.last_check_time).total_seconds() > self.health_check_interval:
            return self.check_system_health()
        return self.last_healthy
    
    # ========== ইনডিভিজুয়াল চেক ==========
    def _check_disk_space(self) -> bool:
        if not self.psutil_available:
            return True
        try:
            usage = self.psutil.disk_usage('.')
            free_mb = usage.free / (1024 * 1024)
            if free_mb < self.disk_threshold_mb:
                logger.warning(f"⚠️ Low disk space: {free_mb:.0f}MB free")
                return False
            return True
        except:
            return True
    
    def _check_memory_usage(self) -> bool:
        if not self.psutil_available:
            return True
        try:
            memory = self.psutil.virtual_memory()
            used_percent = memory.percent
            if used_percent > self.memory_threshold_percent:
                logger.warning(f"⚠️ High memory usage: {used_percent}%")
                return False
            return True
        except:
            return True
    
    def _check_network(self) -> bool:
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
        try:
            if sys.platform == 'win32':
                import ctypes
                ctypes.windll.kernel32.GetTickCount64()
            return True
        except:
            return False
    
    def _check_temp_files(self) -> bool:
        temp_dir = Path(os.environ.get('TEMP', '/tmp'))
        if not temp_dir.exists():
            return True
        try:
            total_size = sum(f.stat().st_size for f in temp_dir.glob('*') if f.is_file())
            if total_size / (1024 * 1024) > 2000:
                logger.warning(f"⚠️ Large temp files: {total_size / (1024 * 1024):.0f}MB")
                return False
            return True
        except:
            return True
    
    def _check_system_load(self) -> bool:
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
        if not self.psutil_available:
            return True
        try:
            process = self.psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)
            if memory_mb > 2000:
                logger.warning(f"⚠️ Python process using {memory_mb:.0f}MB memory")
                return False
            return True
        except:
            return True
    
    def _check_dna_disk_space(self) -> bool:
        """Level 5: DNA ফোল্ডারের ডিস্ক স্পেস চেক"""
        dna_dir = Path("state/dna")
        if not dna_dir.exists():
            return True
        try:
            total_size = sum(f.stat().st_size for f in dna_dir.glob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            if size_mb > 500:  # ৫০০MB-এর বেশি হলে সতর্ক
                logger.warning(f"⚠️ DNA folder large: {size_mb:.0f}MB")
                # খুব বড় হলে (1GB) false
                if size_mb > 1000:
                    logger.error("❌ DNA folder exceeds 1GB. Health check failed.")
                    return False
            return True
        except:
            return True
    
    # ========== রিকভারি ==========
    def _attempt_recovery(self, failed_checks: List[str]):
        self.recovery_attempted = True
        logger.info("🔄 Attempting system recovery...")
        
        if "temp_files_clean" in failed_checks:
            temp_dir = Path(os.environ.get('TEMP', '/tmp'))
            if temp_dir.exists():
                count = sum(1 for f in temp_dir.glob('*.tmp') if f.unlink())
                if count:
                    logger.info(f"🧹 Cleaned {count} temp files.")
        
        if "disk_space" in failed_checks or "dna_disk_space" in failed_checks:
            cache_dir = Path("state/cache")
            if cache_dir.exists():
                count = sum(1 for f in cache_dir.glob('*.json') if f.name != 'cache_meta.json' and f.unlink())
                if count:
                    logger.info(f"🧹 Cleaned {count} cache files.")
        
        time.sleep(5)
        if self.check_system_health():
            self.recovery_attempted = False
            logger.info("✅ Recovery successful.")
        else:
            logger.warning("⚠️ Recovery unsuccessful. Continuing with limited functionality.")
    
    def get_health_report(self) -> Dict[str, any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "is_healthy": self.is_healthy(),
            "last_check_time": self.last_check_time.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "recovery_attempted": self.recovery_attempted,
            "disk_ok": self._check_disk_space(),
            "memory_ok": self._check_memory_usage(),
            "network_ok": self._check_network(),
            "dna_disk_ok": self._check_dna_disk_space()
        }
