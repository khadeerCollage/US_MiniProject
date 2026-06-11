# Multi-Agent Data Pipeline with LangGraph

This directory contains an advanced multi-agent pipeline using LangGraph orchestration, asynchronous I/O, and self-reflection loops.

## Quick Start

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Run the full pipeline (uses sample_data.csv)
python multi-agents/orchestrator.py

# With your own CSV
python multi-agents/orchestrator.py mydata.csv

# Run the orchestration quality benchmark
python multi-agents/benchmark.py
```

## File Overview

* `sample_data.csv`: Test data (30 AI job market records).
* `agent1_summarize.py`: Takes the CSV and generates a statistical summary.
* `agent2_insights.py`: Takes the summary and generates actionable insights.
* `agent3_report.py`: Combines the summary and insights into a Markdown report.
* `validators.py`: Legacy validators for the older sequential pipeline.
* `orchestrator.py`: The upgraded orchestrator leveraging a LangGraph state machine. It handles async execution, conditional routing based on quality scores, and retries.
* `benchmark.py`: A testing script validating that proper orchestration on free tier models reaches paid tier quality.

## How It Works

### 1. LangGraph State Machine
The orchestration uses a state machine defined in `orchestrator.py`. Instead of a simple sequential script, LangGraph defines nodes and conditional edges:

* `load_csv`: Loads data into the pipeline state.
* `summarize`: Agent 1 processes data with an async reflection loop.
* `insights`: Agent 2 processes the summary with an async reflection loop.
* `report`: Agent 3 writes the final report.

Conditional edges route execution back to the same node for a retry if the quality score is too low, ensuring high quality before advancing.

### 2. Async Execution
The pipeline relies on `model_manager.py` (in the root directory) to dispatch requests to the LLM. It uses `AsyncGroqProvider` and `AsyncGeminiProvider` to prevent the event loop from blocking, enabling massive speedups when multiple agents run in parallel (as seen in `benchmark.py`).

### 3. Self-Reflection
Every node uses `ReflectionEngine` (in the root directory). Instead of accepting the first output, the agent critiques its own work and improves it. This reliably boosts free model quality to match more expensive models.
