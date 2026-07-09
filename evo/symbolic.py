#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SymbolicEngine — Neuro-Symbolic Reasoning with Esprima AST + Taint Analysis.
Uses real AST parsing to extract hidden endpoints, parameters, and secrets.
"""

import re
import json
import logging
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

logger = logging.getLogger("ZeroRecon")

class SymbolicEngine:
    """
    Level 5 Symbolic Engine: Uses Esprima for full AST parsing and taint tracking.
    """
    def __init__(self, config: Dict):
        self.config = config
        self.max_depth = config.get("evo", {}).get("neuro_symbolic", {}).get("max_depth", 5)
        self._esprima_available = False
        try:
            import esprima
            self.esprima = esprima
            self._esprima_available = True
        except ImportError:
            logger.warning("⚠️ Esprima not installed. Using regex fallback.")
        self._symbol_table = defaultdict(set)

    def analyze(self, js_content: str, ast: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry: analyze JS content, return endpoints, params, secrets.
        """
        if self._esprima_available and not ast:
            try:
                ast = self.esprima.parseScript(js_content, {'loc': True, 'comment': True})
                return self._analyze_ast(ast)
            except Exception as e:
                logger.error(f"❌ Esprima parse error: {e}. Falling back to regex.")
        return self._analyze_regex(js_content)

    def _analyze_ast(self, ast: Dict) -> Dict:
        endpoints = set()
        params = set()
        secrets = set()
        self._symbol_table.clear()
        self._walk_node(ast, endpoints, params, secrets)
        return {
            "endpoints": list(endpoints)[:30],
            "parameters": list(params)[:20],
            "secrets": list(secrets)[:10],
            "proven": len(endpoints) > 0,
            "symbols": {k: list(v)[:5] for k, v in self._symbol_table.items()}
        }

    def _walk_node(self, node: Dict, endpoints: Set, params: Set, secrets: Set, depth: int = 0):
        """Recursive AST walker with taint tracking."""
        if depth > self.max_depth:
            return
        node_type = node.get('type')
        if node_type == 'Literal':
            value = node.get('value')
            if isinstance(value, str):
                if value.startswith('/') or 'http' in value:
                    endpoints.add(value)
                if 'key' in value.lower() or 'secret' in value.lower():
                    secrets.add(value)
        elif node_type == 'Property':
            key = node.get('key', {})
            val = node.get('value', {})
            if key.get('type') == 'Identifier' and val.get('type') == 'Literal':
                k_name = key.get('name', '')
                v_val = val.get('value', '')
                if k_name in ['url', 'uri', 'endpoint', 'path', 'route']:
                    endpoints.add(str(v_val))
                if any(x in k_name.lower() for x in ['key', 'secret', 'token', 'password']):
                    secrets.add(str(v_val))
                self._symbol_table[k_name].add(str(v_val))
        elif node_type == 'CallExpression':
            callee = node.get('callee', {})
            if callee.get('type') == 'MemberExpression':
                prop = callee.get('property', {}).get('name', '')
                if prop in ['get', 'post', 'put', 'delete', 'fetch', 'axios']:
                    args = node.get('arguments', [])
                    if args and args[0].get('type') == 'Literal':
                        endpoints.add(args[0].get('value', ''))
                    # Taint: check body parameters
                    if len(args) > 1:
                        body = args[1]
                        if body.get('type') == 'ObjectExpression':
                            for prop_node in body.get('properties', []):
                                pkey = prop_node.get('key', {}).get('name', '')
                                if pkey:
                                    params.add(pkey)
                                    self._symbol_table['body_params'].add(pkey)
        # Recursive walk
        for child_key in ['children', 'body', 'consequent', 'alternate', 'elements', 'properties', 'arguments']:
            if child_key in node:
                child_node = node[child_key]
                if isinstance(child_node, list):
                    for item in child_node:
                        if isinstance(item, dict):
                            self._walk_node(item, endpoints, params, secrets, depth+1)
                elif isinstance(child_node, dict):
                    self._walk_node(child_node, endpoints, params, secrets, depth+1)

    def _analyze_regex(self, js_content: str) -> Dict:
        """Fallback regex-based analysis."""
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
            endpoints.update(re.findall(pat, js_content, re.IGNORECASE))
        param_pat = r'["\'](user_id|role|token|id|admin|password|email)["\']\s*[:=]'
        params.update(re.findall(param_pat, js_content, re.IGNORECASE))
        secret_pat = r'(sk_live_|sk_test_|AKIA|ghp_|-----BEGIN|secret|key)'
        secrets.update(re.findall(secret_pat, js_content, re.IGNORECASE))
        return {
            "endpoints": list(endpoints)[:20],
            "parameters": list(params)[:10],
            "secrets": list(secrets)[:5],
            "proven": len(endpoints) > 0,
            "symbols": {}
        }
