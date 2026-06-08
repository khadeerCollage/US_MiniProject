"""
Groq API Live Connection Test
Sends a single non-streaming message to Groq using llama-3.3-70b-versatile to verify the API key is active.
"""

import sys
from utils import get_groq_client


def main():
    client = get_groq_client()
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
        sys.exit(1)


if __name__ == "__main__":
    main()
