@echo off
REM Test runner script for Chatwork-Lark Bridge (Windows)

echo.
echo Testing Chatwork-Lark Bridge
echo ====================================
echo.

set MODE=%1
if "%MODE%"=="" set MODE=all

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install dependencies if needed
where pytest >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing test dependencies...
    pip install -r requirements-test.txt
)

echo.

if "%MODE%"=="unit" (
    echo Running unit tests...
    pytest tests/unit -v -m unit --cov=src --cov-report=term-missing
    goto :end
)

if "%MODE%"=="integration" (
    echo Running integration tests...
    pytest tests/integration -v -m integration --cov=src --cov-report=term-missing
    goto :end
)

if "%MODE%"=="e2e" (
    echo Running E2E tests...
    pytest tests/e2e -v -m e2e --cov=src --cov-report=term-missing
    goto :end
)

if "%MODE%"=="fast" (
    echo Running fast tests (excluding slow^)...
    pytest -v -m "not slow" --cov=src --cov-report=term-missing
    goto :end
)

if "%MODE%"=="coverage" (
    echo Running all tests with detailed coverage...
    pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80
    echo.
    echo Coverage report generated at: htmlcov\index.html
    start htmlcov\index.html
    goto :end
)

if "%MODE%"=="ci" (
    echo Running CI mode (strict^)...
    pytest --cov=src --cov-report=xml --cov-fail-under=80 -W error
    echo.
    echo All tests passed with coverage >= 80%%
    goto :end
)

REM Default: run all tests
echo Running all tests...
echo.
echo 1. Unit tests
pytest tests/unit -v -m unit

echo.
echo 2. Integration tests
pytest tests/integration -v -m integration

echo.
echo 3. E2E tests
pytest tests/e2e -v -m e2e

echo.
echo 4. Coverage report
pytest --cov=src --cov-report=term-missing --cov-fail-under=80

echo.
echo All test suites completed!

:end
echo.
echo ====================================
echo Done!
echo.

REM Usage information
if "%MODE%"=="help" (
    echo Usage: run_tests.bat [mode]
    echo.
    echo Modes:
    echo   all          - Run all tests (default^)
    echo   unit         - Run unit tests only
    echo   integration  - Run integration tests only
    echo   e2e          - Run E2E tests only
    echo   fast         - Run fast tests (exclude slow^)
    echo   coverage     - Generate HTML coverage report
    echo   ci           - Run in CI mode (strict^)
    echo   help         - Show this help
)
