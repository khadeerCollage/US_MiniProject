"""
agent_with_mcp.py - Agent Using the MCP Server with Groq

This script demonstrates an agent connecting to a local MCP server.
It uses Groq's API and the mcp library to fetch tools from the server,
bind them to a free Llama model on Groq, and execute them on the local server.

Pre-requisite:
    Start the MCP server first:
    python mcp_server_career.py --sse

Usage:
    python agent_with_mcp.py
"""

import os
import sys
import json
import asyncio
from groq import AsyncGroq
from mcp import ClientSession
from mcp.client.sse import sse_client


def load_env_file():
    """Load variables from .env file into os.environ if present."""
    for path in [".env", "../.env"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            os.environ[key] = val
                break
            except Exception:
                pass


load_env_file()

if not os.environ.get("GROQ_API_KEY"):
    print("\n[ERROR] GROQ_API_KEY not found in environment or .env file.")
    print("Please add GROQ_API_KEY to your .env file to continue.\n")
    sys.exit(1)

MODEL       = "llama-3.3-70b-versatile"
MCP_SERVER  = "http://localhost:8000/sse"

client = AsyncGroq()

SYSTEM_PROMPT = """
You are an expert AI Career Advisor with access to a live career research database
via MCP tools. You help software engineers land jobs at top US AI companies.

You have 5 powerful MCP tools. Use them proactively:
- search_ai_jobs         -> When user asks about available jobs or roles
- get_skill_gap          -> When user asks what to learn or skill gaps
- calculate_salary       -> When user asks about pay, compensation, worth
- get_company_profile    -> When user asks about a specific company
- get_interview_prep     -> When user asks how to prepare for interviews

For complex requests, combine multiple tools in sequence.
Example: "Should I target TechCorp?" ->
  1. get_company_profile("TechCorp")
  2. search_ai_jobs("AI Engineer", company="TechCorp")
  3. Synthesize into a recommendation

Style:
- Always use tool data. Never give generic career advice without tool results.
- After calling tools, synthesize the results into clear, actionable advice.
- Be direct. End every response with ONE specific next step.
- Reference the user's context when helpful.

CRITICAL TOOL CALLING RULES:
1. ONLY pass arguments that are explicitly listed in the tool's schema. Do NOT hallucinate or add extra arguments (e.g., do NOT pass "location" to search_ai_jobs, as it only accepts "role", "company", and "remote_only").
2. Boolean parameters (such as "remote_only") must be passed strictly as JSON booleans (true or false). NEVER pass them as strings (e.g. do NOT pass "false" or "true").
"""


async def run_mcp_agent(session, user_message: str, messages: list, show_thinking: bool = True) -> str:
    """
    Send a message to the agent connected to our MCP server.
    We query the MCP server session for available tools, map them to Groq format,
    and handle any tool call requests returned by Groq.
    """
    messages.append({"role": "user", "content": user_message})

    # Fetch tools from MCP server
    if show_thinking:
        print("\n  [INFO] Querying MCP server tools...")
    
    try:
        tools_resp = await session.list_tools()
        tools_list = tools_resp.tools
    except Exception as e:
        return f"[ERROR] Failed to list tools from MCP server: {e}"

    # Map MCP tools to Groq tool calling format
    groq_tools = []
    for tool in tools_list:
        groq_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        })

    if show_thinking:
        print(f"  [INFO] Connected. Found {len(groq_tools)} tools.")
        print("  [INFO] Deciding which tools to use...\n")

    # Loop to handle iterative tool calling
    while True:
        try:
            # We call Groq's chat completion
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                tools=groq_tools if groq_tools else None
            )
        except Exception as e:
            # Handle tool calling validation/type errors from Groq (e.g. 400 invalid_request_error with tool_use_failed)
            err_str = str(e).lower()
            if "tool_use_failed" in err_str or "invalid_request_error" in err_str or "400" in err_str:
                if show_thinking:
                    print("  [WARNING] Groq tool calling validation failed. Retrying with self-correction prompt...")
                correction_msg = {
                    "role": "system",
                    "content": (
                        "SYSTEM NOTIFICATION: Your previous tool call failed validation because of incorrect arguments. "
                        "Remember: "
                        "1) ONLY use parameters explicitly defined in the schemas. Do NOT pass 'location' to search_ai_jobs. "
                        "2) Pass boolean arguments strictly as JSON booleans (true or false), never as strings ('true'/'false'). "
                        "Please regenerate the tool call now with correct arguments."
                    )
                }
                try:
                    response = await client.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages + [correction_msg],
                        tools=groq_tools if groq_tools else None
                    )
                except Exception as retry_err:
                    return f"[ERROR] Groq API call failed after retry: {retry_err}"
            else:
                return f"[ERROR] Groq API call failed: {e}"

        message = response.choices[0].message
        
        # If the model wants to call tools
        if message.tool_calls:
            # Serialize the assistant message with tool calls to a plain dict
            tool_calls_list = []
            for tc in message.tool_calls:
                tool_calls_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": tool_calls_list
            })
            
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                if show_thinking:
                    print(f"  [TOOL CALL] {tool_name}")
                    print(f"      Input: {json.dumps(tool_args, indent=8)[:200]}")

                try:
                    # Execute tool call on local MCP server
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    
                    # Extract text content from result
                    result_text = ""
                    for block in result.content:
                        if block.type == "text":
                            result_text += block.text

                    if show_thinking:
                        preview = result_text[:150].replace("\n", " ")
                        print(f"      Result preview: {preview}...")
                except Exception as e:
                    result_text = f"Error executing tool: {e}"
                    if show_thinking:
                        print(f"      [ERROR] {result_text}")

                # Append tool result to history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": result_text
                })
            
            # Continue the loop so Groq can process the tool results and decide to answer or call another tool
            continue
        
        # If no tool calls, this is the final response
        messages.append({"role": "assistant", "content": message.content})
        return message.content or "(No text response)"


def print_banner():
    print("\n------------------------------------------------------------")
    print("   AI Career Agent with MCP (Groq Edition)")
    print("------------------------------------------------------------")
    print(f"   MCP Server:  {MCP_SERVER}")
    print("   Model:       Groq Llama 3.3 (Free Tier)")
    print("   Make sure server is running: python mcp_server_career.py --sse")
    print("------------------------------------------------------------")
    print("  Commands: 'tools' | 'history' | 'clear' | 'thinking' | 'exit'")
    print("------------------------------------------------------------")
    print("  Try: 'Search TechCorp jobs and tell me my skill gaps for Python + APIs'")
    print("  Try: 'Compare TechCorp vs Cohere for a remote engineer in India'")
    print("  Try: 'What salary can I expect with 2 years exp targeting Cohere remotely?'")
    print("------------------------------------------------------------\n")


async def main():
    print_banner()

    messages     = []
    show_thinking = True

    # Establish connection to MCP server
    try:
        async with sse_client(MCP_SERVER) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                while True:
                    try:
                        user_input = input("\nYou: ").strip()
                    except (KeyboardInterrupt, EOFError):
                        print("\n\n  Good luck with the interviews!\n")
                        break

                    if not user_input:
                        continue

                    if user_input.lower() in ("exit", "quit"):
                        print("\n  Exiting agent.\n")
                        break

                    elif user_input.lower() == "thinking":
                        show_thinking = not show_thinking
                        print(f"\n  Tool call display: {'ON (showing)' if show_thinking else 'OFF (hidden)'}\n")
                        continue

                    elif user_input.lower() == "clear":
                        messages.clear()
                        print("\n  History cleared.\n")
                        continue

                    elif user_input.lower() == "history":
                        print(f"\n  {len(messages)} messages in history.\n")
                        continue

                    elif user_input.lower() == "tools":
                        print("""
  MCP Tools available on the server:
  ------------------------------------------------------------
  1. search_ai_jobs(role, company, remote_only)
  2. get_skill_gap(current_skills, target_role, target_company)
  3. calculate_salary(years_experience, role, location, company_tier)
  4. get_company_profile(company_name)
  5. get_interview_prep(company, role, interview_round)
""")
                        continue

                    try:
                        reply = await run_mcp_agent(session, user_input, messages, show_thinking=show_thinking)
                        print(f"\nAdvisor:\n{reply}\n")
                    except Exception as e:
                        print(f"\n  [Error] {e}\n")
                        
    except Exception as e:
        print(f"\n[ERROR] Cannot connect to MCP server at {MCP_SERVER}.")
        print("Make sure the server is running in another terminal:")
        print("  python mcp_server_career.py --sse\n")
        print(f"Details: {e}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n  Good luck with the interviews!\n")