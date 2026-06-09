import sys
import os
from utils import get_groq_client

client = get_groq_client()

tools = [
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

system_prompt = (
    "You are a helpful assistant with access to tools. "
    "When calling a tool, you MUST output the tool call as a raw JSON object matching the tool's schema. "
    "DO NOT wrap the JSON in XML tags like <function=...> or similar formats."
)

try:
    print("Testing clean JSON system prompt + temperature=0...")
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "What are the top skills needed to get hired at Anthropic? Search for this."}
        ],
        tools=tools,
        temperature=0,
        max_tokens=1024
    )
    print("Success:")
    print(res.choices[0].message)
except Exception as e:
    print("Failed:")
    print(e)
