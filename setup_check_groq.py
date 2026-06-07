"""
Groq API Live Connection Test
Sends a single non-streaming message to Groq using llama-3.3-70b-versatile to verify the API key is active.
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


def main():
    load_env()
    
    try:
        import groq
    except ImportError:
        print("[ERROR] 'groq' not found. Run: pip install groq")
        sys.exit(1)

    if not os.environ.get("GROQ_API_KEY"):
        print("[ERROR] GROQ_API_KEY is not set.")
        sys.exit(1)

    client = groq.Groq()
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=80,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Groq connection test successful.'"
                }
            ]
        )
        reply = response.choices[0].message.content
        print(f"Groq: {reply}")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")


if __name__ == "__main__":
    main()
