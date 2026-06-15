# =============================================================================
# langgraph_pipeline.py  —  LangGraph Orchestrated Multi-Agent Pipeline
# =============================================================================
#
# THIS IS THE CORE UPGRADE — LangGraph replaces the simple sequential pipeline
# from Topic 4 with a proper STATE MACHINE that can:
#
#    Retry individual nodes (not the whole pipeline)
#    Branch based on quality scores
#    Run reflection loops per node
#    Track full state across all nodes
#    Handle errors gracefully with fallback paths
#    Work with ANY model (free Groq/Gemini or paid Anthropic)
#
# LANGGRAPH VS TOPIC 4 ORCHESTRATOR:
#
#   Topic 4 (simple sequential):
#     summarize() → validate → insights() → validate → report()
#     Problem: If insights() fails, you lose the summary too.
#
#   LangGraph (state machine):
#     ┌-----------------------------------------------------┐
#     │  START                                              │
#     │    ↓                                                │
#     │  [load_csv]  → loads data into state               │
#     │    ↓                                                │
#     │  [summarize] → Agent 1 with reflection             │
#     │    ↓                                                │
#     │  [check_summary] --→ score < 6 --→ [summarize]    │
#     │    ↓ (score ≥ 6)          (max 3 retries)          │
#     │  [insights]  → Agent 2 with reflection             │
#     │    ↓                                                │
#     │  [check_insights] --→ score < 6 --→ [insights]    │
#     │    ↓ (score ≥ 6)                                   │
#     │  [report]    → Agent 3 with reflection             │
#     │    ↓                                                │
#     │  [save_report]                                      │
#     │    ↓                                                │
#     │  END                                                │
#     └-----------------------------------------------------┘
#
# INSTALL:
#   pip install langgraph langchain-core groq google-generativeai pandas
#
# HOW TO RUN:
#   python langgraph_pipeline.py                        # uses sample_data.csv
#   python langgraph_pipeline.py mydata.csv             # custom CSV
#   python langgraph_pipeline.py --benchmark            # compare free vs Anthropic
# =============================================================================

import os
import sys
import re
import json
import time
import asyncio
import datetime
import pandas as pd
from typing import TypedDict, Optional, Annotated

try:
    from langgraph.graph import StateGraph, END, START
except ImportError:
    print("Run: pip install langgraph")
    sys.exit(1)

# Add parent directory to path so we can import from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from model_manager    import ModelManager, TaskComplexity
from reflection_engine import ReflectionEngine

# -----------------------------------------------------------------------------
# STATE DEFINITION
# LangGraph requires a TypedDict that defines ALL pipeline state.
# Every node reads from this dict and returns updates to it.
# -----------------------------------------------------------------------------

class PipelineState(TypedDict):
    # Input
    csv_path:        str
    # Raw data
    csv_stats:       str
    csv_shape:       str
    csv_columns:     str
    # Agent outputs
    summary:         str
    insights:        str
    report:          str
    # Quality tracking
    summary_score:   int
    insights_score:  int
    report_score:    int
    # Retry tracking
    summary_retries: int
    insights_retries: int
    report_retries:  int
    # Metadata
    models_used:     list
    total_tokens:    int
    errors:          list
    output_file:     str


# -----------------------------------------------------------------------------
# NODE IMPLEMENTATIONS
# Each node is a function that takes the full state and returns partial updates.
# -----------------------------------------------------------------------------

# Initialize model manager + reflection engine once
_mgr    = ModelManager(prefer_free=True)
_engine = ReflectionEngine(_mgr, max_reflections=2)


# NOTE: This is a synchronous node because it performs purely local, blocking I/O (reading a CSV).
# LangGraph natively handles this by wrapping sync nodes in asyncio.to_thread() internally,
# allowing it to seamlessly mix with our async agent nodes without blocking the event loop.
def node_load_csv(state: PipelineState) -> dict:
    """Load and profile the CSV file. Pure Python — no model calls."""
    print("\n    [Node: load_csv] Loading and profiling CSV...")
    path = state["csv_path"]

    if not os.path.exists(path):
        return {"errors": state.get("errors", []) + [f"CSV not found: {path}"]}

    df       = pd.read_csv(path)
    shape    = f"{len(df)} rows × {len(df.columns)} columns"
    columns  = ", ".join(df.columns)
    num_cols = df.select_dtypes(include=["number"]).columns
    stats    = df[num_cols].describe().round(2).to_string() if len(num_cols) > 0 else "No numeric columns"

    print(f"      Loaded: {shape}")
    print(f"      Columns: {columns}")

    return {
        "csv_stats":   stats,
        "csv_shape":   shape,
        "csv_columns": columns,
        "errors":      state.get("errors", [])
    }


async def node_summarize(state: PipelineState) -> dict:
    """Agent 1: CSV data -> natural language summary (async, with reflection)."""
    retries = state.get("summary_retries", 0)
    print(f"\n    [Node: summarize] Agent 1 (attempt {retries+1}/3) [async]...")

    system = """
<role>You are an expert data analyst. Summarize CSV statistics into clear, factual English.</role>
<rules>
- Every claim must reference specific numbers from the data.
- Structure: Dataset Overview -> Key Statistics -> Notable Patterns -> Data Quality.
- Use plain English. Include ranges, averages, distributions.
</rules>
"""
    user = f"""
Summarize this dataset.

SHAPE: {state['csv_shape']}
COLUMNS: {state['csv_columns']}

STATISTICS:
{state['csv_stats']}

Produce a comprehensive natural language summary covering all important patterns.
"""

    output, score, reflections = await _engine.generate_with_reflection_async(
        system=system, user=user,
        task_description="CSV statistical summary with numbers and patterns",
        complexity=TaskComplexity.MEDIUM,
        max_tokens=1200,
        task_label="Agent1-Summary",
        verbose=True
    )

    models = state.get("models_used", [])
    tokens = state.get("total_tokens", 0) + sum(
        e.get("in_tok", 0) + e.get("out_tok", 0)
        for e in _mgr.call_log[-3:]
    )

    return {
        "summary":         output,
        "summary_score":   score,
        "summary_retries": retries + 1,
        "models_used":     models,
        "total_tokens":    tokens
    }


def node_check_summary(state: PipelineState) -> str:
    """
    Conditional edge function: decides where to go after summarize node.
    Returns a string key that LangGraph uses to pick the next node.
    """
    score   = state.get("summary_score", 0)
    retries = state.get("summary_retries", 0)

    print(f"\n    [Check: summary] Score: {score}/10 | Retries: {retries}/3")

    if score >= 6:
        print("      -> Proceeding to insights ")
        return "to_insights"
    elif retries < 3:
        print(f"      -> Score too low ({score}/10). Retrying summarize...")
        return "retry_summary"
    else:
        print("      -> Max retries reached. Proceeding with best available summary.")
        return "to_insights"    # Proceed anyway after 3 tries


async def node_insights(state: PipelineState) -> dict:
    """Agent 2: Summary -> Strategic insights (async, with reflection)."""
    retries = state.get("insights_retries", 0)
    print(f"\n    [Node: insights] Agent 2 (attempt {retries+1}/3) [async]...")

    system = """
<role>You are a senior business analyst. Extract strategic, actionable insights from data summaries.</role>
<rules>
- Each insight MUST cite a specific number from the summary.
- Format: numbered list, 4-6 insights.
- Each insight: Bold CATEGORY -> Finding -> Actionable implication.
- Focus on what a job seeker targeting US AI companies needs to know.
</rules>
<thinking_instructions>
Before generating insights, reason inside <thinking> tags:
1. What is the most surprising pattern in this data?
2. What correlations exist between variables?
3. What specific action does each insight suggest?
</thinking_instructions>
"""
    user = f"""
Generate 4-6 strategic insights from this dataset summary.

DATASET: {state['csv_path']} ({state['csv_shape']})

SUMMARY:
{state['summary']}

Generate insights that are specific, data-backed, and immediately actionable.
"""

    output, score, reflections = await _engine.generate_with_reflection_async(
        system=system, user=user,
        task_description="Strategic actionable insights backed by specific data points",
        complexity=TaskComplexity.COMPLEX,
        max_tokens=1200,
        task_label="Agent2-Insights",
        verbose=True
    )

    tokens = state.get("total_tokens", 0) + sum(
        e.get("in_tok", 0) + e.get("out_tok", 0)
        for e in _mgr.call_log[-3:]
    )

    return {
        "insights":         output,
        "insights_score":   score,
        "insights_retries": retries + 1,
        "total_tokens":     tokens
    }


def node_check_insights(state: PipelineState) -> str:
    """Conditional edge after insights node."""
    score   = state.get("insights_score", 0)
    retries = state.get("insights_retries", 0)

    print(f"\n    [Check: insights] Score: {score}/10 | Retries: {retries}/3")

    if score >= 6:
        print("      -> Proceeding to report ")
        return "to_report"
    elif retries < 3:
        print(f"      -> Score too low. Retrying insights...")
        return "retry_insights"
    else:
        print("      -> Max retries reached. Proceeding with best available insights.")
        return "to_report"


async def node_report(state: PipelineState) -> dict:
    """Agent 3: Summary + Insights -> Full Markdown report (async, with reflection)."""
    retries = state.get("report_retries", 0)
    print(f"\n    [Node: report] Agent 3 (attempt {retries+1}/3) [async]...")

    system = """
<role>You are a professional technical writer. Create executive-quality Markdown reports.</role>
<output_format>
Produce a complete Markdown report with EXACTLY these sections:
# [Descriptive Title]
## Executive Summary  (3-4 sentences, 2+ specific numbers)
## Dataset Overview   (file info, what it covers)
## Key Statistical Findings  (include at least 1 Markdown table)
## Strategic Insights  (numbered, 4-6 items, bold category labels)
## Recommendations for AI Job Seekers  (3-5 specific action items)
## Conclusion  (2-3 sentences)
---
*Report generated by LangGraph AI Pipeline*
</output_format>
<rules>
- Use proper Markdown syntax throughout.
- Include at least one comparison table.
- Reference specific numbers and company names from the data.
- Professional tone — suitable for LinkedIn or GitHub portfolio.
</rules>
"""
    user = f"""
Write a professional Markdown report combining the summary and insights below.

DATASET: {state['csv_path']} | {state['csv_shape']}

AGENT 1 — SUMMARY:
{state['summary']}

AGENT 2 — INSIGHTS:
{state['insights']}

Create a polished, publishable report that an AI job seeker can share on GitHub.
"""

    output, score, reflections = await _engine.generate_with_reflection_async(
        system=system, user=user,
        task_description="Professional Markdown report with tables, sections, specific data references",
        complexity=TaskComplexity.COMPLEX,
        max_tokens=2500,
        task_label="Agent3-Report",
        verbose=True
    )

    tokens = state.get("total_tokens", 0) + sum(
        e.get("in_tok", 0) + e.get("out_tok", 0)
        for e in _mgr.call_log[-5:]
    )

    return {
        "report":         output,
        "report_score":   score,
        "report_retries": retries + 1,
        "total_tokens":   tokens
    }


def node_check_report(state: PipelineState) -> str:
    """Conditional edge after report node."""
    score   = state.get("report_score", 0)
    retries = state.get("report_retries", 0)

    print(f"\n    [Check: report] Score: {score}/10 | Retries: {retries}/3")

    if score >= 6 or retries >= 3:
        return "to_save"
    return "retry_report"


def node_save_report(state: PipelineState) -> dict:
    """Save the final report to a Markdown file."""
    print("\n    [Node: save_report] Saving report...")

    timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base       = os.path.splitext(os.path.basename(state["csv_path"]))[0]
    output_path = f"report_langgraph_{base}_{timestamp}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(state["report"])

    print(f"      Saved to: {output_path}")
    return {"output_file": output_path}


# -----------------------------------------------------------------------------
# BUILD THE LANGGRAPH GRAPH
# -----------------------------------------------------------------------------

def build_pipeline() -> StateGraph:
    """Assemble the LangGraph state machine."""

    workflow = StateGraph(PipelineState)

    # -- Add all nodes -----------------------------------------------------
    workflow.add_node("load_csv",     node_load_csv)
    workflow.add_node("summarize",    node_summarize)
    workflow.add_node("insights",     node_insights)
    workflow.add_node("report",       node_report)
    workflow.add_node("save_report",  node_save_report)

    # -- Set entry point ---------------------------------------------------
    workflow.set_entry_point("load_csv")

    # -- Unconditional edges -----------------------------------------------
    workflow.add_edge("load_csv",    "summarize")
    workflow.add_edge("save_report", END)

    # -- Conditional edges (quality-based routing) -------------------------
    workflow.add_conditional_edges(
        "summarize",
        node_check_summary,
        {
            "to_insights":    "insights",
            "retry_summary":  "summarize",     # Loop back for retry
        }
    )

    workflow.add_conditional_edges(
        "insights",
        node_check_insights,
        {
            "to_report":      "report",
            "retry_insights": "insights",
        }
    )

    workflow.add_conditional_edges(
        "report",
        node_check_report,
        {
            "to_save":    "save_report",
            "retry_report": "report",
        }
    )

    return workflow.compile()


# -----------------------------------------------------------------------------
# MAIN RUNNER  (async)
# -----------------------------------------------------------------------------

async def run_pipeline(csv_path: str):
    """
    Async pipeline runner. Uses app.ainvoke() so LangGraph executes
    async nodes with 'await' instead of blocking the event loop.
    """

    print("\n" + "=" * 65)
    print("     LangGraph Multi-Agent Pipeline  -  Async Upgraded Orchestration")
    print("=" * 65)

    available = _mgr.get_available_providers()
    print(f"   Models available:  {available}")
    print(f"   Prefer free models: {_mgr.prefer_free}")
    print(f"   Reflection loops:   up to {_engine.max_reflections} per agent")
    print(f"   Execution mode:     ASYNC (await app.ainvoke)")
    print("=" * 65)

    if not available:
        print("\n    No model providers configured. Set API keys:\n")
        print("  GROQ_API_KEY     - free at console.groq.com")
        print("  GEMINI_API_KEY   - free at aistudio.google.com\n")
        sys.exit(1)

    app = build_pipeline()

    initial_state: PipelineState = {
        "csv_path":         csv_path,
        "csv_stats":        "",
        "csv_shape":        "",
        "csv_columns":      "",
        "summary":          "",
        "insights":         "",
        "report":           "",
        "summary_score":    0,
        "insights_score":   0,
        "report_score":     0,
        "summary_retries":  0,
        "insights_retries": 0,
        "report_retries":   0,
        "models_used":      [],
        "total_tokens":     0,
        "errors":           [],
        "output_file":      ""
    }

    start_time = time.time()
    print("\n    Starting LangGraph async execution...\n")

    # ainvoke() runs async nodes with 'await', sync nodes via asyncio.to_thread()
    final_state = await app.ainvoke(initial_state)
    elapsed     = round(time.time() - start_time, 1)

    print("\n\n" + "=" * 65)
    print("    PIPELINE COMPLETE")
    print("=" * 65)
    print(f"  Summary quality:  {final_state.get('summary_score', '?')}/10")
    print(f"  Insights quality: {final_state.get('insights_score', '?')}/10")
    print(f"  Report quality:   {final_state.get('report_score', '?')}/10")

    avg_score = (
        final_state.get("summary_score", 0) +
        final_state.get("insights_score", 0) +
        final_state.get("report_score", 0)
    ) / 3

    print(f"  Average quality:  {avg_score:.1f}/10")
    print(f"  Total time:       {elapsed}s")
    print(f"\n  Output: {final_state.get('output_file', 'not saved')}")
    print("\n    Model Usage:")
    _mgr.print_usage_report()
    print("=" * 65)

    return final_state


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    csv_path = "sample_data.csv"

    # Check for custom CSV path
    for arg in sys.argv[1:]:
        if not arg.startswith("--") and arg.endswith(".csv"):
            csv_path = arg
            break

    if not os.path.exists(csv_path):
        print(f"\n    CSV not found: '{csv_path}'")
        print("  Pass your own CSV: python langgraph_pipeline.py mydata.csv\n")
        sys.exit(1)

    # Use asyncio.run() to enter the async event loop
    asyncio.run(run_pipeline(csv_path))
