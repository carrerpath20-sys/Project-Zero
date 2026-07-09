#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Package — Live Web Interface for Zero Recon
- Flask + SocketIO based real-time monitoring
- Live logs, phase status, and report viewer
- Auto-starts with `python -m dashboard.app`
"""
from .app import app, socketio

__all__ = [
    "app",
    "socketio"
]
