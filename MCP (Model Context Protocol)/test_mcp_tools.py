"""
test_mcp_tools.py - Test All MCP Tools Without Protocol Overhead

It is important to test MCP tools in isolation before integrating them with the server.
The MCP protocol adds complexity, so testing raw tool functions first makes debugging easier.

Usage:
    python test_mcp_tools.py           # Run all tests
    python test_mcp_tools.py --tool 1  # Test only tool 1 (search_ai_jobs)
"""

import sys
from mcp_server_career import (
    search_ai_jobs,
    get_skill_gap,
    calculate_salary,
    get_company_profile,
    get_interview_prep
)


def separator(title: str = "", width: int = 60):
    if title:
        pad = (width - len(title) - 4) // 2
        print(f"\n{'-'*pad}  {title}  {'-'*pad}")
    else:
        print("-" * width)


def run_test(tool_num: int, tool_name: str, test_cases: list):
    """Run a list of test cases for a tool."""
    separator(f"TOOL {tool_num}: {tool_name}")

    for i, (description, func_call) in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {description}")
        print("  " + "-" * 50)
        try:
            result = func_call()
            # Print result with indentation for readability
            for line in result.strip().split("\n"):
                print(f"  {line}")
            print(f"\n  [PASS] Test {i} ({len(result)} chars)")
        except Exception as e:
            print(f"  [FAIL] Test {i}: {e}")


# TEST CASES

def test_search_ai_jobs():
    run_test(1, "search_ai_jobs", [
        (
            "Search for AI Engineer roles (all companies)",
            lambda: search_ai_jobs("AI Engineer")
        ),
        (
            "Search for ML Engineer at TechCorp specifically",
            lambda: search_ai_jobs("Engineer", company="TechCorp")
        ),
        (
            "Remote-only search",
            lambda: search_ai_jobs("AI Engineer", remote_only=True)
        ),
        (
            "Edge case - no results",
            lambda: search_ai_jobs("Quantum Blockchain Engineer")
        ),
    ])


def test_get_skill_gap():
    run_test(2, "get_skill_gap", [
        (
            "Python dev targeting AI Engineer role",
            lambda: get_skill_gap(
                current_skills="Python, REST APIs, SQL, React, Git",
                target_role="AI Engineer",
                target_company="TechCorp"
            )
        ),
        (
            "Current skills match almost perfectly",
            lambda: get_skill_gap(
                current_skills="Python, PyTorch, LLM APIs, Prompt Engineering, RAG, Tool Use, MCP",
                target_role="LLM Engineer"
            )
        ),
        (
            "Near-zero skills (reality check scenario)",
            lambda: get_skill_gap(
                current_skills="Java, Spring Boot",
                target_role="Research Engineer",
                target_company="Google DeepMind"
            )
        ),
    ])


def test_calculate_salary():
    run_test(3, "calculate_salary", [
        (
            "3 years exp, AI Engineer, remote, top tier company",
            lambda: calculate_salary(3, "AI Engineer", "remote", "top")
        ),
        (
            "2 years exp, ML Engineer, San Francisco",
            lambda: calculate_salary(2, "ML Engineer", "sf", "top")
        ),
        (
            "Entry level, remote from India",
            lambda: calculate_salary(1, "AI Engineer", "india", "mid")
        ),
    ])


def test_get_company_profile():
    run_test(4, "get_company_profile", [
        (
            "TechCorp profile",
            lambda: get_company_profile("TechCorp")
        ),
        (
            "Cohere profile (great first target)",
            lambda: get_company_profile("Cohere")
        ),
        (
            "Edge case - unknown company",
            lambda: get_company_profile("SomeStartupXYZ")
        ),
    ])


def test_get_interview_prep():
    run_test(5, "get_interview_prep", [
        (
            "TechCorp AI Engineer - all rounds",
            lambda: get_interview_prep("TechCorp", "AI Engineer", "all")
        ),
        (
            "OpenAI ML Engineer - system design only",
            lambda: get_interview_prep("OpenAI", "ML Engineer", "system_design")
        ),
    ])


if __name__ == "__main__":
    print("\nMCP Tools Test Suite")
    print("Testing all 5 tools directly (no MCP protocol overhead)")
    print("This verifies tool logic before running the full server\n")

    all_tests = [
        ("1", test_search_ai_jobs),
        ("2", test_get_skill_gap),
        ("3", test_calculate_salary),
        ("4", test_get_company_profile),
        ("5", test_get_interview_prep),
    ]

    # Allow running a single tool
    if "--tool" in sys.argv:
        idx = sys.argv.index("--tool")
        if idx + 1 < len(sys.argv):
            tool_num = sys.argv[idx + 1]
            all_tests = [(n, f) for n, f in all_tests if n == tool_num]
            if not all_tests:
                print(f"Unknown tool number '{tool_num}'. Use 1-5.\n")
                sys.exit(1)

    for _, test_fn in all_tests:
        test_fn()

    print("\nAll tests complete!")
    print("Next: start the MCP server and run agent_with_mcp.py\n")