# Multi-Agent Data Pipeline

A simple 3-agent pipeline with orchestration, retries, and output validation.

## Quick Start

```bash
# Activate virtual environment
source venv/bin/activate
# Install dependencies
pip install pandas groq

# Run the full pipeline (uses sample_data.csv)
python orchestrator.py

# With your own CSV
python orchestrator.py mydata.csv

# Print the report in terminal too
python orchestrator.py --show-report
```

## File Map

| File | What it does |
|------|-------------|
| `sample_data.csv` | Test data (30 AI job market records) |
| `validators.py` | Validates the output of each agent before passing it forward |
| `agent1_summarize.py` | Takes the CSV and generates a statistical summary |
| `agent2_insights.py` | Takes the summary and generates actionable insights |
| `agent3_report.py` | Combines the summary and insights into a Markdown report |
| `orchestrator.py` | Runs the pipeline, handles retries, and saves the output |

## How it Works

### 1. Orchestrator -> Subagent
```text
orchestrator.py
    |
    +-> agent1_summarize.summarize_csv()
    |
    +-> agent2_insights.generate_insights(agent1_result)
    |
    +-> agent3_report.write_report(agent1_result, agent2_result)
    |
    +-> report_TIMESTAMP.md
```
Each agent handles one specific task. The orchestrator manages the flow between them so they don't have to worry about each other.

### 2. Retries and Backoff
If something goes wrong (like a rate limit or a bad LLM response), the orchestrator will try again and wait a bit longer each time:
```text
attempt 1 -> fails -> wait 2s
attempt 2 -> fails -> wait 4s
attempt 3 -> fails -> wait 8s -> stop the pipeline
```
You can change these in `orchestrator.py` (`MAX_RETRIES` and `RETRY_BASE_SECS`).

### 3. Validation
Before passing data to the next step, we check the output to make sure the LLM didn't just return garbage.
```python
result = run_agent(...)
validation = validate_output(result)

if validation.passed:
    # move on to the next agent
else:
    # retry this agent
```
The validators just make sure the output has the right structure, minimum length, and actually contains data instead of an error message.

## Testing Standalone Agents

If you want to run the agents by themselves without the orchestrator:

```bash
# Test just Agent 1
python agent1_summarize.py sample_data.csv

# Test Agent 1 + 2
python agent2_insights.py

# Test all 3 agents
python agent3_report.py

# Test the validators
python validators.py
```

## Passing Data Between Agents

Instead of just passing plain text around, we pass dictionaries containing the full context. 

```python
result1 = agent1(csv_path)         # returns a dict with summary + raw_stats + tokens
result2 = agent2(result1)          # receives EVERYTHING — summary AND raw numbers
```

This way, downstream agents get everything they need. For example, Agent 2 can look at the exact raw numbers from Agent 1, not just the text summary.
