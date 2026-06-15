"""
agent2_insights.py - Insight Generation Agent

This module demonstrates how an agent receives structured output (from Agent 1)
and processes both the natural language summary and raw stats to produce
actionable insights. It implements Chain-of-Thought (CoT) reasoning.

How to test standalone:
    python agent2_insights.py
"""

import os
import sys
import json
import re

# Add the parent directory to sys.path so we can import from utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import get_groq_client

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024

client = get_groq_client()

# SYSTEM PROMPT — Agent 2 uses CoT for better insight quality
AGENT2_SYSTEM_PROMPT = """
<role>
You are a senior business analyst and career strategist specializing in
the AI/tech job market. You transform data summaries into strategic, actionable insights.
</role>

<task>
Receive a dataset summary and produce 4-6 high-quality, specific insights.
Each insight must be directly supported by the data. No generic observations.
</task>

<thinking_process>
Before generating insights, reason through these steps inside <thinking> tags:
1. What is the most surprising or non-obvious finding in this data?
2. What patterns appear across multiple data points?
3. What would be most valuable for a job seeker in this market to know?
4. What specific actions do these numbers suggest?
</thinking_process>

<output_format>
<thinking>
[Your reasoning process - work through all 4 steps above]
</thinking>

<insights>
[Numbered list of 4-6 insights. Each insight must:]
[1. Start with a bold CATEGORY in ALL CAPS]
[2. State the specific data-backed finding]
[3. Explain the implication or recommended action]

Format:
1. **CATEGORY**: [Finding] - [Implication/Action]

Example:
1. **SALARY STRATEGY**: Remote roles average $162k vs $205k on-site - 
   a $43k gap that narrows significantly at senior levels, suggesting 
   remote engineers should target senior titles to close the compensation gap.
</insights>

<top_opportunity>
The single highest-value action a job seeker should take based on this data.
One sentence. Be specific - include company names, skills, or numbers if relevant.
</top_opportunity>
</output_format>

<rules>
- Every insight must cite at least one specific number from the data.
- Prioritize insights that lead to CONCRETE ACTIONS, not just observations.
- Tailor insights for someone wanting to get hired at a US AI company.
</rules>
"""


def generate_insights(agent1_result: dict, verbose: bool = False) -> dict:
    """
    Agent 2 main function.

    Args:
        agent1_result: Output dict from agent1_summarize.summarize_csv()
        verbose:       Print progress if True

    Returns:
        dict with status, insights, insight_count, thinking, top_opportunity
    """
    if agent1_result.get("status") != "success":
        return {"status": "error", "error": "Agent 1 did not succeed. Cannot generate insights."}

    summary = agent1_result["summary"]
    raw_stats = agent1_result.get("raw_stats", {})
    file_name = agent1_result.get("file_name", "unknown")
    rows = agent1_result.get("row_count", "?")
    cols = agent1_result.get("col_count", "?")

    if verbose:
        print(f"Agent 2 Generating insights from {file_name} ({rows} rows)...")

    # Build the input — Agent 2 uses BOTH the summary AND the raw stats
    numeric_stats = raw_stats.get("numeric_stats", "Not available")
    cat_stats = json.dumps(raw_stats.get("categorical_stats", {}), indent=2)[:1000]

    user_message = f"""
Generate strategic insights from this AI job market data.

DATASET: {file_name} ({rows} rows x {cols} columns)

NATURAL LANGUAGE SUMMARY (from Agent 1):
{summary}

RAW NUMERIC STATISTICS (for precise data referencing):
{numeric_stats}

TOP CATEGORICAL VALUES:
{cat_stats}

Generate 4-6 actionable insights for an engineer targeting US AI company jobs.
"""

    if verbose:
        print("Agent 2 Calling model with CoT prompt...")

    # Call Groq API compatible with OpenAI library format
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": AGENT2_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )
        full_output = response.choices[0].message.content
    except Exception as e:
        return {"status": "error", "error": f"Groq API call failed: {e}"}

    # Extract <thinking> and <insights> sections separately
    thinking_match = re.search(r"<thinking>(.*?)</thinking>", full_output, re.DOTALL)
    insights_match = re.search(r"<insights>(.*?)</insights>",  full_output, re.DOTALL)
    opportunity_match = re.search(r"<top_opportunity>(.*?)</top_opportunity>", full_output, re.DOTALL)

    thinking = thinking_match.group(1).strip() if thinking_match else ""
    insights = insights_match.group(1).strip() if insights_match else full_output
    opportunity = opportunity_match.group(1).strip() if opportunity_match else ""

    # Count actual insights (numbered items)
    insight_count = len(re.findall(r"^\s*\d+\.", insights, re.MULTILINE))

    # Handle usage tokens
    usage = getattr(response, "usage", None)
    input_tokens = usage.prompt_tokens if usage else 0
    output_tokens = usage.completion_tokens if usage else 0

    if verbose:
        print(f"Agent 2 Generated {insight_count} insights ({len(insights)} chars)")
        print(f"Agent 2 Tokens -> Input: {input_tokens} | Output: {output_tokens}")

    return {
        "status": "success",
        "insights": insights,
        "thinking": thinking,
        "top_opportunity": opportunity,
        "full_output": full_output,
        "insight_count": insight_count,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens
        }
    }


# Standalone test
if __name__ == "__main__":
    try:
        from validators import validate_summary, validate_insights
    except ImportError:
        validate_summary = None
        validate_insights = None
        print("Warning: validators module not found. Validation steps will be skipped.")

    try:
        from agent1_summarize import summarize_csv
    except ImportError:
        print("Error: agent1_summarize.py is required for the standalone test.")
        sys.exit(1)

    csv_path = "sample_data.csv"

    print("\nAgent 2 - Insight Generation (standalone test)\n")

    print("Step 1: Running Agent 1...")
    a1 = summarize_csv(csv_path, verbose=True)

    if validate_summary:
        vr1 = validate_summary(a1.get("summary", ""))
        if not vr1.passed:
            print(f"Agent 1 validation failed:\n{vr1}")
            sys.exit(1)
        print(f"Agent 1 validation: {vr1}\n")
    else:
        print("Agent 1 validation skipped.\n")

    print("Step 2: Running Agent 2...")
    a2 = generate_insights(a1, verbose=True)

    print("\nAgent 2 Output")
    if a2.get("thinking"):
        print(f"\nTHINKING PROCESS:\n{a2['thinking'][:400]}...\n")
    print(f"INSIGHTS:\n{a2['insights']}")
    
    if a2.get("top_opportunity"):
        print(f"\nTOP OPPORTUNITY: {a2['top_opportunity']}")

    if validate_insights:
        print("\nValidation")
        vr2 = validate_insights(a2.get("insights", ""))
        print(vr2)
    else:
        print("\nAgent 2 validation skipped.")
