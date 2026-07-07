#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  ZERO RECON FRAMEWORK — MAIN ENTRY POINT                              █
█  Aggressive, Modular, Windows-Native Recon Automation                █
█  (c) 2026 Zero Labs — Offensive Security Research                   █
████████████████████████████████████████████████████████████████████████████

এই ফাইলটি হল পুরো ফ্রেমওয়ার্কের দরজা। এটি:
- কমান্ড-লাইন আর্গুমেন্ট পার্স করে
- কনফিগারেশন লোড করে
- সুপারভাইজার (মাস্টার অর্কেস্ট্রেটর) স্টার্ট করে
- এবং পুরো রিকন প্রক্রিয়া চালু করে

Windows 10/11, Python 3.8+ এ টেস্টেড।
"""

import sys
import os
import argparse
import logging
import yaml
from pathlib import Path
from datetime import datetime

# ===================== [ লগার সেটআপ ] =====================
def setup_logging(verbose: bool = False):
    """কনসোল ও ফাইল — দুই জায়গায় লগ লেখার ব্যবস্থা"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '[%(asctime)s] %(levelname)-8s %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # ফাইল হ্যান্ডলার (প্রতিটি রানের জন্য আলাদা লগ ফাইল)
    log_dir = Path("outputs/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"zero_recon_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logging.getLogger().addHandler(file_handler)
    
    return logging.getLogger("ZeroRecon")

# ===================== [ কনফিগ লোডার ] =====================
def load_config(config_path: str = "config.yaml") -> dict:
    """YAML কনফিগ ফাইল লোড করে। না থাকলে ডিফল্ট তৈরি করে"""
    if not Path(config_path).exists():
        logging.warning(f"⚠️ Config file '{config_path}' not found. Creating default.")
        default_config = {
            "framework": {
                "name": "Zero Recon",
                "version": "1.0.0",
                "author": "Zero Labs"
            },
            "ai": {
                "cerebras": {
                    "enabled": True,
                    "api_key": "YOUR_CEREBRAS_API_KEY",
                    "base_url": "https://api.cerebras.ai/v1/chat/completions",
                    "models": {
                        "high": "gpt-oss-120b",
                        "medium": "gemma-4-31b",
                        "low": "zai-glm-4.7"
                    },
                    "limits": {"max_rpm": 5, "max_rpd": 2400}
                },
                "openrouter": {
                    "enabled": True,
                    "api_key": "YOUR_OPENROUTER_API_KEY",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions",
                    "fallback_models": {
                        "high": "nvidia/nemotron-3-ultra",
                        "medium": "poolside/laguna-m.1",
                        "low": "openai/gpt-oss-20b"
                    },
                    "limits": {"max_rpd": 50}
                }
            },
            "scan": {
                "ports": [443, 8443, 465, 80, 8080],
                "timeout": 10,
                "retries": 5,
                "delay_between_requests": 1.5,
                "max_threads": 5,
                "max_subdomains_to_scan": 100
            },
            "auto_install": True,
            "output_dir": "outputs",
            "state_dir": "state"
        }
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        logging.info(f"✅ Default config created at: {config_path}")
        return default_config
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# ===================== [ মেইন ফাংশন ] =====================
def main():
    """প্রধান এন্ট্রি পয়েন্ট — CMD থেকে এটাই প্রথমে কল হয়"""
    parser = argparse.ArgumentParser(
        description="Zero Recon Framework — Windows-native AI-powered reconnaissance",
        epilog="Example: python main.py example.com --verbose"
    )
    parser.add_argument(
        "target",
        help="Target domain (e.g., example.com)"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging"
    )
    parser.add_argument(
        "--auto-install", "-a",
        action="store_true",
        help="Auto-install missing tools without prompting"
    )
    parser.add_argument(
        "--resume", "-r",
        help="Resume from a previous session ID (checkpoint)"
    )
    parser.add_argument(
        "--phases", "-p",
        help="Comma-separated list of phases to run (e.g., 1,2,5)"
    )
    parser.add_argument(
        "--output", "-o",
        default="outputs",
        help="Output directory (default: outputs)"
    )
    
    args = parser.parse_args()
    
    # ১. লগার সেটআপ
    logger = setup_logging(args.verbose)
    logger.info("="*70)
    logger.info("🔍 ZERO RECON FRAMEWORK v1.0.0 (Windows-Native)")
    logger.info("="*70)
    logger.info(f"🎯 Target: {args.target}")
    logger.info(f"📁 Config: {args.config}")
    logger.info(f"📁 Output: {args.output}")
    if args.auto_install:
        logger.info("📦 Auto-install mode: ENABLED")
    
    # ২. কনফিগ লোড
    try:
        config = load_config(args.config)
        logger.info("✅ Configuration loaded successfully.")
    except Exception as e:
        logger.critical(f"❌ Failed to load config: {e}")
        sys.exit(1)
    
    # ৩. API Keys চেক
    cerebras_key = config.get("ai", {}).get("cerebras", {}).get("api_key", "")
    openrouter_key = config.get("ai", {}).get("openrouter", {}).get("api_key", "")
    
    if not cerebras_key or "YOUR_" in cerebras_key:
        logger.warning("⚠️ Cerebras API Key is missing or default. Please set it in config.yaml")
    if not openrouter_key or "YOUR_" in openrouter_key:
        logger.warning("⚠️ OpenRouter API Key is missing or default. Please set it in config.yaml")
    
    # ৪. ডিরেক্টরি তৈরি
    for dir_name in [config.get("output_dir", "outputs"), config.get("state_dir", "state")]:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    # ৫. সুপারভাইজার স্টার্ট
    try:
        from supervisor.orchestrator import SupervisorOrchestrator
        logger.info("🚀 Initializing Supervisor...")
        
        supervisor = SupervisorOrchestrator(
            target=args.target,
            config=config,
            auto_install=args.auto_install,
            resume_session=args.resume,
            phases_to_run=args.phases
        )
        
        # ৬. মিশন শুরু
        logger.info("🔥 Starting reconnaissance mission...")
        results = supervisor.run()
        
        # ৭. রিপোর্ট
        if results:
            logger.info("✅ Mission complete! Report saved to outputs/reports/")
            print("\n" + "="*60)
            print("🎯 MISSION COMPLETE")
            print("="*60)
            print(f"📊 Subdomains found: {len(results.get('subdomains', []))}")
            print(f"📊 Live hosts: {len(results.get('live_hosts', []))}")
            print(f"📊 Vulnerabilities flagged: {len(results.get('vulnerabilities', []))}")
            print("="*60)
            print(f"📁 Full report: outputs/reports/report_{args.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        else:
            logger.error("❌ Mission failed. Check logs for details.")
            sys.exit(1)
            
    except ImportError as e:
        logger.critical(f"❌ Supervisor module not found. Make sure you're in the project root and all files are present.")
        logger.critical(f"   Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"❌ Unhandled exception: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)
    
    logger.info("🛑 Zero Recon shutdown complete.")

if __name__ == "__main__":
    main()