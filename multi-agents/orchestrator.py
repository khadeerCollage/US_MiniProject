"""
orchestrator.py - The Main Orchestrator

This module implements the orchestrator pattern, controlling the execution flow 
of three separate agents:
1. Agent 1 (CSV -> Summary)
2. Agent 2 (Summary -> Insights)
3. Agent 3 (Summary + Insights -> Report)

It features production-level patterns including:
- Retry on failure (with exponential backoff)
- Inter-step validation (validating the output of each agent before continuing)
- Pipeline tracking (tracking execution time and token usage)

How to run:
    python orchestrator.py                          # uses sample_data.csv
    python orchestrator.py mydata.csv               # use your own CSV
    python orchestrator.py mydata.csv --no-save     # don't write report file
    python orchestrator.py mydata.csv --show-report # print report to terminal
"""

import os
import sys
import time
import json
import datetime

# Add the parent directory to sys.path so we can import from utils.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    import groq
except ImportError:
    groq = None

from agent1_summarize import summarize_csv
from agent2_insights  import generate_insights
from agent3_report    import write_report

try:
    from validators import validate_summary, validate_insights, validate_report
except ImportError:
    # Dummy validators if the module is missing
    class DummyValidationResult:
        passed = True
        score = 100
        warnings = []
        errors = []
        def __str__(self): return "PASSED (dummy validator)"
    
    def validate_summary(x): return DummyValidationResult()
    def validate_insights(x): return DummyValidationResult()
    def validate_report(x): return DummyValidationResult()

# Pipeline Configuration
MAX_RETRIES     = 3        # How many times to retry a failing step
RETRY_BASE_SECS = 2        # Base delay for exponential backoff (2->4->8 seconds)
MIN_VALID_SCORE = 50       # Minimum validation score to proceed (0-100)


def run_with_retry(agent_name: str, agent_func, validator_func, *args, **kwargs) -> dict:
    """
    Run an agent function with retry logic and output validation.

    Args:
        agent_name:     Human-readable name for logging ("Agent 1")
        agent_func:     The agent function to call (e.g., summarize_csv)
        validator_func: The validation function for this step
        *args, **kwargs: Arguments passed directly to agent_func

    Returns:
        The agent's result dict (with status="success")
        Raises RuntimeError if all retries fail.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            # Exponential backoff: 2s, 4s, 8s
            delay = RETRY_BASE_SECS * (2 ** (attempt - 2))
            print(f"[{agent_name}] Retrying in {delay}s... (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(delay)

        print(f"\n[{agent_name}] Running (attempt {attempt}/{MAX_RETRIES})...")

        try:
            # Run the agent
            result = agent_func(*args, verbose=True, **kwargs)

            # Check if agent returned an error
            if result.get("status") == "error":
                last_error = result.get("error", "Unknown error")
                print(f"[{agent_name}] Returned error: {last_error}")
                continue   # Retry

            # Validate the output
            # Get the key field to validate (differs per agent)
            content_to_validate = (
                result.get("summary")  or
                result.get("insights") or
                result.get("report")   or ""
            )

            validation = validator_func(content_to_validate)
            print(f"[{agent_name}] Validation result:")
            print(f"    {validation}")

            if validation.passed and validation.score >= MIN_VALID_SCORE:
                print(f"[{agent_name}] PASSED (score: {validation.score}/100)")
                return result

            elif not validation.passed:
                last_error = f"Validation failed (score: {validation.score}): " + \
                             "; ".join(validation.errors)
                print(f"[{agent_name}] Validation FAILED. Will retry.")
                continue   # Retry

            else:
                # Passed but with warnings - proceed anyway
                if validation.warnings:
                    print(f"[{agent_name}] Passed with warnings - proceeding.")
                return result

        except Exception as e:
            # If it's a groq API error, we can check for rate limits
            if groq and isinstance(e, groq.APIError):
                last_error = f"Groq API error: {e}"
                print(f"[{agent_name}] API error: {e}")
                if "rate_limit" in str(e).lower():
                    time.sleep(30)   # Rate limit - wait longer
                continue
            
            last_error = f"Unexpected error: {e}"
            print(f"[{agent_name}] Unexpected error: {e}")
            continue

    # All retries exhausted
    raise RuntimeError(
        f"[{agent_name}] Failed after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


class PipelineTracker:
    def __init__(self, csv_path: str):
        self.csv_path  = csv_path
        self.start_time = time.time()
        self.steps     = []
        self.total_tokens = {"input": 0, "output": 0}

    def record_step(self, name: str, result: dict, elapsed: float):
        tokens = result.get("tokens", {"input": 0, "output": 0})
        self.total_tokens["input"]  += tokens.get("input", 0)
        self.total_tokens["output"] += tokens.get("output", 0)
        self.steps.append({
            "name":          name,
            "elapsed_sec":   round(elapsed, 1),
            "input_tokens":  tokens.get("input", 0),
            "output_tokens": tokens.get("output", 0),
            "status":        result.get("status", "?")
        })

    def print_summary(self):
        total_elapsed = round(time.time() - self.start_time, 1)
        total_tokens  = self.total_tokens["input"] + self.total_tokens["output"]

        print("\nPIPELINE SUMMARY")
        print(f"{'Step':<20}  {'Time':>6}  {'In tok':>8}  {'Out tok':>8}")
        for s in self.steps:
            print(f"{s['name']:<20}  {s['elapsed_sec']:>5.1f}s  "
                  f"{s['input_tokens']:>7}t  {s['output_tokens']:>7}t")
        print(f"{'TOTAL':<20}  {total_elapsed:>5.1f}s  "
              f"{self.total_tokens['input']:>7}t  {self.total_tokens['output']:>7}t")
        print(f"\nTotal API calls: {len(self.steps)}")
        print(f"Total tokens:    {total_tokens:,}")


def run_pipeline(csv_path: str, save_report: bool = True, show_report: bool = False):
    """
    Run the full 3-agent pipeline with orchestration, retry, and validation.

    Args:
        csv_path:    Path to the CSV file
        save_report: Write final report to report_TIMESTAMP.md
        show_report: Print report to terminal after saving
    """
    tracker = PipelineTracker(csv_path)

    print("\nMulti-Agent Pipeline")
    print(f"CSV:    {csv_path}")
    print(f"Agents: CSV Summarizer -> Insight Generator -> Report Writer")
    print(f"Retry:  up to {MAX_RETRIES}x per step | Backoff: exponential")

    # STEP 1: Agent 1 — CSV Summarization
    print("\nSTEP 1 of 3 - CSV Summarization")
    t0 = time.time()
    try:
        agent1_result = run_with_retry(
            "Agent 1 (Summarizer)",
            summarize_csv,
            validate_summary,
            csv_path            # positional arg -> summarize_csv(csv_path)
        )
    except RuntimeError as e:
        print(f"\nPIPELINE FAILED at Step 1:\n{e}\n")
        sys.exit(1)

    tracker.record_step("Agent 1: Summarize", agent1_result, time.time() - t0)

    # STEP 2: Agent 2 — Insight Generation
    print("\nSTEP 2 of 3 - Insight Generation")
    t0 = time.time()
    try:
        agent2_result = run_with_retry(
            "Agent 2 (Insights)",
            generate_insights,
            validate_insights,
            agent1_result       # positional arg -> generate_insights(agent1_result)
        )
    except RuntimeError as e:
        print(f"\nPIPELINE FAILED at Step 2:\n{e}\n")
        sys.exit(1)

    tracker.record_step("Agent 2: Insights", agent2_result, time.time() - t0)

    # STEP 3: Agent 3 — Report Writing
    print("\nSTEP 3 of 3 - Report Writing")
    t0 = time.time()
    try:
        agent3_result = run_with_retry(
            "Agent 3 (Report)",
            write_report,
            validate_report,
            agent1_result,      # positional args
            agent2_result
        )
    except RuntimeError as e:
        print(f"\nPIPELINE FAILED at Step 3:\n{e}\n")
        sys.exit(1)

    tracker.record_step("Agent 3: Report", agent3_result, time.time() - t0)

    # PIPELINE COMPLETE
    print("\nALL 3 AGENTS COMPLETED SUCCESSFULLY!\n")
    tracker.print_summary()

    # Save the report to a Markdown file
    report_text = agent3_result["report"]

    if save_report:
        timestamp   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name   = os.path.splitext(os.path.basename(csv_path))[0]
        output_path = f"report_{base_name}_{timestamp}.md"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)

        print(f"\nReport saved to: '{output_path}'")
        print(f"Words: {agent3_result.get('word_count', '?')} | "
              f"Sections: {agent3_result.get('heading_count', '?')}")

    if show_report:
        print("\nFINAL REPORT:\n")
        print(report_text)

    return agent3_result


if __name__ == "__main__":
    # Parse args
    args        = sys.argv[1:]
    csv_path    = "sample_data.csv"
    save_report = True
    show_report = False

    for arg in args:
        if arg == "--no-save":
            save_report = False
        elif arg == "--show-report":
            show_report = True
        elif not arg.startswith("--"):
            csv_path = arg

    if not os.path.exists(csv_path):
        print(f"\nCSV not found: '{csv_path}'")
        print("Usage: python orchestrator.py [csv_file] [--show-report] [--no-save]\n")
        sys.exit(1)

    run_pipeline(csv_path, save_report=save_report, show_report=show_report)