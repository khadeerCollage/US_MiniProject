"""
Chain-of-Thought Bot
Demonstrates Chain-of-Thought reasoning using Groq and llama-3.3-70b-versatile.
"""

import os
import re
import sys
from utils import get_groq_client

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 2048

client = get_groq_client()

NORMAL_SYSTEM_PROMPT = """
You are an expert AI engineering career advisor specializing in helping engineers
land jobs at top US AI companies like Anthropic, OpenAI, Google DeepMind, and Meta AI.

Answer questions clearly and helpfully. Be direct and practical.
"""

COT_SYSTEM_PROMPT = """
<role>
You are an expert AI engineering career advisor specializing in helping engineers
land jobs at top US AI companies: Anthropic, OpenAI, Google DeepMind, and Meta AI.
You have helped 100+ engineers navigate technical interviews and career transitions.
</role>

<thinking_instructions>
Before answering ANY question, you MUST reason through it using these exact steps inside
<thinking> tags. This is not optional. Do this even for questions that seem simple.

Step 1 — UNDERSTAND THE QUESTION:
  What is the person really asking? What is their underlying goal?
  Are there multiple interpretations? Which is most likely given context?

Step 2 — IDENTIFY WHAT I KNOW:
  What relevant facts, frameworks, or experiences apply here?
  What are the key variables or trade-offs involved?

Step 3 — REASON STEP BY STEP:
  Work through the problem logically.
  Consider: best case, worst case, most likely case.
  If there are options, evaluate each one explicitly.

Step 4 — CHECK MY REASONING:
  Does my conclusion follow from my reasoning?
  Am I missing an important consideration?
  Is there a common mistake I should warn the person about?
</thinking_instructions>

<output_format>
Your response MUST follow this exact format. No exceptions.

<thinking>
[Your full reasoning process using the 4 steps above.
Be thorough here — this is where the quality comes from.]
</thinking>

<answer>
[Your final, polished answer to the user.
This should be clear, direct, and actionable.
The user reads only this section — make it excellent.]
</answer>
</output_format>
"""


def extract_sections(text: str) -> tuple:
    """
    Parse the response to extract <thinking> and <answer> sections.
    """
    thinking_match = re.search(r"<thinking>(.*?)</thinking>", text, re.DOTALL)
    answer_match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL)

    thinking = thinking_match.group(1).strip() if thinking_match else ""
    answer = answer_match.group(1).strip() if answer_match else text.strip()

    return thinking, answer


def print_response(reply: str, show_thinking: bool, cot_mode: bool):
    """Display the response with optional thinking section."""
    if not cot_mode:
        print(f"\nAdvisor:\n{reply}\n")
        return

    thinking, answer = extract_sections(reply)

    if show_thinking and thinking:
        print("\nTHINKING PROCESS (type 'thinking' to toggle)")
        for line in thinking.split("\n"):
            trimmed = line.strip()
            if trimmed:
                print(f"  {trimmed}")
        print()

    print(f"\nAnswer:\n{answer}\n")


def print_mode_status(cot_mode: bool, show_thinking: bool):
    mode_label = "Chain-of-Thought ON" if cot_mode else "Normal Mode"
    think_label = "(thinking visible)" if (cot_mode and show_thinking) else "(thinking hidden)" if cot_mode else ""
    print(f"\n  Mode: {mode_label} {think_label}")
    print("  Commands: 'toggle' | 'thinking' | 'exit'\n")


def print_banner():
    print("\n   Chain-of-Thought Bot\n")
    print("  Ask complex career or technical questions.")
    print("  Toggle CoT on/off live to see how answers differ.")


if __name__ == "__main__":
    print_banner()

    cot_mode = True
    show_thinking = True
    messages = []

    print_mode_status(cot_mode, show_thinking)

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Goodbye!\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("\n  Goodbye!\n")
            break

        elif user_input.lower() == "toggle":
            cot_mode = not cot_mode
            messages.clear()
            print(f"\n  Switched to: {'Chain-of-Thought' if cot_mode else 'Normal'} mode")
            print_mode_status(cot_mode, show_thinking)
            continue

        elif user_input.lower() == "thinking":
            if not cot_mode:
                print("\n  Enable CoT mode first (type 'toggle')\n")
                continue
            show_thinking = not show_thinking
            status = "visible" if show_thinking else "hidden"
            print(f"\n  Thinking section is now {status}\n")
            continue

        messages.append({"role": "user", "content": user_input})
        
        system = COT_SYSTEM_PROMPT if cot_mode else NORMAL_SYSTEM_PROMPT
        api_messages = [{"role": "system", "content": system}] + messages

        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=api_messages
            )

            reply = response.choices[0].message.content
            messages.append({"role": "assistant", "content": reply})

            print_response(reply, show_thinking, cot_mode)
            
            in_tokens = response.usage.prompt_tokens if response.usage else 0
            out_tokens = response.usage.completion_tokens if response.usage else 0
            print(f"  Tokens -> Input: {in_tokens}  Output: {out_tokens}\n")

        except Exception as e:
            print(f"\n  API Error: {e}\n")