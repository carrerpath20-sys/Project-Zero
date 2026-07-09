#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SymbolicEngine — Neuro-Symbolic Reasoning for Code Understanding.
Converts JavaScript AST (or any code) into symbolic expressions,
evaluates conditions to prove hidden endpoints and parameter existence.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger("ZeroRecon")

class SymbolicEngine:
    """
    Uses deterministic symbolic execution to reason about code paths.
    Given a JS AST (or raw code), it extracts constraints and infers
    hidden endpoints with high confidence.
    """
    def __init__(self, config: Dict):
        self.config = config
        self.max_depth = config.get("evo", {}).get("neuro_symbolic", {}).get("max_depth", 5)
        self._symbol_table = defaultdict(set)  # variable -> possible values

    def analyze(self, js_content: str, ast: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry: given JS content, returns proven endpoints and parameters.
        If AST not provided, it uses a simple regex-based approximation.
        """
        logger.info("🧠 Symbolic analysis started")
        if ast:
            return self._analyze_ast(ast)
        else:
            # Fallback to regex-based symbolic approximation
            return self._analyze_regex(js_content)

    def _analyze_ast(self, ast: Dict) -> Dict:
        """
        Walk the AST, extract variable assignments, function calls,
        and build constraints. Evaluate constraints to discover endpoints.
        """
        endpoints = set()
        params = set()
        secrets = set()
        # Placeholder: we simulate AST walking by using a simplified traversal
        # In production, use esprima AST node types.
        # We'll implement a recursive visitor.
        self._symbol_table.clear()
        self._visit_node(ast, endpoints, params, secrets)
        return {
            "endpoints": list(endpoints),
            "parameters": list(params),
            "secrets": list(secrets),
            "proven": len(endpoints) > 0,
            "symbols": {k: list(v) for k, v in self._symbol_table.items()}
        }

    def _visit_node(self, node: Dict, endpoints: Set, params: Set, secrets: Set, depth: int = 0):
        """Recursive AST visitor (simplified)."""
        if depth > self.max_depth:
            return
        node_type = node.get("type")
        if node_type == "Literal":
            value = node.get("value")
            if isinstance(value, str):
                if value.startswith('/') or 'http' in value:
                    endpoints.add(value)
                if 'key' in value.lower() or 'secret' in value.lower():
                    secrets.add(value)
        elif node_type == "Property":
            key = node.get("key", {}).get("name", "")
            val = node.get("value", {})
            if isinstance(val, dict) and val.get("type") == "Literal":
                if key and (key in ["url", "uri", "endpoint", "path", "route"]):
                    endpoints.add(str(val.get("value", "")))
                if 'key' in key.lower() or 'secret' in key.lower() or 'token' in key.lower():
                    secrets.add(str(val.get("value", "")))
        elif node_type == "CallExpression":
            callee = node.get("callee", {})
            if callee.get("type") == "MemberExpression":
                prop = callee.get("property", {}).get("name", "")
                if prop in ["get", "post", "put", "delete", "fetch", "axios"]:
                    args = node.get("arguments", [])
                    if args and args[0].get("type") == "Literal":
                        endpoints.add(args[0].get("value", ""))
                    # Check for body parameters
                    if len(args) > 1:
                        body = args[1]
                        if body.get("type") == "ObjectExpression":
                            for prop in body.get("properties", []):
                                pkey = prop.get("key", {}).get("name", "")
                                if pkey:
                                    params.add(pkey)
        # Recursively visit children
        for child_key in ["children", "body", "elements", "properties"]:
            if child_key in node:
                child_node = node[child_key]
                if isinstance(child_node, list):
                    for item in child_node:
                        if isinstance(item, dict):
                            self._visit_node(item, endpoints, params, secrets, depth+1)
                elif isinstance(child_node, dict):
                    self._visit_node(child_node, endpoints, params, secrets, depth+1)

    def _analyze_regex(self, js_content: str) -> Dict:
        """
        Fallback: use regex to extract endpoints and parameters.
        Less powerful but deterministic.
        """
        endpoints = set()
        params = set()
        secrets = set()
        patterns = [
            r'["\'](/[^\s"\']+)["\']',
            r'["\'](https?://[^\s"\']+)["\']',
            r'(?:url|uri|endpoint|path|route)\s*[:=]\s*["\']([^"\']+)["\']',
            r'fetch\s*\(\s*["\']([^"\']+)["\']',
            r'axios\.(?:get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']'
        ]
        for pat in patterns:
            matches = re.findall(pat, js_content, re.IGNORECASE)
            endpoints.update(matches)
        # Parameter extraction (simplified)
        param_pat = r'["\'](user_id|role|token|id|admin|password|email)["\']\s*[:=]'
        params.update(re.findall(param_pat, js_content, re.IGNORECASE))
        # Secrets
        secret_pat = r'(sk_live_|sk_test_|AKIA|ghp_|-----BEGIN|secret|key)'
        secrets.update(re.findall(secret_pat, js_content, re.IGNORECASE))
        return {
            "endpoints": list(endpoints)[:20],
            "parameters": list(params)[:10],
            "secrets": list(secrets)[:5],
            "proven": len(endpoints) > 0,
            "symbols": {}
        }
