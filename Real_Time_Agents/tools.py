"""
Tool implementations for the Research Assistant.
Defines available functions and maps them in the TOOL_REGISTRY.
"""

import os
import json
import math
import datetime

USE_REAL_SEARCH = os.environ.get("USE_REAL_SEARCH", "false").lower() == "true"


def search_web(query: str, max_results: int = 4) -> str:
    if USE_REAL_SEARCH:
        return _real_search(query, max_results)
    else:
        return _mock_search(query)


def _mock_search(query: str) -> str:
    query_lower = query.lower()

    if "anthropic" in query_lower and ("job" in query_lower or "hire" in query_lower or "engineer" in query_lower):
        return """
[SEARCH RESULTS for: "{query}"]

Result 1 - Anthropic Careers Page
URL: careers.anthropic.com
Anthropic is hiring AI Safety Engineers, Research Engineers, and Full-Stack Engineers.
Requirements: Strong Python skills, experience with LLMs, familiarity with ML frameworks.
Compensation: $150,000-$300,000 base + equity. Remote-friendly.

Result 2 - LinkedIn: Anthropic AI Engineer Roles
URL: linkedin.com/jobs/anthropic
Most listed roles require: 3+ years Python, API design experience, understanding of
transformer architectures. Portfolio projects using LLM APIs are explicitly
mentioned as a plus in 70% of postings reviewed.

Result 3 - Glassdoor: Anthropic Interview Process
URL: glassdoor.com/anthropic-interviews
Interview format: 1 recruiter screen, 2 technical rounds (coding + system design),
1 values/mission alignment round. Coding rounds focus on Python.
Candidates who ship AI projects before applying report much higher callback rates.

Result 4 - Reddit r/MachineLearning: Getting hired at Anthropic
Top advice from upvoted comments: "Build real things with the API. Show GitHub.
The team cares about what you've actually shipped, not just theory."
""".format(query=query)

    elif "openai" in query_lower or "google" in query_lower or "meta ai" in query_lower:
        return f"""
[SEARCH RESULTS for: "{query}"]

Result 1 - Top AI Company Hiring Trends
URL: techcrunch.com/ai-hiring
All major AI labs (Anthropic, OpenAI, Google DeepMind, Meta AI) have increased
hiring of AI Application Engineers - engineers who build with AI APIs rather
than train models from scratch. This role grew significantly.

Result 2 - Levels.fyi: AI Engineer Compensation
URL: levels.fyi/ai-engineer
Median total compensation at top AI companies: $280,000-$400,000 (base + equity + bonus).
Remote roles: $150,000-$220,000 base. 

Result 3 - What skills do AI companies actually want?
URL: stackoverflow.blog/ai-engineer-skills
Survey of 500 AI engineers: Python (98%), REST APIs (89%), LLM APIs (87%),
Prompt Engineering (76%), Agentic Frameworks (61%), MCP/Tool Use (47%).
"""

    elif "mcp" in query_lower or "model context protocol" in query_lower:
        return f"""
[SEARCH RESULTS for: "{query}"]

Result 1 - Anthropic MCP Documentation
URL: docs.anthropic.com/mcp
Model Context Protocol (MCP) is an open standard for connecting AI models to
external tools and data sources. Released by Anthropic in late 2024.
Growing adoption: 500+ MCP servers published on GitHub as of 2025.

Result 2 - Why MCP matters for AI engineers
URL: anthropic.com/blog/mcp
MCP knowledge is becoming a differentiator in AI engineer interviews.
Companies building production AI apps cite MCP as the preferred integration layer.

Result 3 - Getting started with MCP in Python
URL: github.com/anthropics/mcp
The Python MCP SDK allows you to build custom MCP servers in ~50 lines of code.
Most useful starting tools: filesystem, fetch, and database connectors.
"""

    elif "salary" in query_lower or "compensation" in query_lower or "pay" in query_lower:
        return f"""
[SEARCH RESULTS for: "{query}"]

Result 1 - AI Engineer Salaries (levels.fyi)
URL: levels.fyi/salaries/ai-engineer
US-based AI Engineers:
  - Entry (0-2 yrs): $130k-$180k total comp
  - Mid (2-5 yrs): $200k-$320k total comp
  - Senior (5+ yrs): $350k-$500k+ total comp

Result 2 - Anthropic Compensation Philosophy
URL: anthropic.com/careers/compensation
Anthropic pays at the 90th percentile of market. 
They make strong offers upfront. Equity is a meaningful component.
"""

    else:
        return f"""
[SEARCH RESULTS for: "{query}"]

Result 1 - General result for "{query}"
URL: example.com/result1
Standard result information for the query provided.

Result 2 - More information about "{query}"
URL: example.com/result2
Additional context regarding the query topics.

Result 3 - "{query}" - Additional context
URL: example.com/result3
Further details on the specific topic requested.
"""


def _real_search(query: str, max_results: int = 4) -> str:
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"Title: {r.get('title', 'N/A')}\n"
                    f"URL:   {r.get('href', 'N/A')}\n"
                    f"Body:  {r.get('body', 'N/A')}\n"
                )

        if not results:
            return f"No results found for: {query}"

        header = f"[REAL SEARCH RESULTS for: '{query}'] ({len(results)} results)\n\n"
        return header + "\n---\n".join(results)

    except ImportError:
        return (
            "Error: duckduckgo-search not installed.\n"
            "Run: pip install duckduckgo-search\n"
            "Then re-run with: export USE_REAL_SEARCH=true"
        )
    except Exception as e:
        return f"Search error: {str(e)}\nFalling back to mock results.\n\n" + _mock_search(query)


def read_file(path: str) -> str:
    safe_path = os.path.normpath(path)
    if safe_path.startswith(".."):
        return f"Error: Cannot read files outside the current directory. Path: {path}"

    if not os.path.exists(safe_path):
        return f"Error: File not found: '{safe_path}'\nAvailable files: {', '.join(os.listdir('.'))}"

    if not os.path.isfile(safe_path):
        return f"Error: '{safe_path}' is a directory, not a file."

    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()

        char_count = len(content)
        if char_count > 50_000:
            content = content[:50_000]
            return (
                f"[FILE: {safe_path} | {char_count:,} chars - showing first 50,000]\n\n"
                + content
                + "\n\n[...file truncated - too large for single read]"
            )

        return f"[FILE: {safe_path} | {char_count:,} chars]\n\n{content}"

    except UnicodeDecodeError:
        return f"Error: '{safe_path}' is not a readable text file"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(path: str, content: str, mode: str = "write") -> str:
    safe_path = os.path.normpath(path)
    if safe_path.startswith(".."):
        return f"Error: Cannot write outside current directory."

    try:
        file_mode = "a" if mode == "append" else "w"
        with open(safe_path, file_mode, encoding="utf-8") as f:
            f.write(content)

        action = "Appended to" if mode == "append" else "Written to"
        size   = os.path.getsize(safe_path)
        return f"{action} '{safe_path}' successfully. File size: {size:,} bytes."

    except Exception as e:
        return f"Error writing file: {str(e)}"


def calculate(expression: str) -> str:
    try:
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})

        if any(bad in expression.lower() for bad in ["import", "exec", "eval", "open", "__"]):
            return "Error: Invalid expression - only math operations allowed."

        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Result: {expression} = {result}"

    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error evaluating '{expression}': {str(e)}"


def get_company_info(company_name: str) -> str:
    db = {
        "anthropic": {
            "name":      "Anthropic",
            "founded":   "2021",
            "hq":        "San Francisco, CA",
            "focus":     "AI safety, Constitutional AI, Claude models",
            "models":    "Claude 3.5 Sonnet, Claude 3 Opus, Claude Haiku",
            "careers":   "careers.anthropic.com",
            "size":      "~800 employees (2025)",
            "interview": "Python coding, system design, mission alignment",
            "key_skills":"Python, LLM APIs, safety research, agentic systems",
        },
        "openai": {
            "name":      "OpenAI",
            "founded":   "2015",
            "hq":        "San Francisco, CA",
            "focus":     "AGI research, GPT models, safety",
            "models":    "GPT-4o, o1, Sora, DALL-E",
            "careers":   "openai.com/careers",
            "size":      "~3,000 employees (2025)",
            "interview": "Technical depth, coding, ML fundamentals",
            "key_skills":"Python, ML/DL, distributed systems, product sense",
        },
        "google deepmind": {
            "name":      "Google DeepMind",
            "founded":   "2010 (DeepMind), merged 2023",
            "hq":        "London, UK + Mountain View, CA",
            "focus":     "Gemini models, AlphaFold, robotics, AGI",
            "models":    "Gemini Ultra/Pro/Nano, Imagen",
            "careers":   "deepmind.google/about/jobs",
            "size":      "~3,500 employees (2025)",
            "interview": "Research-heavy, publications valued",
            "key_skills":"Python, JAX, ML research, publications preferred",
        },
        "meta ai": {
            "name":      "Meta AI",
            "founded":   "2013",
            "hq":        "Menlo Park, CA",
            "focus":     "Open-source AI, LLaMA models, AI infrastructure",
            "models":    "LLaMA 3, Llama Guard, Code Llama",
            "careers":   "metacareers.com",
            "size":      "~70,000 total (AI team: ~2,000)",
            "interview": "Facebook-style: coding + system design + behavioral",
            "key_skills":"Python, PyTorch, distributed training, open-source",
        },
    }

    key = company_name.lower().strip()
    info = db.get(key)

    if not info:
        for db_key in db:
            if key in db_key or db_key in key:
                info = db[db_key]
                break

    if not info:
        available = ", ".join(db.keys())
        return f"Company '{company_name}' not in database. Available: {available}"

    lines = [f"=== {info['name']} ==="]
    for field, value in info.items():
        if field != "name":
            lines.append(f"{field.upper():12}: {value}")
    return "\n".join(lines)


TOOL_REGISTRY = {
    "search_web":       search_web,
    "read_file":        read_file,
    "write_file":       write_file,
    "calculate":        calculate,
    "get_company_info": get_company_info,
}


def execute_tool(name: str, args: dict) -> str:
    func = TOOL_REGISTRY.get(name)
    if not func:
        return f"Error: Unknown tool: '{name}'. Available: {', '.join(TOOL_REGISTRY.keys())}"
    try:
        result = func(**args)
        return str(result)
    except TypeError as e:
        return f"Error: Tool '{name}' called with wrong arguments: {e}"
    except Exception as e:
        return f"Error: Tool '{name}' raised an error: {e}"


if __name__ == "__main__":
    print("Testing tools")
    print(search_web("Anthropic job requirements")[:200])
    print(read_file("tools.py")[:100])
    print(write_file("test_output.txt", "Hello from tools.py!"))
    print(calculate("150000 * 1.15"))
    print(get_company_info("anthropic"))