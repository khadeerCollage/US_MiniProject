"""
Common utilities for Groq project
Handles environment variables loading and Groq client initialization.
"""

import os
import sys


def load_env():
    from dotenv import load_dotenv
    load_dotenv()


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
