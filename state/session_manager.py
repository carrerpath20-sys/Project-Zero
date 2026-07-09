#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 SESSION MANAGER (Level 5 — Evo Metadata Support)
- Tracks current scan state, checkpoints, and resumes.
- Saves current target, completed phases, and partial results.
- NOW SAVES: MCTS results, Debate verdicts, Mutator rules.
- Uses atomic writes (temp file + rename) to avoid corruption.
- Handles large JSON blobs (DNA/vectors) safely.
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
        """Load session file, or create default if missing/corrupt."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("⚠️ Corrupt session.json. Creating new.")
        return {"sessions": []}
    
    def _save(self):
        """Atomic write (temp + rename) to prevent corruption."""
        temp_file = self.session_file.with_suffix(".tmp")
        try:
            with open(temp_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
            temp_file.rename(self.session_file)
        except Exception as e:
            logger.error(f"❌ Failed to save session: {e}")
    
    def start_session(self, target: str, phases: List[int] = None) -> str:
        """Start a new session with a unique ID."""
        session_id = f"{target}_{int(time.time())}"
        new_session = {
            "session_id": session_id,
            "target": target,
            "start_time": datetime.now().isoformat(),
            "phases": phases or list(range(1, 16)),
            "completed_phases": [],
            "current_phase": 0,
            "status": "running",
            "results_summary": {},
            # Level 5: Evo metadata fields
            "evo_meta": {}
        }
        self.data["sessions"].append(new_session)
        self._save()
        logger.info(f"🆕 Session started: {session_id}")
        return session_id
    
    def update_progress(self, session_id: str, phase: int, result: Dict):
        """Update progress after a phase completes."""
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
    
    # ================================================================
    # Level 5: Evo Metadata Management
    # ================================================================
    def update_evo_meta(self, session_id: str, evo_data: Dict):
        """
        Update the Evo metadata (MCTS, Debate, Mutator, etc.) for a session.
        """
        for sess in self.data["sessions"]:
            if sess["session_id"] == session_id:
                sess["evo_meta"].update(evo_data)
                self._save()
                # Also update checkpoint for consistency
                self._save_checkpoint(session_id, sess)
                logger.debug(f"🧬 Evo meta updated for {session_id}")
                break
    
    def _save_checkpoint(self, session_id: str, session_data: Dict):
        """Save a recovery checkpoint with full Evo metadata."""
        cp_file = self.checkpoint_dir / f"{session_id}.json"
        try:
            with open(cp_file, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            logger.debug(f"💾 Checkpoint saved: {cp_file.name}")
        except Exception as e:
            logger.warning(f"Checkpoint save failed: {e}")
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a specific session by ID."""
        for sess in self.data["sessions"]:
            if sess["session_id"] == session_id:
                return sess
        return None
    
    def get_latest_session(self, target: str = None) -> Optional[Dict]:
        """Get the latest session, optionally filtered by target."""
        sessions = self.data["sessions"]
        if target:
            sessions = [s for s in sessions if s["target"] == target]
        if not sessions:
            return None
        return max(sessions, key=lambda s: s["start_time"])
    
    def finish_session(self, session_id: str, status: str = "completed"):
        """Mark a session as finished."""
        for sess in self.data["sessions"]:
            if sess["session_id"] == session_id:
                sess["status"] = status
                sess["end_time"] = datetime.now().isoformat()
                self._save()
                logger.info(f"🏁 Session {session_id} finished ({status})")
                return
        logger.warning(f"Session {session_id} not found to finish.")
    
    def clear_session(self, session_id: str):
        """Remove a session and its checkpoint."""
        self.data["sessions"] = [s for s in self.data["sessions"] if s["session_id"] != session_id]
        self._save()
        cp_file = self.checkpoint_dir / f"{session_id}.json"
        if cp_file.exists():
            cp_file.unlink()
        logger.info(f"🗑️ Cleared session {session_id}")
