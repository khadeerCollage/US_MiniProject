"""
Groq CLI Chatbot
Interactive CLI chatbot with conversation history and token usage tracking using llama-3.3-70b-versatile.
"""

import sys
from utils import get_groq_client

client = get_groq_client()

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024

messages = []
total_input_tokens = 0
total_output_tokens = 0


def send_to_groq(user_text: str) -> str:
    global total_input_tokens, total_output_tokens

    messages.append({
        "role": "user",
        "content": user_text
    })

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=messages
    )

    reply = response.choices[0].message.content

    messages.append({
        "role": "assistant",
        "content": reply
    })

    if response.usage:
        total_input_tokens += response.usage.prompt_tokens
        total_output_tokens += response.usage.completion_tokens

    return reply


def show_history():
    if not messages:
        print("\n  (No messages yet)\n")
        return
    print("\n  CONVERSATION HISTORY")
    for i, msg in enumerate(messages, 1):
        role = "You" if msg["role"] == "user" else "Groq"
        preview = msg["content"][:120].replace("\n", " ")
        if len(msg["content"]) > 120:
            preview += "..."
        print(f"  [{i}] {role}: {preview}")
    print()


def show_tokens():
    print(f"\n  Token usage this session:")
    print(f"     Input tokens (what you sent):      {total_input_tokens}")
    print(f"     Output tokens (what Groq sent):   {total_output_tokens}")
    print(f"     Total:                             {total_input_tokens + total_output_tokens}")
    print(f"     Messages in history:               {len(messages)}\n")


def print_banner():
    print("\n   Groq CLI Chatbot")
    print("   Commands: 'history' | 'tokens' | 'clear' | 'exit'\n")


if __name__ == "__main__":
    print_banner()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye!\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye"):
            show_tokens()
            print("  Goodbye! Great chatting with you.\n")
            break

        elif user_input.lower() == "history":
            show_history()
            continue

        elif user_input.lower() == "tokens":
            show_tokens()
            continue

        elif user_input.lower() == "clear":
            messages.clear()
            total_input_tokens = 0
            total_output_tokens = 0
            print("\n  History cleared. Starting fresh!\n")
            continue

        try:
            print("\nGroq: ", end="", flush=True)
            reply = send_to_groq(user_input)
            print(reply)
            print()

        except Exception as e:
            print(f"\n  Error: {e}\n")