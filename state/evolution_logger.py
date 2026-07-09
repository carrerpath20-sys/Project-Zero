#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 EVOLUTION LOGGER (Level 5 — Evo & Debate Logging)
- Logs MCTS decisions, Mutation results, Debate verdicts, and Reflections.
- Stores data in state/evolution_log.json.
- Provides query methods for Healer Agent to learn from past mistakes.
- Auto-creates required directories (state/, dna/, profiles/, snapshots/).
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
        # নিশ্চিত করি ফোল্ডারগুলো আছে (state/, state/dna/, state/profiles/, state/snapshots/)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "dna").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "profiles").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "snapshots").mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.base_dir / "evolution_log.json"
        self.data = self._load()
    
    def _load(self) -> Dict:
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"entries": [], "stats": {"success": 0, "failure": 0, "debate_wins": 0}}
    
    def _save(self):
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Evolution log save failed: {e}")
    
    def log(self, event_type: str, target: str, phase: int, details: Dict, outcome: str):
        """Generic log method for any event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "target": target,
            "phase": phase,
            "event_type": event_type,
            "outcome": outcome,
            "details": details
        }
        self.data["entries"].append(entry)
        if outcome == "success":
            self.data["stats"]["success"] += 1
        else:
            self.data["stats"]["failure"] += 1
        
        if len(self.data["entries"]) > 1500:  # ১৫০০ এন্ট্রি পর্যন্ত রাখি
            self.data["entries"] = self.data["entries"][-1500:]
        self._save()
        logger.debug(f"📝 Evolution log: {event_type} -> {outcome}")
    
    # ---------- বিশেষায়িত লগ মেথড (Level 5) ----------
    def log_mcts(self, target: str, selected_path: str, confidence: float, all_paths: List):
        """Log MCTS search result."""
        self.log(
            event_type="mcts",
            target=target,
            phase=0,
            details={
                "selected_path": selected_path,
                "confidence": confidence,
                "all_paths": all_paths
            },
            outcome="success" if confidence > 0.6 else "failure"
        )
    
    def log_debate(self, target: str, verdict: str, flaws: List, rules_count: int):
        """Log Debate verdict."""
        outcome = "success" if verdict == "APPROVED" else "failure"
        if verdict == "APPROVED":
            self.data["stats"]["debate_wins"] += 1
        
        self.log(
            event_type="debate",
            target=target,
            phase=0,
            details={
                "verdict": verdict,
                "flaws": flaws[:5],
                "rules_count": rules_count
            },
            outcome=outcome
        )
    
    def log_mutation(self, target: str, rules_generated: int, source: str):
        """Log Mutator rule generation."""
        self.log(
            event_type="mutation",
            target=target,
            phase=0,
            details={
                "rules_generated": rules_generated,
                "source": source
            },
            outcome="success" if rules_generated > 0 else "failure"
        )
    
    def log_reflection(self, target: str, success_rate: float, dna_updated: bool, injected: bool):
        """Log Reflector DNA update."""
        self.log(
            event_type="reflection",
            target=target,
            phase=0,
            details={
                "success_rate": success_rate,
                "dna_updated": dna_updated,
                "injected": injected
            },
            outcome="success" if dna_updated else "failure"
        )
    
    # ---------- কুয়েরি মেথড (Healer Agent-এর জন্য) ----------
    def get_lesson(self, target: str, phase: int, event_type: str) -> Optional[str]:
        """Check previous outcomes for a specific event."""
        for entry in reversed(self.data["entries"]):
            if (entry["target"] == target and 
                entry["phase"] == phase and 
                entry["event_type"] == event_type):
                return entry["outcome"]
        # Generic fallback (without target)
        for entry in reversed(self.data["entries"]):
            if (entry["phase"] == phase and 
                entry["event_type"] == event_type):
                return entry["outcome"]
        return None
    
    def get_debate_history(self, target: str, limit: int = 5) -> List[Dict]:
        """Get recent debate results for a target."""
        return [e for e in self.data["entries"] 
                if e["target"] == target and e["event_type"] == "debate"][-limit:]
    
    def get_stats(self) -> Dict:
        """Return aggregated stats."""
        return self.data["stats"]
    
    def get_failures(self, target: str = None, limit: int = 20) -> List[Dict]:
        """Return recent failures for debugging."""
        failures = [e for e in self.data["entries"] if e["outcome"] == "failure"]
        if target:
            failures = [e for e in failures if e["target"] == target]
        return failures[-limit:]
    
    def clear(self):
        """Wipe evolution memory."""
        self.data = {"entries": [], "stats": {"success": 0, "failure": 0, "debate_wins": 0}}
        self._save()
        logger.info("🗑️ Evolution log cleared.")
