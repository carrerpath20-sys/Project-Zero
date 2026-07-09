#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profiler — Deterministic Code Style Profiler (No SBERT, 0MB download).
"""

import re
import json
import logging
from pathlib import Path

logger = logging.getLogger("ZeroRecon")

class Profiler:
    def __init__(self, config: Dict):
        self.config = config
        self.profile_dir = Path("state/profiles")
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def profile_js(self, target: str, js_content: str) -> Dict:
        if not js_content:
            return {"profile_id": target, "style_features": {}}
        lines = js_content.split('\n')
        features = {
            "comment_ratio": sum(1 for l in lines if l.strip().startswith(('//', '/*'))) / max(1, len(lines)),
            "indentation": "spaces" if "  " in js_content else "tabs" if "\t" in js_content else "mixed",
            "var_style": "camelCase" if re.search(r'[a-z]+[A-Z]', js_content) else "snake_case" if re.search(r'[a-z]+_[a-z]', js_content) else "unknown"
        }
        profile = {"profile_id": target, "style_features": features, "target": target}
        self._save(profile)
        return {"target": target, "features": features, "matches": [], "status": "profiled"}

    def _save(self, profile: Dict):
        try:
            with open(self.profile_dir / f"{profile['profile_id']}.json", 'w') as f:
                json.dump(profile, f, indent=2)
        except:
            pass
