"""
Groq Summarizer V2
Demonstrates structured prompts using XML tags compared to plain prompts using llama-3.3-70b-versatile.
"""

import os
import sys
from utils import get_groq_client

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1200

client = get_groq_client()

PLAIN_SYSTEM_PROMPT = """
You are a document summarizer. Please summarize the given document clearly.
Include the main points and any important details.
"""

XML_SYSTEM_PROMPT = """
<role>
You are an expert technical document analyst working for a US tech company.
Your summaries are used by engineering teams and hiring managers.
</role>

<rules>
- Be precise and factual. Never add information not present in the document.
- Use plain American English. No jargon unless it is in the document itself.
- Each section must appear exactly once, in the order specified below.
- If a section cannot be filled (e.g., no numbers exist), write "None found."
</rules>

<output_format>
Produce exactly these five sections in your response:

<summary>
2-3 sentences. The core purpose and main message of the document.
</summary>

<key_points>
4-6 bullet points. The most important facts, claims, or recommendations.
Each bullet starts with a bold keyword in ALL CAPS followed by a colon.
Example:  • TIMELINE: The project runs 8-10 weeks.
</key_points>

<numbers_and_data>
List every specific number, percentage, date, dollar amount, or statistic.
Format: "• [value] - [what it refers to]"
If none: write "• None found."
</numbers_and_data>

<action_items>
What should the READER do after reading this document?
List 2-4 concrete next steps as imperative sentences (Start with a verb).
</action_items>

<one_liner>
A single sentence under 20 words capturing the entire document's essence.
</one_liner>
</output_format>
"""


def read_file(path: str) -> str:
    if not os.path.exists(path):
        print(f"\n  [ERROR] File not found: '{path}'\n")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def call_groq(system_prompt: str, file_name: str, content: str) -> tuple:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please summarize this document.\n\nFile: {file_name}\n\n---\n{content}\n---"}
        ]
    )
    in_tok = response.usage.prompt_tokens if response.usage else 0
    out_tok = response.usage.completion_tokens if response.usage else 0
    return response.choices[0].message.content, in_tok, out_tok


def run_compare_mode(file_path: str, content: str):
    file_name = os.path.basename(file_path)

    print(f"\n   COMPARE MODE: Plain Prompt vs XML Structured Prompt")
    print(f"   File: {file_name} ({len(content):,} characters)\n")

    print("  Running PLAIN prompt...")
    plain_reply, plain_in, plain_out = call_groq(PLAIN_SYSTEM_PROMPT, file_name, content)

    print("  Running XML STRUCTURED prompt...\n")
    xml_reply, xml_in, xml_out = call_groq(XML_SYSTEM_PROMPT, file_name, content)

    print(f"  RESULT A - Plain Prompt (vague instructions)")
    print(plain_reply)
    print(f"\n  Tokens -> Input: {plain_in}  Output: {plain_out}\n")

    print(f"  RESULT B - XML Structured Prompt (precise instructions)")
    print(xml_reply)
    print(f"\n  Tokens -> Input: {xml_in}  Output: {xml_out}\n")

    print("  WHAT TO NOTICE:")
    print("  1. Does Result B have more consistent section headers?")
    print("  2. Did Result B include numbers/data that Result A missed?")
    print("  3. Is Result B more scannable and useful to an engineer?")
    print("  4. Could you write code to PARSE Result B reliably?")
    print()

    out_path = f"{file_name}_comparison.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"PROMPT COMPARISON - {file_name}\n\n")
        f.write("PLAIN PROMPT RESULT:\n")
        f.write(plain_reply + "\n\n")
        f.write("XML STRUCTURED PROMPT RESULT:\n")
        f.write(xml_reply + "\n")
    print(f"  Comparison saved to '{out_path}'\n")


def run_xml_mode(file_path: str, content: str):
    file_name = os.path.basename(file_path)
    print(f"\n  Summarizing with XML structured prompt...\n")
    reply, in_tok, out_tok = call_groq(XML_SYSTEM_PROMPT, file_name, content)

    print(f"   STRUCTURED SUMMARY: {file_name}\n")
    print(reply)
    print(f"\n  Tokens -> Input: {in_tok}  Output: {out_tok}\n")


if __name__ == "__main__":
    print("\n   Summarizer v2 (XML Prompts)\n")

    if len(sys.argv) < 2:
        print("  Usage:")
        print("    python summarize_v2.py <file>             ")
        print("    python summarize_v2.py <file> --compare   \n")
        sys.exit(1)

    file_path = sys.argv[1]
    compare = "--compare" in sys.argv

    content = read_file(file_path)
    print(f"\n  File: {os.path.basename(file_path)} ({len(content):,} chars)")

    if compare:
        run_compare_mode(file_path, content)
    else:
        run_xml_mode(file_path, content)