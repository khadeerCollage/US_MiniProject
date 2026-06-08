"""
Common utilities for Groq project
Handles environment variables loading and Groq client initialization.
"""

import os
import sys


def load_env():
    if not os.environ.get("GROQ_API_KEY"):
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ[k.strip()] = v.strip().strip("'\"")
            except Exception:
                pass


def get_groq_client():
    load_env()
    try:
        import groq
    except ImportError:
        print("[ERROR] 'groq' not found. Run: pip install groq")
        sys.exit(1)

    if not os.environ.get("GROQ_API_KEY"):
        print("[ERROR] GROQ_API_KEY is not set.")
        sys.exit(1)

    return groq.Groq()
