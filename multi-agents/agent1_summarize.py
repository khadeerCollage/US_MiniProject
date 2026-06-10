"""
agent1_summarize.py - CSV Summarization Agent
Loads a CSV file, generates a statistical profile, and uses Groq to produce a natural-language summary.
"""

import os
import sys
import json
import pandas as pd

# Add the parent directory to sys.path so we can import from utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import get_groq_client

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024

client = get_groq_client()

# SYSTEM PROMPT — Specific to Agent 1's summarization task
AGENT1_SYSTEM_PROMPT = """
<role>
You are a data analyst specializing in workforce and compensation data.
Your job is to translate raw CSV statistics into clear, professional English summaries.
</role>

<task>
You will receive statistical data from a CSV file (output of pandas describe()).
Produce a clear, factual natural-language summary.
</task>

<output_format>
Your response MUST follow this exact structure:

<dataset_overview>
2-3 sentences: What is this dataset about? How many rows/columns?
</dataset_overview>

<key_statistics>
Bullet points summarizing the most important numerical facts.
Include: ranges, averages, and any obvious distributions.
Format: • METRIC: value (context)
</key_statistics>

<data_quality_notes>
1-2 sentences: Any missing values, outliers, or data quality issues noticed.
</data_quality_notes>

<summary_sentence>
One sentence (under 25 words) capturing the dataset's core story.
</summary_sentence>
</output_format>

<rules>
- Only report what is in the data. No speculation.
- Use plain English. Avoid statistical jargon.
- Always include actual numbers from the statistics.
</rules>
"""


def load_and_profile_csv(path: str) -> tuple:
    """
    Load CSV with pandas and extract a rich statistical profile.
    Returns a tuple of (profile_dict, dataframe).
    """
    df = pd.read_csv(path)

    profile = {
        "file_name":    os.path.basename(path),
        "total_rows":   len(df),
        "total_cols":   len(df.columns),
        "columns":      list(df.columns),
        "dtypes":       df.dtypes.astype(str).to_dict(),
        "missing_vals": df.isnull().sum().to_dict(),
    }

    # Numeric summary (describe gives count, mean, std, min, 25%, 50%, 75%, max)
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        profile["numeric_stats"] = df[numeric_cols].describe().round(2).to_string()

    # Categorical summary — top values per column
    cat_cols = df.select_dtypes(include=["object"]).columns
    if len(cat_cols) > 0:
        cat_summary = {}
        for col in cat_cols:
            value_counts = df[col].value_counts()
            cat_summary[col] = {
                "unique_count": int(df[col].nunique()),
                "top_values":   value_counts.head(5).to_dict()
            }
        profile["categorical_stats"] = cat_summary

    return profile, df


def summarize_csv(path: str, verbose: bool = False) -> dict:
    """
    Agent 1 main function.

    Args:
        path:    Path to the CSV file
        verbose: Print progress if True

    Returns:
        {
          "status":    "success" | "error"
          "summary":   str — Groq's natural language summary
          "raw_stats": dict — pandas profile
          "file_name": str
          "row_count":  int
          "col_count":  int
        }
    """
    if verbose:
        print(f"  [Agent 1] Loading CSV: {path}")

    # Step 1: Load and profile
    if not os.path.exists(path):
        return {"status": "error", "error": f"File not found: {path}"}

    try:
        profile, df = load_and_profile_csv(path)
    except Exception as e:
        return {"status": "error", "error": f"CSV load failed: {e}"}

    if verbose:
        print(f"  [Agent 1] Loaded {profile['total_rows']} rows x {profile['total_cols']} cols")
        print(f"  [Agent 1] Sending to Groq for natural language summary...")

    # Step 2: Build LLM's input message
    user_message = f"""
Please summarize the following CSV dataset statistics.

FILE: {profile['file_name']}
DIMENSIONS: {profile['total_rows']} rows x {profile['total_cols']} columns
COLUMNS: {', '.join(profile['columns'])}

MISSING VALUES:
{json.dumps({k: v for k, v in profile['missing_vals'].items() if v > 0} or {"none": 0}, indent=2)}

NUMERIC STATISTICS (from pandas describe):
{profile.get('numeric_stats', 'No numeric columns')}

CATEGORICAL COLUMN SUMMARIES:
{json.dumps(profile.get('categorical_stats', {}), indent=2)[:2000]}
"""

    # Step 3: Call Groq
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": AGENT1_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )

    summary_text = response.choices[0].message.content

    prompt_tokens = response.usage.prompt_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0

    if verbose:
        print(f"  [Agent 1] Summary generated ({len(summary_text)} chars)")
        print(f"  [Agent 1] Tokens used -> Input: {prompt_tokens} | Output: {completion_tokens}")

    # Step 4: Return structured result
    return {
        "status":    "success",
        "summary":   summary_text,
        "raw_stats": profile,
        "file_name": profile["file_name"],
        "row_count": profile["total_rows"],
        "col_count": profile["total_cols"],
        "tokens":    {
            "input":  prompt_tokens,
            "output": completion_tokens
        }
    }


# Standalone test
if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "sample_data.csv"

    print("\n   Agent 1 - CSV Summarization\n")

    result = summarize_csv(csv_path, verbose=True)

    if result["status"] == "error":
        print(f"  Agent 1 failed: {result['error']}")
        sys.exit(1)

    print("\n--- Agent 1 Output ---")
    print(result["summary"])

    try:
        from validators import validate_summary
        print("\n--- Validation ---")
        vr = validate_summary(result["summary"])
        print(vr)
    except ImportError:
        pass