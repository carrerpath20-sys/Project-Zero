#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EVOLUTION LOGGER — Self-Learning Memory for AI Agents
- Logs which tactics worked (e.g., "massdns fallback succeeded")
- Logs failures (e.g., "Cloudflare bypass failed due to rate limit")
- Healer Agent queries this to avoid repeating mistakes.
- Stores data in state/evolution_log.json
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ZeroRecon")

class EvolutionLogger:
    def __init__(self, base_dir: Path = Path("state")):
        self.base_dir = Path(base_dir)
        self.log_file = self.base_dir / "evolution_log.json"
        self.data = self._load()
    
    def _load(self) -> Dict:
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"entries": [], "stats": {"success": 0, "failure": 0}}
    
    def _save(self):
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.warning(f"Evolution log save failed: {e}")
    
    def log(self, event_type: str, target: str, phase: int, details: Dict, outcome: str):
        """
        event_type: e.g., "dns_bruteforce", "cloud_scan", "ai_analysis"
        outcome: "success" or "failure"
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "target": target,
            "phase": phase,
            "event_type": event_type,
            "outcome": outcome,
            "details": details
        }
        self.data["entries"].append(entry)
        
        # স্ট্যাটস আপডেট
        if outcome == "success":
            self.data["stats"]["success"] += 1
        else:
            self.data["stats"]["failure"] += 1
        
        # লিমিট: সর্বোচ্চ ১০০০ এন্ট্রি রাখি
        if len(self.data["entries"]) > 1000:
            self.data["entries"] = self.data["entries"][-1000:]
        
        self._save()
        logger.debug(f"📝 Evolution log: {event_type} -> {outcome}")
    
    def get_lesson(self, target: str, phase: int, event_type: str) -> Optional[str]:
        """
        কোনো টার্গেট/ফেজের জন্য আগের লেসন খোঁজে।
        রিটার্ন: "success" or "failure" or None
        """
        for entry in reversed(self.data["entries"]):
            if (entry["target"] == target and 
                entry["phase"] == phase and 
                entry["event_type"] == event_type):
                return entry["outcome"]
        return None
    
    def get_stats(self) -> Dict:
        """সামগ্রিক পরিসংখ্যান"""
        return self.data["stats"]
    
    def clear(self):
        """লগ মুছে ফেলা (রিসেট)"""
        self.data = {"entries": [], "stats": {"success": 0, "failure": 0}}
        self._save()
        logger.info("🗑️ Evolution log cleared.")