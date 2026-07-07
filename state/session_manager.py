#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SESSION MANAGER — Tracks current scan state, checkpoints, and resumes.
- Saves current target, completed phases, and partial results.
- Creates checkpoints so you can resume after a crash.
- Uses atomic writes (temp file + rename) to avoid corruption.
"""
import os
import json
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("ZeroRecon")

class SessionManager:
    def __init__(self, base_dir: Path = Path("state")):
        self.base_dir = Path(base_dir)
        self.session_file = self.base_dir / "session.json"
        self.checkpoint_dir = self.base_dir / "checkpoint"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.data = self._load()
    
    def _load(self) -> Dict:
        """সেশন ফাইল লোড করে, না থাকলে ডিফল্ট তৈরি করে"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except:
                logger.warning("⚠️ Corrupt session.json. Creating new.")
        return {"sessions": []}
    
    def _save(self):
        """Atomic write (temp + rename) দিয়ে সেশন সেভ করে"""
        temp_file = self.session_file.with_suffix(".tmp")
        try:
            with open(temp_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            temp_file.rename(self.session_file)
        except Exception as e:
            logger.error(f"❌ Failed to save session: {e}")
    
    def start_session(self, target: str, phases: List[int] = None) -> str:
        """নতুন সেশন শুরু করে এবং ইউনিক ID রিটার্ন করে"""
        session_id = f"{target}_{int(time.time())}"
        new_session = {
            "session_id": session_id,
            "target": target,
            "start_time": datetime.now().isoformat(),
            "phases": phases or list(range(1, 16)),  # 1-15
            "completed_phases": [],
            "current_phase": 0,
            "status": "running",
            "results_summary": {}
        }
        self.data["sessions"].append(new_session)
        self._save()
        logger.info(f"🆕 Started session: {session_id}")
        return session_id
    
    def update_progress(self, session_id: str, phase: int, result: Dict):
        """একটি ফেজ শেষ হলে আপডেট করে"""
        for sess in self.data["sessions"]:
            if sess["session_id"] == session_id:
                if phase not in sess["completed_phases"]:
                    sess["completed_phases"].append(phase)
                sess["current_phase"] = phase
                sess["results_summary"][f"phase_{phase}"] = {
                    "status": result.get("status", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }
                self._save()
                self._save_checkpoint(session_id, sess)
                break
    
    def _save_checkpoint(self, session_id: str, session_data: Dict):
        """রিকভারির জন্য চেকপয়েন্ট ফাইল তৈরি করে"""
        cp_file = self.checkpoint_dir / f"{session_id}.json"
        try:
            with open(cp_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            logger.debug(f"💾 Checkpoint saved: {cp_file}")
        except Exception as e:
            logger.warning(f"Checkpoint save failed: {e}")
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """সেশন আইডি দিয়ে ডেটা খোঁজে"""
        for sess in self.data["sessions"]:
            if sess["session_id"] == session_id:
                return sess
        return None
    
    def get_latest_session(self, target: str = None) -> Optional[Dict]:
        """সবশেষ সেশন খোঁজে (যদি টার্গেট দেওয়া থাকে)"""
        sessions = self.data["sessions"]
        if target:
            sessions = [s for s in sessions if s["target"] == target]
        if not sessions:
            return None
        return max(sessions, key=lambda s: s["start_time"])
    
    def finish_session(self, session_id: str, status: str = "completed"):
        """সেশন শেষ মার্ক করে"""
        for sess in self.data["sessions"]:
            if sess["session_id"] == session_id:
                sess["status"] = status
                sess["end_time"] = datetime.now().isoformat()
                self._save()
                break
        logger.info(f"🏁 Session {session_id} finished ({status})")