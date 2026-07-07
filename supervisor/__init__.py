#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  SUPERVISOR PACKAGE — ZERO RECON FRAMEWORK                           █
█  This package contains the core orchestration logic:                █
█  - orchestrator: main supervisor loop (ARTEMIS-style)              █
█  - api_router: hybrid AI router with key rotation                 █
█  - context_manager: token caching and context tracking            █
█  - health_monitor: 20-point crash shield                         █
████████████████████████████████████████████████████████████████████████████
"""

from .orchestrator import SupervisorOrchestrator
from .api_router import AIRouter
from .context_manager import ContextManager
from .health_monitor import HealthMonitor

__all__ = [
    "SupervisorOrchestrator",
    "AIRouter",
    "ContextManager",
    "HealthMonitor"
]
