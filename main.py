#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
████████████████████████████████████████████████████████████████████████████
█  ZERO RECON FRAMEWORK — MAIN ENTRY POINT (Level 5)                  █
█  Aggressive, Modular, Windows-Native Recon Automation              █
█  (c) 2026 Zero Labs — Offensive Security Research                 █
█  Flags: --god-mode, --aggressive-debate, --dashboard             █
████████████████████████████████████████████████████████████████████████████
"""

import sys
import os
import argparse
import logging
import yaml
import subprocess
from pathlib import Path
from datetime import datetime

# =====================================================================
#  লগার সেটআপ
# =====================================================================
def setup_logging(verbose: bool = False):
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '[%(asctime)s] %(levelname)-8s %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # ফাইল হ্যান্ডলার
    log_dir = Path("outputs/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"zero_recon_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logging.getLogger().addHandler(file_handler)
    
    return logging.getLogger("ZeroRecon")

# =====================================================================
#  কনফিগ লোডার
# =====================================================================
def load_config(config_path: str = "config.yaml") -> dict:
    if not Path(config_path).exists():
        logging.warning(f"⚠️ Config file '{config_path}' not found. Creating default.")
        default_config = {
            "framework": {"name": "Zero Recon", "version": "1.0.0", "author": "Zero Labs"},
            "ai": {
                "cerebras": {
                    "enabled": True,
                    "api_key": "YOUR_CEREBRAS_API_KEY",
                    "base_url": "https://api.cerebras.ai/v1/chat/completions",
                    "models": {"high": "gpt-oss-120b", "medium": "gemma-4-31b", "low": "zai-glm-4.7"},
                    "limits": {"max_rpm": 5, "max_rpd": 2400}
                },
                "openrouter": {
                    "enabled": True,
                    "api_key": "YOUR_OPENROUTER_API_KEY",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions",
                    "fallback_models": {"high": "nvidia/nemotron-3-ultra", "medium": "poolside/laguna-m.1", "low": "openai/gpt-oss-20b"},
                    "limits": {"max_rpd": 50}
                }
            },
            "scan": {"ports": [443, 8443, 465, 80, 8080], "timeout": 10, "retries": 5, "delay_between_requests": 1.5, "max_threads": 5, "max_subdomains_to_scan": 100},
            "auto_install": True,
            "output_dir": "outputs",
            "state_dir": "state",
            "evo": {
                "mcts": {"enabled": False},
                "neuro_symbolic": {"enabled": False},
                "adversarial_debate": {"enabled": False}
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        return default_config
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# =====================================================================
#  মেইন ফাংশন
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Zero Recon Framework v2.0 (Level 5) — Windows-native AI-powered reconnaissance",
        epilog="Example: python main.py example.com --god-mode --verbose"
    )
    
    # টার্গেট
    parser.add_argument("target", help="Target domain (e.g., example.com)")
    
    # কনফিগ
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to config file")
    
    # অপশন
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--auto-install", "-a", action="store_true", help="Auto-install missing tools")
    parser.add_argument("--resume", "-r", help="Resume from a previous session ID")
    parser.add_argument("--phases", "-p", help="Comma-separated list of phases to run (e.g., 1,2,5)")
    parser.add_argument("--output", "-o", default="outputs", help="Output directory")
    parser.add_argument("--all", action="store_true", help="Run all phases (1-15)")
    
    # ================================================================
    #  Level 5 এক্সক্লুসিভ ফ্ল্যাগ
    # ================================================================
    parser.add_argument(
        "--god-mode", 
        action="store_true", 
        help="Enable all Evo engines (MCTS, Symbolic, Mutator, Reflector) for maximum intelligence"
    )
    parser.add_argument(
        "--aggressive-debate", 
        action="store_true", 
        help="Enable Adversarial Multi-Agent Debate (WAF bypass validation) — increases API calls by ~2"
    )
    parser.add_argument(
        "--dashboard", 
        action="store_true", 
        help="Start the live Flask/SocketIO dashboard (requires dashboard/ folder)"
    )
    
    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    
    # ================================================================
    #  ড্যাশবোর্ড চালানোর লজিক (যদি ফ্ল্যাগ দেওয়া হয়)
    # ================================================================
    if args.dashboard:
        logger.info("🌐 Launching Zero Recon Dashboard...")
        try:
            # ড্যাশবোর্ডটি আলাদা প্রক্রিয়ায় চালু করি
            subprocess.Popen([sys.executable, "-m", "dashboard.app"])
            logger.info("✅ Dashboard started at http://localhost:5000")
        except Exception as e:
            logger.error(f"❌ Failed to start dashboard: {e}. Make sure dashboard/ folder exists.")
        # ড্যাশবোর্ড চালানোর পরও মূল স্ক্যান চালানো হবে (ব্যাকগ্রাউন্ডে ড্যাশবোর্ড চলবে)
    
    # ================================================================
    #  কনফিগ লোড
    # ================================================================
    logger.info("="*70)
    logger.info("🔍 ZERO RECON FRAMEWORK v2.0 (Level 5 — God-Tier)")
    logger.info("="*70)
    logger.info(f"🎯 Target: {args.target}")
    logger.info(f"📁 Config: {args.config}")
    logger.info(f"📁 Output: {args.output}")
    
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.critical(f"❌ Failed to load config: {e}")
        sys.exit(1)
    
    # ================================================================
    #  Level 5 ফ্ল্যাগ → কনফিগ ইনজেক্ট
    # ================================================================
    if args.god_mode:
        logger.info("🧠 GOD MODE ENABLED: Activating MCTS, Symbolic, Mutator, Reflector")
        config["evo"] = config.get("evo", {})
        config["evo"]["mcts"] = {"enabled": True, "max_paths": 3}
        config["evo"]["neuro_symbolic"] = {"enabled": True, "max_depth": 5}
        # Mutator ও Reflector ডিফল্ট ইভোতে থাকে, আমরা নিশ্চিত করি
        config["evo"]["mutator"] = {"enabled": True}
        config["evo"]["reflector"] = {"enabled": True}
        # DNA ও Profiler ইতিমধ্যেই ডিফল্ট

    if args.aggressive_debate:
        logger.info("⚖️ AGGRESSIVE DEBATE ENABLED: Activating Attacker vs Defender validation")
        config["evo"] = config.get("evo", {})
        config["evo"]["adversarial_debate"] = {"enabled": True, "rounds": 3, "temperature": 0.5}
    
    # --all ফ্ল্যাগ হ্যান্ডেল (যদি --phases না দেওয়া থাকে)
    if args.all:
        args.phases = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15"
        logger.info("🎯 Running ALL 15 phases.")
    
    # ================================================================
    #  ডিরেক্টরি তৈরি
    # ================================================================
    for dir_name in [config.get("output_dir", "outputs"), config.get("state_dir", "state")]:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    # ================================================================
    #  সুপারভাইজার স্টার্ট
    # ================================================================
    try:
        from supervisor.orchestrator import SupervisorOrchestrator
        logger.info("🚀 Initializing Supervisor (Level 5)...")
        
        supervisor = SupervisorOrchestrator(
            target=args.target,
            config=config,  # ইনজেক্টেড কনফিগ
            auto_install=args.auto_install,
            resume_session=args.resume,
            phases_to_run=args.phases
        )
        
        # ================================================================
        #  মিশন শুরু
        # ================================================================
        logger.info("🔥 Starting reconnaissance mission...")
        results = supervisor.run()
        
        if results:
            logger.info("✅ Mission complete! Report saved to outputs/reports/")
            print("\n" + "="*60)
            print("🎯 MISSION COMPLETE")
            print("="*60)
            print(f"📊 Subdomains found: {len(results.get('subdomains', []))}")
            print(f"📊 Live hosts: {len(results.get('live_hosts', []))}")
            print(f"📊 Vulnerabilities flagged: {len(results.get('vulnerabilities', []))}")
            if results.get('evo_meta'):
                print(f"🧠 Evo Meta: MCTS={results['evo_meta'].get('mcts', {}).get('selected', 'N/A')}")
                print(f"⚖️ Debate Verdict: {results['evo_meta'].get('debate', {}).get('verdict', 'N/A')}")
            print("="*60)
            print(f"📁 Full report: outputs/reports/report_{args.target}_*.json")
        else:
            logger.error("❌ Mission failed. Check logs for details.")
            sys.exit(1)
            
    except ImportError as e:
        logger.critical(f"❌ Supervisor module not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"❌ Unhandled exception: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)
    
    logger.info("🛑 Zero Recon shutdown complete.")

if __name__ == "__main__":
    main()
