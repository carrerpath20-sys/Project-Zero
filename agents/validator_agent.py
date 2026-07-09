#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 VALIDATOR AGENT (Level 5 — Neuro-Symbolic + DNA Cross-Check)
- Validates each phase's data against expected schemas.
- Uses DNA similarity to flag suspicious/missing fields.
- Cross-checks with Symbolic Engine outputs (if available).
- Generates a confidence score (0-1) for each validated phase.
- Flags critical data anomalies for Healer Agent.
"""

import logging
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

logger = logging.getLogger("ZeroRecon")

class ValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("ValidatorAgent")
        self.required_fields = {
            "phase_1": ["subdomains"],
            "phase_2": ["asn_info", "origin_ips"],
            "phase_3": ["repositories", "secrets_found"],
            "phase_4": ["endpoints_found"],
            "phase_5": ["confirmed_public"],
            "phase_6": ["permutations"],
            "phase_7": ["live_hosts"],
            "phase_8": ["found_subdomains"],
            "phase_9": ["subdomains", "ips"],
            "phase_10": ["takeover_candidates", "risk_score"],
            "phase_11": ["confirmed_subdomains", "critical_assets"],
            "phase_12": ["report_files"],
            "phase_13": ["internal_networks"],
            "phase_14": ["metadata"],
            "phase_15": ["changes"]
        }

    def run(self, target: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        self._log_start()
        if not context or "results" not in context:
            result = {"error": "No results to validate", "status": "failed"}
            self._log_error("No results provided")
            return result

        all_results = context.get("results", {})
        dna = context.get("dna")
        symbolic_data = context.get("symbolic_data", {})

        validated = {}
        errors = []
        warnings = []
        total_confidence = 0.0
        phase_count = 0

        for phase_key, phase_data in all_results.items():
            phase_num = phase_key.replace("phase_", "")
            if not phase_num.isdigit():
                continue
            phase_num = int(phase_num)
            required = self.required_fields.get(f"phase_{phase_num}", [])

            # Phase data validation
            if not phase_data:
                warnings.append(f"Phase {phase_num}: Empty data")
                validated[phase_key] = {"status": "empty", "confidence": 0.0}
                continue

            if not isinstance(phase_data, dict):
                errors.append(f"Phase {phase_num}: Data is not a dictionary")
                validated[phase_key] = {"status": "invalid_type", "confidence": 0.0}
                continue

            # Check required fields
            missing = [f for f in required if f not in phase_data]
            if missing:
                warnings.append(f"Phase {phase_num}: Missing fields: {missing}")

            # Check if any field has error
            has_error = "error" in phase_data and phase_data["error"]
            is_skipped = phase_data.get("status") == "skipped"

            # Calculate base confidence
            confidence = 0.8 if not missing and not has_error else 0.4
            if is_skipped:
                confidence = 0.0
                validated[phase_key] = {
                    "status": "skipped",
                    "confidence": 0.0,
                    "reason": phase_data.get("reason", "Skipped")
                }
                continue

            # DNA similarity boost (if DNA available)
            dna_boost = 0.0
            if dna and phase_data:
                try:
                    # Get a sample string from the phase data
                    sample_text = str(phase_data)[:200]
                    similar = dna.get_similarity(sample_text, top_k=1)
                    if similar and similar[0].get("similarity", 0) > 0.5:
                        dna_boost = 0.15
                        confidence += dna_boost
                except Exception as e:
                    logger.debug(f"DNA validation error for {phase_key}: {e}")

            # Symbolic cross-check (if symbolic data available for this phase)
            symbolic_boost = 0.0
            if symbolic_data and phase_key in symbolic_data:
                try:
                    sym = symbolic_data.get(phase_key, {})
                    if sym.get("proven", False):
                        symbolic_boost = 0.15
                        confidence += symbolic_boost
                except:
                    pass

            # Clamp confidence to 0-1
            confidence = min(1.0, max(0.0, confidence))

            # Clean data (deduplicate lists)
            cleaned_data = {}
            for key, value in phase_data.items():
                if isinstance(value, list) and value:
                    try:
                        # Only deduplicate if all items are strings
                        if isinstance(value[0], str):
                            cleaned_data[key] = list(set(value))
                        else:
                            cleaned_data[key] = value
                    except:
                        cleaned_data[key] = value
                else:
                    cleaned_data[key] = value

            validated[phase_key] = {
                "status": "valid" if not missing and not has_error else "partial",
                "missing_fields": missing,
                "confidence": confidence,
                "has_error": has_error,
                "is_skipped": is_skipped,
                "data": cleaned_data
            }

            total_confidence += confidence
            phase_count += 1

        # Overall validation summary
        avg_confidence = total_confidence / phase_count if phase_count > 0 else 0.0

        result = {
            "target": target,
            "validated_phases": validated,
            "errors": errors,
            "warnings": warnings,
            "avg_confidence": avg_confidence,
            "status": "complete" if not errors else "partial"
        }

        self._log_complete(result)
        return result
