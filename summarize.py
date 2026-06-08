"""
Groq Document Summarizer
Injects file content into Groq context using llama-3.3-70b-versatile and produces a structured summary.
"""

import os
import sys
from utils import get_groq_client

client = get_groq_client()

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
MAX_FILE_CHARS = 60_000

SYSTEM_PROMPT = """
You are an expert document summarizer. When given a file's content, produce a
structured summary with EXACTLY these four sections:

<summary>
Write 2-3 sentences capturing the core purpose and main message of the document.
</summary>

<key_points>
List 4-6 of the most important points or takeaways, as bullet points.
</key_points>

<notable_details>
Mention any specific data, numbers, names, dates, or technical terms worth remembering.
</notable_details>

<one_liner>
A single sentence (under 20 words) that captures the document's essence.
</one_liner>

Be concise, accurate, and neutral. Do not add information not found in the document.
"""


def read_file(path: str) -> str:
    if not os.path.exists(path):
        print(f"\n  [ERROR] File not found: '{path}'\n")
        sys.exit(1)

    if not os.path.isfile(path):
        print(f"\n  [ERROR] That's a directory, not a file: '{path}'\n")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        print(f"\n  [ERROR] Could not read '{path}' as text.\n")
        sys.exit(1)


def summarize_file(file_path: str):
    print(f"\n  Reading: {file_path}")
    content = read_file(file_path)

    file_size = len(content)
    print(f"  File size: {file_size:,} characters")

    truncated = False
    if file_size > MAX_FILE_CHARS:
        print(f"\n  [WARNING] File is large ({file_size:,} chars). Truncating to {MAX_FILE_CHARS:,} chars.\n")
        content = content[:MAX_FILE_CHARS]
        truncated = True

    file_name = os.path.basename(file_path)
    print(f"\n  Sending to Groq for summarization...\n")

    user_message = f"""Please summarize the following file.

File name: {file_name}
{"[NOTE: File was truncated to fit context limit]" if truncated else ""}

File content:
---
{content}
---
"""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )

    summary = response.choices[0].message.content

    print(f"   SUMMARY OF: {file_name}\n")
    print(summary)
    print()
    if response.usage:
        print(f"  Tokens used -> Input: {response.usage.prompt_tokens} | Output: {response.usage.completion_tokens}\n")

    output_path = f"{file_name}_summary.txt"
    save = input(f"  Save summary to '{output_path}'? (y/n): ").strip().lower()
    if save == "y":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"SUMMARY OF: {file_name}\n\n")
            f.write(summary)
            f.write("\n")
        print(f"  Saved to '{output_path}'\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n  Usage: python summarize.py <file_path>")
        print("  Example: python summarize.py README.md\n")
        sys.exit(1)

    file_path = sys.argv[1]
    summarize_file(file_path)