"""
claude_desktop_setup.py - Claude Desktop MCP Configuration

This script generates the configuration JSON required to connect Claude Desktop
to your custom MCP servers. It also shows you exactly where to put this
configuration file on your system.

Usage:
    python claude_desktop_setup.py

    It will print the exact JSON to paste into Claude Desktop settings.
    Open Claude Desktop -> Settings -> Developer -> Edit Config
"""

import os
import sys
import json
import platform
import glob


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


def get_claude_config_paths() -> list:
    """Return a list of paths to Claude Desktop's config file (including virtualized packaged paths)."""
    system = platform.system()
    paths = []
    
    if system == "Darwin":    # macOS
        paths.append(os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json"))
    elif system == "Windows":
        # Standard AppData path
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            paths.append(os.path.join(app_data, "Claude", "claude_desktop_config.json"))
        
        # Packaged Microsoft Store Claude AppData path
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            pattern = os.path.join(local_app_data, "Packages", "Claude_*", "LocalCache", "Roaming", "Claude", "claude_desktop_config.json")
            packaged_paths = glob.glob(pattern)
            paths.extend(packaged_paths)
            
            # If no paths matched but the Packages/Claude_* directory structure exists, 
            # we can pre-emptively look for the LocalCache/Roaming/Claude directory to create it.
            if not packaged_paths:
                packages_dir = os.path.join(local_app_data, "Packages")
                if os.path.exists(packages_dir):
                    for folder in os.listdir(packages_dir):
                        if folder.startswith("Claude_"):
                            candidate = os.path.join(packages_dir, folder, "LocalCache", "Roaming", "Claude", "claude_desktop_config.json")
                            paths.append(candidate)
    else:                     # Linux
        paths.append(os.path.expanduser("~/.config/claude/claude_desktop_config.json"))
        
    return list(set(paths)) # Remove duplicates


def get_python_path() -> str:
    """Get the path to the current Python executable."""
    return sys.executable


def get_server_path() -> str:
    """Get absolute path to our MCP server script."""
    return os.path.abspath("mcp_server_career.py")


def build_config() -> dict:
    """
    Build the Claude Desktop config that registers our MCP server.
    """
    python_path = get_python_path()
    server_path = get_server_path()
    api_key     = os.environ.get("GROQ_API_KEY", "YOUR_KEY_HERE")

    config = {
        "mcpServers": {
            # Our custom career research server
            "ai-career-research": {
                "command": python_path,
                "args":    [server_path],
                "env": {
                    "GROQ_API_KEY": api_key
                }
            },
            # Official filesystem server (read/write local files)
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    os.path.expanduser("~/Desktop"),
                    os.path.expanduser("~/Documents"),
                ],
                "env": {}
            },
            # Official fetch server (fetch web URLs)
            "fetch": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-fetch"
                ],
                "env": {}
            }
        }
    }

    return config


def print_setup_guide():
    load_env_file()
    config      = build_config()
    config_paths = get_claude_config_paths()
    config_json = json.dumps(config, indent=2)

    print("\n------------------------------------------------------------")
    print("   Claude Desktop MCP Setup Guide")
    print("------------------------------------------------------------")

    print(f"""
STEP 1: Install Node.js (needed for official MCP servers)
------------------------------------------------------------
  Download from: https://nodejs.org  (LTS version)
  Verify: node --version && npm --version


STEP 2: Install official MCP servers
------------------------------------------------------------
  npm install -g @modelcontextprotocol/server-filesystem
  npm install -g @modelcontextprotocol/server-fetch


STEP 3: Install our MCP server dependencies
------------------------------------------------------------
  pip install "mcp[cli]" uvicorn


STEP 4: Find your Claude Desktop config file
------------------------------------------------------------
  Detected config path(s) on your system:""")
    for path in config_paths:
        print(f"  - {path}")
        
    print("""
  Open Claude Desktop -> Settings (gear icon) -> Developer
  Click "Edit Config" - this opens the JSON file.


STEP 5: Paste this JSON into the config file
------------------------------------------------------------
""")
    print(config_json)

    print(f"""

STEP 6: Restart Claude Desktop
------------------------------------------------------------
  Fully quit Claude Desktop (not just close the window).
  Re-open it. Look for the tool icon in the chat box.
  That confirms MCP servers are connected.


STEP 7: Test in Claude Desktop chat
------------------------------------------------------------
  Type these in the Claude Desktop chat:

  Using filesystem server:
    "List all files on my Desktop"
    "Read the file README.md from my Desktop"

  Using our career server:
    "Search for AI Engineer jobs at TechCorp"
    "What skills do I need to get hired as an AI Engineer?"
    "Calculate salary for 3 years experience, AI Engineer, remote"

  Using fetch server:
    "Fetch the content from https://example.com"


STEP 8: Try combining servers!
------------------------------------------------------------
  "Search TechCorp jobs, then save the results to ~/Desktop/jobs.txt"
  (Uses career server + filesystem server together!)


WHAT'S HAPPENING UNDER THE HOOD:
------------------------------------------------------------
  Claude Desktop reads the config -> starts each MCP server as a subprocess
  -> Claude sees all available tools from all servers
  -> When you ask something, Claude decides which tool(s) to use
  -> The MCP protocol handles the communication automatically

  You are now using MCP exactly as production applications use it.
""")

    # Optional: Auto-write the config
    print("------------------------------------------------------------")
    write = input("  Auto-write this config to your Claude Desktop config file(s)? (y/n): ").strip().lower()
    if write == "y":
        for config_path in config_paths:
            config_dir = os.path.dirname(config_path)
            os.makedirs(config_dir, exist_ok=True)

            # Backup existing config if present
            if os.path.exists(config_path):
                backup = config_path + ".backup"
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        backup_data = f.read()
                    with open(backup, "w", encoding="utf-8") as f:
                        f.write(backup_data)
                    print(f"  [BACKUP] Backed up existing config to: {backup}")
                except Exception as e:
                    print(f"  [WARNING] Could not back up existing config at {config_path}: {e}")

            # Merge config
            merged = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        merged = json.load(f)
                except Exception:
                    pass

            if "mcpServers" not in merged:
                merged["mcpServers"] = {}

            # Merge servers
            for key, val in config["mcpServers"].items():
                merged["mcpServers"][key] = val

            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(merged, f, indent=2)
                print(f"  [SUCCESS] Config written to: {config_path}")
            except Exception as e:
                print(f"  [ERROR] Failed to write config to {config_path}: {e}")
        
        print("  [INFO] Now restart Claude Desktop.")
    else:
        print("  Copy the JSON above manually into your Claude Desktop config file.")

    print()


if __name__ == "__main__":
    print_setup_guide()