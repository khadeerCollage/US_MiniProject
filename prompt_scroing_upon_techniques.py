"""
Prompt Comparison Harness
Tests multiple prompt strategies on the same input using Groq and llama-3.3-70b-versatile.
"""

import os
import sys
import time
from utils import get_groq_client

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024

client = get_groq_client()

TEST_INPUTS = {
    "default": """
Anthropic recently published research showing that their Claude models can significantly
outperform previous benchmarks on multi-step reasoning tasks when given structured prompts.
The study tested 3 prompt patterns: simple instructions, XML-structured instructions, and
chain-of-thought instructions. Results showed XML prompts improved output consistency by 47%
compared to simple prompts. Chain-of-thought prompts showed the highest accuracy on complex
tasks (89% vs 71%) but used 2.3x more tokens on average.

The research team recommends: use simple prompts for straightforward tasks, XML prompts
for any task requiring structured output, and chain-of-thought for multi-step reasoning.
They note that few-shot examples (2-5) combined with XML tags provided the best balance
of quality and token efficiency for production applications.

Engineers using these techniques in production reported 60% fewer retries due to malformed
output and a 35% reduction in prompt iteration time during development.
""",

    "career": """
A software engineer with 4 years of experience in backend development (Python, Java, AWS)
is considering transitioning into AI engineering. They have no direct ML experience but have
recently completed the fast.ai course and built 3 small projects using the Anthropic API:
a CLI chatbot, a document summarizer, and a multi-agent pipeline. They are based in Hyderabad,
India, and want to work remotely for a US AI company within 6 months. Their current salary
is $35,000/year. US remote AI engineering roles typically pay $120,000-$180,000/year.
They have received encouraging feedback from a US-based mentor who works at a top AI lab.
""",

    "technical": """
The messages array in the Anthropic Claude API is a list of dictionaries, each containing
a 'role' (user or assistant) and 'content' (string). Unlike stateful APIs, Claude has no
memory between API calls. Each request must include the complete conversation history.
This means token usage grows linearly with conversation length. For a 10-turn conversation
with 100 tokens per turn, the 10th request sends approximately 1000 tokens of context.

Token limits: claude-sonnet-4-6 supports 200,000 input tokens. At $3 per million input
tokens, a 1000-token request costs $0.003. For production chatbots with high traffic,
context management strategies like summarizing old messages or using sliding windows are
essential for cost control. The system prompt is included in every request and counts
toward the input token total.
""",
}


PROMPTS = {
    "simple": {
        "label":       "SIMPLE — Plain instruction",
        "description": "One sentence. No structure. Model guesses the format.",
        "system":      "Analyze the following text and provide a summary with key insights.",
    },

    "xml": {
        "label":       "XML — Structured with tags",
        "description": "Explicit sections. Format rules. Predictable every run.",
        "system": """
<role>
You are an expert analyst. Your output will be used in engineering reports and
decision-making documents. Precision and structure are critical.
</role>

<rules>
- Stick strictly to information in the provided text. No additions.
- Use the exact section headers specified below.
- Bullet points must start with a bold keyword in ALL CAPS followed by a colon.
</rules>

<output_format>
<summary>
2-3 sentences. The core finding or situation described in the text.
</summary>

<key_insights>
4-6 bullet points. Most important facts or conclusions.
Format: • KEYWORD: description
</key_insights>

<numbers>
Every specific metric, percentage, dollar amount, or time value.
Format: • [number] — what it measures
If none: • None found
</numbers>

<recommendation>
1-3 concrete actions based on the evidence in the text.
Start each with an action verb.
</recommendation>
</output_format>
""",
    },

    "cot": {
        "label":       "COT — Chain-of-Thought + XML",
        "description": "Forces step-by-step reasoning before the answer.",
        "system": """
<role>
You are an expert analyst helping engineers and decision-makers extract maximum
value from technical and business documents.
</role>

<thinking_process>
Before producing any output, think through these steps inside <thinking> tags:
1. What TYPE of content is this? (research, career info, technical spec, etc.)
2. What is the most important thing a reader NEEDS to know?
3. What numbers or data points are present, and what do they imply?
4. What is the single most actionable insight?
</thinking_process>

<output_format>
<thinking>
[Your reasoning process — 4 steps above. Be explicit.]
</thinking>

<summary>
2-3 sentences. The core message.
</summary>

<key_insights>
4-6 bullet points. Format: • KEYWORD: insight
</key_insights>

<numbers>
Every metric with context. Format: • [value] — meaning
</numbers>

<recommendation>
Top 2-3 actions. Start each with a verb.
</recommendation>

<confidence>
Rate your confidence in this analysis: High / Medium / Low
One sentence explaining why.
</confidence>
</output_format>
""",
    },
}

SCORING_DIMENSIONS = [
    ("Structure",    "Does the output have clear, consistent sections?"),
    ("Completeness", "Are all key points from the source captured?"),
    ("Numbers",      "Are specific data points extracted and labeled?"),
    ("Actionable",   "Does it tell you what to DO next?"),
    ("Parseable",    "Could you extract sections reliably with code?"),
]


def run_prompt(name: str, prompt_config: dict, user_input: str) -> dict:
    start_time = time.time()

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": prompt_config["system"]},
            {"role": "user", "content": f"Analyze this text:\n\n{user_input}"}
        ]
    )

    elapsed = time.time() - start_time
    in_tokens = response.usage.prompt_tokens if response.usage else 0
    out_tokens = response.usage.completion_tokens if response.usage else 0

    return {
        "name":          name,
        "label":         prompt_config["label"],
        "description":   prompt_config["description"],
        "reply":         response.choices[0].message.content,
        "input_tokens":  in_tokens,
        "output_tokens": out_tokens,
        "elapsed_sec":   round(elapsed, 2),
    }


def display_result(result: dict, index: int, total: int):
    print(f"\n  RESULT {index}/{total}:  {result['label']}")
    print(f"  {result['description']}")
    print(f"  {result['elapsed_sec']}s  |  Input: {result['input_tokens']} tok  |  Output: {result['output_tokens']} tok\n")
    print(result["reply"])


def display_comparison_table(results: list):
    print("\n\n  COMPARISON SUMMARY\n")
    print(f"  {'Prompt':<12}  {'Time':>6}  {'Input':>8}  {'Output':>8}  {'Total':>8}")
    for r in results:
        total_tok = r["input_tokens"] + r["output_tokens"]
        print(f"  {r['name']:<12}  {r['elapsed_sec']:>5.1f}s  {r['input_tokens']:>7}  {r['output_tokens']:>7}  {total_tok:>7}")
    print()


def display_scoring_guide(results: list):
    print("\n  SCORE EACH RESULT (do this manually — it builds your intuition)\n")
    print(f"  {'Dimension':<16}  {'What to look for'}")
    for dim, desc in SCORING_DIMENSIONS:
        print(f"  {dim:<16}  {desc}")
    print("\n  Grade each on 1-5 for all three prompts.")
    print("  Highest total score = best prompt for this type of content.\n")

    names = [r["name"] for r in results]
    header = f"  {'Dimension':<14}  " + "  ".join(f"{n:>7}" for n in names)
    print(header)
    for dim, _ in SCORING_DIMENSIONS:
        row = f"  {dim:<14}  " + "  ".join(f"{'___':>7}" for _ in names)
        print(row)
    print()


def save_report(results: list, test_input: str, topic: str):
    out_path = f"harness_results_{topic}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"PROMPT HARNESS RESULTS — Topic: {topic}\n\n")
        f.write("TEST INPUT:\n")
        f.write(test_input.strip() + "\n\n")

        for r in results:
            f.write(f"{r['label']}\n")
            f.write(f"Time: {r['elapsed_sec']}s | Tokens: {r['input_tokens']} in / {r['output_tokens']} out\n\n")
            f.write(r["reply"] + "\n\n")

    print(f"  Full report saved to '{out_path}'\n")
    return out_path


if __name__ == "__main__":
    print("\n   Prompt Comparison Harness\n")

    topic = "default"
    test_input = ""

    if len(sys.argv) >= 2 and sys.argv[1] not in ("--topic",):
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(f"\n  File not found: '{file_path}'\n")
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            test_input = f.read()
        topic = os.path.basename(file_path).replace(".txt", "")
        print(f"\n  Test input: {file_path} ({len(test_input):,} chars)")

    elif "--topic" in sys.argv:
        idx = sys.argv.index("--topic")
        if idx + 1 < len(sys.argv):
            topic = sys.argv[idx + 1]
            if topic not in TEST_INPUTS:
                print(f"\n  Unknown topic '{topic}'. Using 'default'.")
                print(f"  Available: {', '.join(TEST_INPUTS.keys())}\n")
                topic = "default"
        test_input = TEST_INPUTS[topic]
        print(f"\n  Test topic: {topic} ({len(test_input):,} chars)")

    else:
        test_input = TEST_INPUTS["default"]
        print(f"\n  Using default test input ({len(test_input):,} chars)")
        print("  Tip: run with --topic career or --topic technical for other inputs")

    print(f"\n  Running all 3 prompts on the same input...")
    print(f"  Model: {MODEL}  |  Max tokens per response: {MAX_TOKENS}\n")

    results = []
    for i, (name, config) in enumerate(PROMPTS.items(), 1):
        print(f"  [{i}/3] Running {config['label']}...", end="", flush=True)
        result = run_prompt(name, config, test_input)
        results.append(result)
        print(f"  done ({result['elapsed_sec']}s)")

    for i, result in enumerate(results, 1):
        display_result(result, i, len(results))

    display_comparison_table(results)
    display_scoring_guide(results)

    report_path = save_report(results, test_input, topic)

    print("\n  Harness complete!")
    print(f"  Open '{report_path}' to review and score all 3 outputs.\n")