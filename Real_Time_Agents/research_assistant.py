"""
Agentic Research Assistant using Groq and Llama 3.
Demonstrates the full tool use loop.
"""

import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import real_search
from utils import get_groq_client
from real_search import execute_tool

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 4096
client = get_groq_client()

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web for current information. Use this when the user asks about "
                "anything that requires looking up information: job requirements, company details, "
                "industry trends, salaries, technical concepts, or any factual question. "
                "Always search before giving advice on topics you're uncertain about."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific. Example: 'Anthropic AI engineer Python requirements 2025'"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return. Default 4. Max 8."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a local text file. Use this when the user mentions "
                "a file they want analyzed, summarized, or referenced. Also use it to check "
                "if a file already exists before writing to it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path. Example: 'notes.txt', 'resume.md', 'data.csv'"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write or append content to a local file. Use this to save research results, "
                "create reports, export summaries, or create any output file. "
                "Use mode='write' to create/overwrite, mode='append' to add to existing file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to write to. Example: 'research.txt', 'report.md'"
                    },
                    "content": {
                        "type": "string",
                        "description": "The full content to write to the file."
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["write", "append"],
                        "description": "write = overwrite/create new. append = add to end of existing file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Evaluate a mathematical expression and return the result. "
                "Use for salary calculations, token estimations, percentages, "
                "or any numerical computation. Example: '150000 * 1.15' or 'sqrt(144)'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A Python-compatible math expression. Use standard operators: +,-,*,/,**. Also: sqrt, log, ceil, floor."
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_info",
            "description": (
                "Get structured information about a top AI company: hiring requirements, "
                "interview process, key skills, compensation range, and more. "
                "Available companies: Anthropic, OpenAI, Google DeepMind, Meta AI."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Name of the company. Example: 'Anthropic', 'OpenAI', 'Google DeepMind', 'Meta AI'"
                    }
                },
                "required": ["company_name"]
            }
        }
    }
]

SYSTEM_PROMPT = """
You are an expert AI Career Research Assistant helping a software engineer in India
prepare to land a remote AI engineering role at a top US company (Anthropic, OpenAI,
Google DeepMind, or Meta AI) within 6 months.

You have 5 powerful tools available. Use them proactively.

Guidelines:
- ALWAYS search before giving advice on job requirements, salaries, or company specifics.
- If the user asks you to save/export/create a file, ALWAYS use write_file.
- If the user mentions an existing file, use read_file to check its contents first.
- Use calculate for any numerical questions (salary, token counts, percentages).
- Use get_company_info for quick, structured company lookups.
- You may call MULTIPLE tools in sequence when a task requires it.

Communication Style:
- Be direct and actionable. Lead with the most important insight.
- After using tools, synthesize the results - don't just dump raw data.
- Always end with a concrete next step the user can take TODAY.

IMPORTANT: If you call a tool, you must format the function call strictly as:
<function=tool_name>{"arg": "value"}</function>.
Ensure there is a closing angle bracket '>' after the function name.
"""

def run_agent(user_message: str, messages: list, show_tool_calls: bool = True) -> str:
    messages.append({"role": "user", "content": user_message})

    tool_call_count = 0
    max_tool_calls = 10

    while tool_call_count < max_tool_calls:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0,
            tools=TOOL_DEFINITIONS,
            messages=messages
        )

        response_message = response.choices[0].message
        messages.append(response_message)

        if response.choices[0].finish_reason == "tool_calls" and response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                tool_call_count += 1
                tool_name = tool_call.function.name
                
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except Exception:
                    tool_args = {}

                if show_tool_calls:
                    print(f"\n[Calling tool: {tool_name}]")
                    print(f"Arguments: {json.dumps(tool_args, indent=2)}")

                result = execute_tool(tool_name, tool_args)

                if show_tool_calls:
                    preview = result[:150].replace("\n", " ")
                    print(f"Result preview: {preview}...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": result
                })
        else:
            return response_message.content or "(No text response)"

    return "(Max tool calls reached - please refine your request)"

def configure_search():
    print("\nSelect Search Engine Mode:")
    print("1. Mock Search (Local Data)")
    print("2. DuckDuckGo (Real Web - Free)")
    print("3. Tavily (Real Web - Default, requires API key)")
    print("4. SerpAPI (Real Web - requires API key)")
    
    choice = input("\nEnter choice (1-4) [default: 3]: ").strip()
    
    if choice == "1":
        real_search.USE_REAL_SEARCH = False
    elif choice == "2":
        real_search.USE_REAL_SEARCH = True
        real_search.SEARCH_ENGINE = "duckduckgo"
    elif choice == "4":
        real_search.USE_REAL_SEARCH = True
        real_search.SEARCH_ENGINE = "serpapi"
    else:
        real_search.USE_REAL_SEARCH = True
        real_search.SEARCH_ENGINE = "tavily"

def print_banner():
    if real_search.USE_REAL_SEARCH:
        mode = f"REAL ({real_search.SEARCH_ENGINE.upper()})"
    else:
        mode = "MOCK"
    print("\n------------------------------------------------------------")
    print("AI Career Research Assistant")
    print(f"Search mode: {mode}")
    print("------------------------------------------------------------")
    print("Commands: 'tools' | 'history' | 'clear' | 'exit'")
    print("------------------------------------------------------------\n")

def show_tools():
    print("\nAvailable Tools:")
    print("--------------------------------------------------")
    for tool in TOOL_DEFINITIONS:
        print(f"Tool: {tool['function']['name']}")
        print(f"      {tool['function']['description'][:80]}...")
    print()

def show_history(messages: list):
    if not messages or len(messages) <= 1:
        print("\n(No messages yet)\n")
        return
    print("\nConversation History")
    print("--------------------------------------------------")
    for i, msg in enumerate(messages):
        role = msg.role if hasattr(msg, "role") else msg.get("role")
        content = msg.content if hasattr(msg, "content") else msg.get("content")
        
        if role == "system":
            continue
            
        if role == "user":
            print(f"[{i}] You: {str(content)[:100]}")
        elif role == "tool":
            print(f"[{i}] Tool Results: {str(content)[:50]}...")
        elif role == "assistant":
            if content:
                print(f"[{i}] Assistant: {str(content)[:100]}")
            
            tool_calls = msg.tool_calls if hasattr(msg, "tool_calls") else msg.get("tool_calls")
            if tool_calls:
                for t in tool_calls:
                    name = t.function.name if hasattr(t, "function") else t.get("function", {}).get("name")
                    print(f"[{i}] Assistant->Tool: {name}")
    print()

if __name__ == "__main__":
    configure_search()
    print_banner()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("\nGoodbye!\n")
            break
        elif user_input.lower() == "tools":
            show_tools()
            continue
        elif user_input.lower() == "history":
            show_history(messages)
            continue
        elif user_input.lower() == "clear":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("\nConversation cleared.\n")
            continue

        try:
            print()
            reply = run_agent(user_input, messages, show_tool_calls=True)
            print(f"\nAssistant:\n{reply}\n")
        except Exception as e:
            print(f"\nError: {e}\n")