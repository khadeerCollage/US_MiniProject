# US Mini Project - Groq AI Integration

This repository contains a suite of CLI tools configured to interface with the Groq API using the free-tier llama-3.3-70b-versatile model.

## File Structure

* utils.py: Shared helper functions to load environment variables from a local .env file and initialize the Groq client.
* setup_check_groq.py: A connection verification script to confirm your Groq API key is valid and working.
* chat.py: A CLI conversational chatbot featuring message history preservation and session token usage tracking.
* summarize.py: A document summarizer that accepts any plain text file, handles truncation for large context limits, and outputs structured summaries.
* summarize_v2.py: A document summarizer demonstrating plain vs structured XML prompts using the --compare flag.
* persona_bot.py: An interactive character Q&A chatbot allowing real-time switching between four distinct system-prompt-driven personas:
  * Coach Alex: Silicon Valley career coach.
  * Dr. Sarah Chen: Senior machine learning scientist.
  * Marcus the Builder: Senior full-stack engineer.
  * Priya the Interviewer: Technical interviewer.
* persona_bot_v2.py: An interactive persona chatbot that demonstrates the power of few-shot prompting to shape character responses.
* chain_of_thought.py: A Chain-of-Thought reasoning bot demonstrating how to force the model to reason step-by-step before answering.
* prompt_scroing_upon_techniques.py: A testing harness that runs simple, XML structured, and Chain-of-Thought prompts against the same inputs to objectively evaluate output quality and token efficiency.
* Real_Time_Agents/tools.py: Contains the actual Python functions that get called when the model decides to use a tool (e.g., search_web, read_file, calculate).
* Real_Time_Agents/tools_working.py: A step-by-step visual demonstration of the LLM tool-calling loop (function calling) using Groq.
* Real_Time_Agents/research_assistant.py: A fully functional agentic research assistant that can autonomously use multiple tools in an iterative loop to answer complex questions using Groq.
* Real_Time_Agents/real_search.py: Search integrations for the Research Assistant, implementing DuckDuckGo, SerpAPI, and Tavily interfaces.
* multi-agents/agent1_summarize.py: Part of the multi-agent pipeline. A focused subagent that reads a CSV dataset, profiles it, and generates a structured summary using Groq.
* multi-agents/agent2_insights.py: Part of the multi-agent pipeline. Generates strategic, actionable business insights from Agent 1's structured summary using Groq and Chain-of-Thought reasoning.
* MCP (Model Context Protocol)/test_mcp_tools.py: Tests the 5 career research MCP tools directly without running a server.
* MCP (Model Context Protocol)/mcp_server_career.py: A custom FastMCP server that exposes 5 career research and analysis tools to any MCP-compatible client.
* MCP (Model Context Protocol)/agent_with_mcp.py: An interactive agent connected directly to the MCP server using the Anthropic API.
* MCP (Model Context Protocol)/claude_desktop_setup.py: A utility script to generate the Claude Desktop configuration required to connect the desktop app to local MCP servers.

## Installation and Configuration

1. Initialize and activate your virtual environment:
   .\venv\Scripts\activate

2. Install dependencies:
   pip install groq

3. Configure your API key in a local .env file in the root directory:
   GROQ_API_KEY="your_api_key_here"

## Usage

* To run the connection test:
  python setup_check_groq.py

* To start the chat loop:
  python chat.py

* To summarize a document:
  python summarize.py <file_path>
  python summarize_v2.py <file_path> [--compare]

* To interact with different personas:
  python persona_bot.py
  python persona_bot_v2.py

* To test Chain-of-Thought reasoning:
  python chain_of_thought.py

* To evaluate prompt techniques with the scoring harness:
  python prompt_scroing_upon_techniques.py [--topic career | technical | default]

* To run the step-by-step tool use explanation:
  python Real_Time_Agents/tools_working.py

* To run the autonomous research assistant agent:
  python Real_Time_Agents/research_assistant.py

* To run the multi-agent profiling and insights pipeline:
  - Run Agent 1 (CSV Summarization) standalone:
    ```bash
    python multi-agents/agent1_summarize.py multi-agents/sample_data.csv
    ```
  - Run Agent 2 (Insight Generation with CoT) standalone:
    ```bash
    python multi-agents/agent2_insights.py
    ```
    *(Note: Agent 2 runs Agent 1 under the hood to profile `sample_data.csv`, then applies Chain-of-Thought reasoning to generate structured strategic insights).*

* To interact with the MCP Server and Agent:
  - Run the MCP server in SSE mode in Terminal 1:
    ```bash
    python "MCP (Model Context Protocol)/mcp_server_career.py" --sse
    ```
  - Connect the MCP agent to the server in Terminal 2:
    ```bash
    python "MCP (Model Context Protocol)/agent_with_mcp.py"
    ```
