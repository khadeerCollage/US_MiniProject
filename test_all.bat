@echo off
echo ==================================================
echo      US_MiniProject - Full Manual Test Suite
echo ==================================================
echo.

echo [1/3] Running Automated Tests (pytest)...
python -m pytest tests/
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Pytest suite failed! Stopping tests.
    exit /b %ERRORLEVEL%
)
echo [OK] All automated tests passed.
echo.

echo [2/3] Testing LangGraph Pipeline (orchestrator.py)...
python multi-agents/orchestrator.py sample_data.csv
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] LangGraph pipeline failed! Stopping tests.
    exit /b %ERRORLEVEL%
)
echo [OK] LangGraph pipeline ran successfully.
echo.

echo [3/3] Testing MCP Server Tools...
python "MCP (Model Context Protocol)\test_mcp_tools.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] MCP Tools test failed! Stopping tests.
    exit /b %ERRORLEVEL%
)
echo [OK] MCP Server tools ran successfully.
echo.

echo ==================================================
echo     ALL TESTS PASSED SUCCESSFULLY! 10/10
echo ==================================================
pause
