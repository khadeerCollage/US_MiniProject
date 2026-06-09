"""
Visual Step-by-Step Tool Use Tutorial
Demonstrates a single tool call loop using Groq and llama-3.3-70b-versatile.
"""

import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_groq_client
from tools import execute_tool

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
client = get_groq_client()

SIMPLE_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web. Returns relevant results for the query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    }
]


def separator(title: str = ""):
    if title:
        print(f"\n--- {title} ---")
    else:
        print("\n----------------------------------------")


def step(n: int, title: str, description: str):
    print(f"\nSTEP {n}: {title}")
    print(f"Description: {description}")


def run_visual_demo():
    print("Tool Use Loop - Visual Step-by-Step Explanation")
    print("This demo shows exactly what happens during one tool call.")
    print("The same loop runs in the research assistant for every message.")
    print("Study this output carefully before moving on.")

    input("Press ENTER to start the demo...\n")

    step(1, "User sends a message", "We add it to the messages list and send to Groq.")

    system_prompt = (
        "You are a helpful assistant. If you call a tool, you must format the function call strictly as: "
        "<function=tool_name>{\"arg\": \"value\"}</function>. "
        "Ensure there is a closing angle bracket '>' after the function name."
    )
    user_message = "What are the top skills needed to get hired at Anthropic? Search for this."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    print(f"\nUser message: '{user_message}'")
    print("\nMessages array (what we send to Groq):")
    print(json.dumps(messages, indent=4))

    input("\nPress ENTER for Step 2...")

    step(2, "Groq responds - finish_reason = 'tool_calls'",
         "Groq decides it needs the search tool. It does not give a text answer yet.")

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,
        tools=SIMPLE_TOOL,
        messages=messages
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    finish_reason = response.choices[0].finish_reason

    print(f"\nresponse.choices[0].finish_reason = '{finish_reason}'")
    print("(If this is 'tool_calls', Groq wants to call a tool)")
    
    if tool_calls:
        print(f"\nresponse_message has {len(tool_calls)} tool call(s):")
        for i, tool_call in enumerate(tool_calls):
            print(f"\nTool Call {i}:")
            print(f"  id        = '{tool_call.id}'")
            print(f"  type      = '{tool_call.type}'")
            print(f"  name      = '{tool_call.function.name}'")
            print(f"  arguments = {tool_call.function.arguments}")

    input("\nPress ENTER for Step 3...")

    step(3, "Append Groq's response to messages",
         "We store the response message. Required for tool tracking.")

    messages.append(response_message)

    print(f"\nmessages now has {len(messages)} entries.")
    print("(user message + Groq's tool_use response)")

    input("\nPress ENTER for Step 4...")

    step(4, "Python extracts the tool call and runs it locally",
         "Groq decided what to call. Python actually runs it.")

    if tool_calls:
        for tool_call in tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"\nTool name:  {name}")
            print(f"Arguments:  {args}")
            print(f"\nRunning execute_tool('{name}', {args})...")

            result = execute_tool(name, args)

            print("\nResult (first 300 chars):")
            print("  " + result[:300].replace("\n", "\n  "))

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": result
            })

    input("\nPress ENTER for Step 5...")

    step(5, "Send tool results back to Groq (role = 'tool')",
         "We send the results as a tool message. Groq reads them and writes its final answer.")

    print("\nMessages now has:")
    for idx, msg in enumerate(messages):
        role = msg.role if hasattr(msg, "role") else msg.get("role")
        print(f"  [{idx}] role: {role}")

    input("\nPress ENTER for Step 6...")

    step(6, "Groq gets the results - finish_reason = 'stop'",
         "Groq reads the search results and now writes its final text answer.")

    final_response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,
        tools=SIMPLE_TOOL,
        messages=messages
    )

    final_message = final_response.choices[0].message
    final_finish_reason = final_response.choices[0].finish_reason

    print(f"\nresponse.choices[0].finish_reason = '{final_finish_reason}'")
    print("(stop = Groq is done! Time to print the reply.)\n")

    separator("GROQ'S FINAL ANSWER")
    print(final_message.content)
    separator()

    print("\nWhat just happened (the full loop):")
    print("1. User said: 'Search for Anthropic skills'")
    print("2. Groq said: finish_reason='tool_calls' -> call search_web(...)")
    print("3. Python ran search_web() -> got results")
    print("4. Python sent results back to Groq with role='tool'")
    print("5. Groq said: finish_reason='stop' -> gave final answer")
    print("\nThis loop can repeat many times for complex tasks.")


if __name__ == "__main__":
    run_visual_demo()